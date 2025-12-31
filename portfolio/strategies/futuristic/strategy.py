"""Futuristic strategy: robotics-heavy thematic with AI infra and nuclear."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np

from portfolio.data.prices import price_fetcher
from portfolio.data.universes import FUTURISTIC_UNIVERSE
from portfolio.db.models import Price, StrategySignal
from portfolio.utils.logging import logger


# Theme weights (higher = more important)
THEME_WEIGHTS = {
    # Robotics & Automation (highest weight)
    "ISRG": Decimal("1.5"),
    "ABB": Decimal("1.5"),
    "ROK": Decimal("1.5"),
    "EMR": Decimal("1.5"),
    "IRBT": Decimal("1.4"),
    # AI Infrastructure (high weight)
    "NVDA": Decimal("1.3"),
    "AMD": Decimal("1.3"),
    "AVGO": Decimal("1.3"),
    "ASML": Decimal("1.3"),
    # AI Software (medium-high)
    "PLTR": Decimal("1.2"),
    "PATH": Decimal("1.2"),
    "AI": Decimal("1.2"),
    "SNOW": Decimal("1.2"),
    # Nuclear (medium)
    "CEG": Decimal("1.1"),
    "VST": Decimal("1.1"),
    "SMR": Decimal("1.1"),
    "CCJ": Decimal("1.1"),
    "NEE": Decimal("1.0"),
}


class FuturisticStrategy:
    """
    Futuristic thematic strategy:
    - Robotics heavy (higher theme weights)
    - AI infrastructure
    - Nuclear energy
    - Momentum + theme scoring
    - Rebalances quarterly
    """

    def __init__(self):
        """Initialize futuristic strategy."""
        self.universe = FUTURISTIC_UNIVERSE
        self.top_n = 12  # Hold 12 positions
        self.lookback_days = 365

    def generate_signals(self, asof_date: date) -> list[StrategySignal]:
        """Generate futuristic theme signals."""
        start_date = asof_date - timedelta(days=self.lookback_days)

        logger.info(f"Fetching futuristic universe prices from {start_date} to {asof_date}")
        price_data = price_fetcher.fetch_prices(self.universe, start_date, asof_date)

        signals = []
        for ticker in self.universe:
            if ticker not in price_data or len(price_data[ticker]) < 120:
                logger.warning(f"Insufficient data for {ticker}, skipping")
                continue

            try:
                signal = self._compute_signal(ticker, price_data[ticker], asof_date)
                signals.append(signal)
            except Exception as e:
                logger.error(f"Error computing signal for {ticker}: {e}")
                continue

        signals.sort(key=lambda s: s.score, reverse=True)
        logger.info(f"Generated {len(signals)} futuristic signals")

        return signals

    def _compute_signal(
        self, ticker: str, prices: list[Price], asof_date: date
    ) -> StrategySignal:
        """Compute futuristic theme signal."""
        dates = np.array([p.date for p in prices])
        adj_close = np.array([float(p.adj_close) for p in prices])

        # Momentum (6 and 12 month)
        momentum_6m = self._compute_return(adj_close, dates, asof_date, months=6)
        momentum_12m = self._compute_return(adj_close, dates, asof_date, months=12)

        # Average momentum
        momentum_score = (momentum_6m + momentum_12m) / Decimal("2")

        # Theme weight
        theme_weight = THEME_WEIGHTS.get(ticker, Decimal("1.0"))

        # Composite: momentum * theme_weight
        # This gives higher theme stocks a boost
        composite_score = momentum_score * theme_weight

        return StrategySignal(
            ticker=ticker,
            score=composite_score,
            components={
                "momentum_6m": momentum_6m,
                "momentum_12m": momentum_12m,
                "theme_weight": theme_weight,
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

    def compute_target_weights(
        self, signals: list[StrategySignal], capital: Decimal
    ) -> dict[str, Decimal]:
        """Compute target weights with equal weighting (quarterly rebalance)."""
        top_signals = signals[: self.top_n]

        if not top_signals:
            return {}

        # Equal weight
        weight = Decimal("1") / Decimal(str(len(top_signals)))
        weights = {signal.ticker: weight for signal in top_signals}

        return weights


# Global instance
futuristic_strategy = FuturisticStrategy()
