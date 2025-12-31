"""Momentum strategy: price momentum + volume acceleration + sentiment."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np

from portfolio.data.prices import price_fetcher
from portfolio.data.sentiment import news_sentiment, reddit_sentiment
from portfolio.data.universes import MOMENTUM_UNIVERSE
from portfolio.db.models import Price, StrategySignal
from portfolio.utils.logging import logger


class MomentumStrategy:
    """
    Momentum strategy combining:
    - Multi-period price momentum (3/6/12 months)
    - Volume acceleration
    - Sentiment (news + reddit)

    Rebalances monthly, monitors weekly for crash conditions.
    """

    def __init__(self):
        """Initialize momentum strategy."""
        self.universe = MOMENTUM_UNIVERSE
        self.top_n = 10  # Hold top N stocks
        self.lookback_days = 365  # Need 1 year for 12-month momentum

    def generate_signals(self, asof_date: date) -> list[StrategySignal]:
        """
        Generate momentum signals for the universe.

        Args:
            asof_date: Date to compute signals as of

        Returns:
            List of StrategySignal objects sorted by score (descending)
        """
        start_date = asof_date - timedelta(days=self.lookback_days)

        logger.info(f"Fetching momentum universe prices from {start_date} to {asof_date}")
        price_data = price_fetcher.fetch_prices(self.universe, start_date, asof_date)

        signals = []
        for ticker in self.universe:
            if ticker not in price_data or len(price_data[ticker]) < 180:
                logger.warning(f"Insufficient data for {ticker}, skipping")
                continue

            try:
                signal = self._compute_signal(ticker, price_data[ticker], asof_date)
                signals.append(signal)
            except Exception as e:
                logger.error(f"Error computing signal for {ticker}: {e}")
                continue

        # Sort by score descending
        signals.sort(key=lambda s: s.score, reverse=True)
        logger.info(f"Generated {len(signals)} momentum signals, top: {signals[0].ticker if signals else 'none'}")

        return signals

    def _compute_signal(
        self, ticker: str, prices: list[Price], asof_date: date
    ) -> StrategySignal:
        """Compute composite momentum signal for a ticker."""
        # Convert to numpy arrays
        dates = np.array([p.date for p in prices])
        adj_close = np.array([float(p.adj_close) for p in prices])
        volumes = np.array([float(p.volume) if p.volume else 0 for p in prices])

        # Price momentum components
        momentum_3m = self._compute_return(adj_close, dates, asof_date, months=3)
        momentum_6m = self._compute_return(adj_close, dates, asof_date, months=6)
        momentum_12m = self._compute_return(adj_close, dates, asof_date, months=12)

        # Weighted momentum (weights: 3m=0.3, 6m=0.4, 12m=0.3)
        momentum_score = (
            Decimal("0.3") * momentum_3m +
            Decimal("0.4") * momentum_6m +
            Decimal("0.3") * momentum_12m
        )

        # Volume acceleration (recent vs historical average)
        volume_score = self._compute_volume_accel(volumes, dates, asof_date)

        # Sentiment scores
        sentiment_start = asof_date - timedelta(days=30)
        news_score = news_sentiment.get_sentiment(ticker, sentiment_start, asof_date)
        reddit_score = reddit_sentiment.get_sentiment(ticker, sentiment_start, asof_date)
        sentiment_score = (news_score + reddit_score) / Decimal("2")

        # Volatility (for inverse vol weighting)
        volatility = self._compute_volatility(adj_close, dates, asof_date)

        # Composite score (weights: momentum=0.6, volume=0.2, sentiment=0.2)
        composite_score = (
            Decimal("0.6") * momentum_score +
            Decimal("0.2") * volume_score +
            Decimal("0.2") * sentiment_score
        )

        return StrategySignal(
            ticker=ticker,
            score=composite_score,
            components={
                "momentum_3m": momentum_3m,
                "momentum_6m": momentum_6m,
                "momentum_12m": momentum_12m,
                "volume_accel": volume_score,
                "sentiment": sentiment_score,
                "volatility": volatility,
            },
        )

    def _compute_return(
        self, prices: np.ndarray, dates: np.ndarray, asof_date: date, months: int
    ) -> Decimal:
        """Compute total return over N months."""
        lookback_date = asof_date - timedelta(days=months * 30)

        # Find prices closest to target dates
        current_price = prices[-1]
        lookback_idx = np.searchsorted(dates, lookback_date)

        if lookback_idx >= len(prices):
            return Decimal("0.0")

        lookback_price = prices[lookback_idx]

        if lookback_price <= 0:
            return Decimal("0.0")

        return_pct = (current_price - lookback_price) / lookback_price
        return Decimal(str(return_pct))

    def _compute_volume_accel(
        self, volumes: np.ndarray, dates: np.ndarray, asof_date: date
    ) -> Decimal:
        """Compute volume acceleration score."""
        if len(volumes) < 60 or np.sum(volumes) == 0:
            return Decimal("0.0")

        # Recent 20 days vs prior 40 days
        recent_avg = np.mean(volumes[-20:])
        prior_avg = np.mean(volumes[-60:-20])

        if prior_avg <= 0:
            return Decimal("0.0")

        accel = (recent_avg - prior_avg) / prior_avg
        # Normalize to [-1, 1] range (cap at +/-100%)
        accel = max(-1.0, min(1.0, accel))
        return Decimal(str(accel))

    def _compute_volatility(
        self, prices: np.ndarray, dates: np.ndarray, asof_date: date
    ) -> Decimal:
        """Compute annualized volatility (for risk adjustment)."""
        if len(prices) < 60:
            return Decimal("0.2")  # Default

        # Daily returns
        returns = np.diff(prices) / prices[:-1]
        returns = returns[-60:]  # Last 60 days

        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        return Decimal(str(annual_vol))

    def compute_target_weights(
        self, signals: list[StrategySignal], capital: Decimal
    ) -> dict[str, Decimal]:
        """
        Compute target weights using inverse volatility weighting.

        Args:
            signals: Sorted strategy signals
            capital: Capital allocated to this sleeve

        Returns:
            Dictionary mapping ticker to target weight
        """
        # Take top N
        top_signals = signals[: self.top_n]

        if not top_signals:
            return {}

        # Inverse volatility weighting
        weights = {}
        total_inv_vol = Decimal("0")

        for signal in top_signals:
            vol = signal.components.get("volatility", Decimal("0.2"))
            if vol <= 0:
                vol = Decimal("0.2")
            inv_vol = Decimal("1") / vol
            weights[signal.ticker] = inv_vol
            total_inv_vol += inv_vol

        # Normalize to sum to 1
        if total_inv_vol > 0:
            for ticker in weights:
                weights[ticker] = weights[ticker] / total_inv_vol

        # Apply max position size constraint (20% max)
        max_weight = Decimal("0.20")
        for ticker in weights:
            if weights[ticker] > max_weight:
                weights[ticker] = max_weight

        # Renormalize after capping
        total_weight = sum(weights.values())
        if total_weight > 0:
            for ticker in weights:
                weights[ticker] = weights[ticker] / total_weight

        return weights


# Global instance
momentum_strategy = MomentumStrategy()
