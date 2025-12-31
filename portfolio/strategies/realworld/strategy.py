"""Real-world strategy: physical/industrials/staples, resilient cash flow focus."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from scipy import stats

from portfolio.data.prices import price_fetcher
from portfolio.data.universes import REALWORLD_UNIVERSE
from portfolio.db.models import Price, StrategySignal
from portfolio.utils.logging import logger


class RealWorldStrategy:
    """
    Real-world strategy focusing on:
    - Low beta (defensive)
    - Stable momentum (lower volatility preferred)
    - Dividend yield proxy (using price stability as proxy)
    - Rebalances semi-annually
    """

    def __init__(self):
        """Initialize real-world strategy."""
        self.universe = REALWORLD_UNIVERSE
        self.top_n = 15  # Hold 15 positions for diversification
        self.lookback_days = 365

    def generate_signals(self, asof_date: date) -> list[StrategySignal]:
        """Generate real-world signals."""
        start_date = asof_date - timedelta(days=self.lookback_days)

        logger.info(f"Fetching real-world universe prices from {start_date} to {asof_date}")
        price_data = price_fetcher.fetch_prices(self.universe, start_date, asof_date)

        # Also fetch SPY for beta calculation
        spy_data = price_fetcher.fetch_prices(["SPY"], start_date, asof_date)
        spy_returns = None
        if "SPY" in spy_data and len(spy_data["SPY"]) > 60:
            spy_prices = np.array([float(p.adj_close) for p in spy_data["SPY"]])
            spy_returns = np.diff(spy_prices) / spy_prices[:-1]

        signals = []
        for ticker in self.universe:
            if ticker not in price_data or len(price_data[ticker]) < 120:
                logger.warning(f"Insufficient data for {ticker}, skipping")
                continue

            try:
                signal = self._compute_signal(
                    ticker, price_data[ticker], asof_date, spy_returns
                )
                signals.append(signal)
            except Exception as e:
                logger.error(f"Error computing signal for {ticker}: {e}")
                continue

        signals.sort(key=lambda s: s.score, reverse=True)
        logger.info(f"Generated {len(signals)} real-world signals")

        return signals

    def _compute_signal(
        self,
        ticker: str,
        prices: list[Price],
        asof_date: date,
        spy_returns: np.ndarray | None,
    ) -> StrategySignal:
        """Compute real-world signal."""
        dates = np.array([p.date for p in prices])
        adj_close = np.array([float(p.adj_close) for p in prices])

        # Price stability (lower volatility is better)
        returns = np.diff(adj_close) / adj_close[:-1]
        volatility = np.std(returns[-252:]) if len(returns) >= 252 else np.std(returns)
        stability_score = Decimal("1") / Decimal(str(max(volatility, 0.01)))

        # Beta (lower is better for defensive)
        beta = self._compute_beta(returns, spy_returns) if spy_returns is not None else Decimal("1.0")
        beta_score = Decimal("2.0") - beta  # Lower beta = higher score

        # Stable momentum (6 month)
        momentum_6m = self._compute_return(adj_close, dates, asof_date, months=6)

        # Composite score (weights: stability=0.4, beta=0.3, momentum=0.3)
        composite_score = (
            Decimal("0.4") * stability_score +
            Decimal("0.3") * beta_score +
            Decimal("0.3") * momentum_6m
        )

        return StrategySignal(
            ticker=ticker,
            score=composite_score,
            components={
                "stability": stability_score,
                "beta": beta,
                "beta_score": beta_score,
                "momentum_6m": momentum_6m,
                "volatility": Decimal(str(volatility)),
            },
        )

    def _compute_return(
        self, prices: np.ndarray, dates: np.ndarray, asof_date: date, months: int
    ) -> Decimal:
        """Compute total return over N months."""
        lookback_date = asof_date - timedelta(days=months * 30)
        current_price = prices[-1]
        lookback_idx = np.searchsorted(dates, lookback_date)

        if lookback_idx >= len(prices):
            return Decimal("0.0")

        lookback_price = prices[lookback_idx]
        if lookback_price <= 0:
            return Decimal("0.0")

        return_pct = (current_price - lookback_price) / lookback_price
        return Decimal(str(return_pct))

    def _compute_beta(self, returns: np.ndarray, spy_returns: np.ndarray) -> Decimal:
        """Compute beta vs SPY."""
        # Align lengths
        min_len = min(len(returns), len(spy_returns))
        if min_len < 60:
            return Decimal("1.0")

        stock_ret = returns[-min_len:]
        market_ret = spy_returns[-min_len:]

        # Linear regression
        slope, _, _, _, _ = stats.linregress(market_ret, stock_ret)
        return Decimal(str(slope))

    def compute_target_weights(
        self, signals: list[StrategySignal], capital: Decimal
    ) -> dict[str, Decimal]:
        """Compute target weights with equal weighting."""
        top_signals = signals[: self.top_n]

        if not top_signals:
            return {}

        # Equal weight
        weight = Decimal("1") / Decimal(str(len(top_signals)))
        weights = {signal.ticker: weight for signal in top_signals}

        return weights


# Global instance
realworld_strategy = RealWorldStrategy()
