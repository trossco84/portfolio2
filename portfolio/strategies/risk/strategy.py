"""Risk/hedge strategy: ETF-based portfolio optimization."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from scipy import stats

from portfolio.data.prices import price_fetcher
from portfolio.data.universes import RISK_UNIVERSE
from portfolio.db.models import Price, StrategySignal
from portfolio.utils.logging import logger

# Try to import cvxpy, fall back to heuristic if not available
try:
    import cvxpy as cp

    HAS_CVXPY = True
except ImportError:
    HAS_CVXPY = False
    logger.warning("cvxpy not installed, will use heuristic optimizer")


class RiskStrategy:
    """
    Risk/hedge strategy using portfolio optimization:
    - Universe: ETFs (equities, bonds, commodities, real estate)
    - Weekly optimization
    - Objective: maximize Sharpe ratio
    - Constraints: long-only, beta <= 1.1, max weight 35%
    """

    def __init__(self):
        """Initialize risk strategy."""
        self.universe = RISK_UNIVERSE
        self.lookback_days = 365
        self.max_beta = Decimal("1.1")
        self.max_weight = Decimal("0.35")

    def generate_signals(self, asof_date: date) -> list[StrategySignal]:
        """
        Generate optimized allocations.

        For risk sleeve, signals represent the optimized weights.
        """
        start_date = asof_date - timedelta(days=self.lookback_days)

        logger.info(f"Fetching risk universe prices from {start_date} to {asof_date}")
        price_data = price_fetcher.fetch_prices(self.universe, start_date, asof_date)

        # Filter to tickers with sufficient data
        valid_tickers = [
            t for t in self.universe if t in price_data and len(price_data[t]) >= 252
        ]

        if len(valid_tickers) < 3:
            logger.error("Insufficient data for risk optimization")
            return []

        # Compute returns matrix
        returns_matrix = self._build_returns_matrix(price_data, valid_tickers)

        # Compute expected returns and covariance
        expected_returns = self._compute_expected_returns(returns_matrix)
        cov_matrix = np.cov(returns_matrix, rowvar=True)

        # Get SPY beta for each asset
        spy_idx = valid_tickers.index("SPY") if "SPY" in valid_tickers else None
        spy_returns = returns_matrix[spy_idx] if spy_idx is not None else None

        betas = {}
        for i, ticker in enumerate(valid_tickers):
            if spy_returns is not None and ticker != "SPY":
                beta = self._compute_beta(returns_matrix[i], spy_returns)
                betas[ticker] = beta
            else:
                betas[ticker] = Decimal("1.0")

        # Run optimizer
        if HAS_CVXPY:
            weights = self._optimize_cvxpy(
                valid_tickers, expected_returns, cov_matrix, betas
            )
        else:
            weights = self._optimize_heuristic(
                valid_tickers, expected_returns, cov_matrix, betas
            )

        # Convert to signals
        signals = []
        for ticker, weight in weights.items():
            if weight > Decimal("0.001"):  # Filter tiny weights
                signal = StrategySignal(
                    ticker=ticker,
                    score=weight,  # Score is the weight
                    components={
                        "weight": weight,
                        "beta": betas.get(ticker, Decimal("1.0")),
                    },
                )
                signals.append(signal)

        logger.info(f"Optimized {len(signals)} risk allocations")
        return signals

    def _build_returns_matrix(
        self, price_data: dict[str, list[Price]], tickers: list[str]
    ) -> np.ndarray:
        """Build returns matrix (weekly returns)."""
        # Convert to numpy arrays of weekly returns
        returns_list = []

        for ticker in tickers:
            prices = np.array([float(p.adj_close) for p in price_data[ticker]])
            # Downsample to weekly (every 5 days)
            weekly_prices = prices[::5]
            weekly_returns = np.diff(weekly_prices) / weekly_prices[:-1]
            returns_list.append(weekly_returns)

        # Align lengths
        min_len = min(len(r) for r in returns_list)
        returns_matrix = np.array([r[-min_len:] for r in returns_list])

        return returns_matrix

    def _compute_expected_returns(self, returns_matrix: np.ndarray) -> np.ndarray:
        """Compute expected returns (trailing 6-month mean)."""
        # Use last 26 weeks (6 months)
        recent_returns = returns_matrix[:, -26:]
        expected = np.mean(recent_returns, axis=1)
        return expected

    def _compute_beta(self, returns: np.ndarray, spy_returns: np.ndarray) -> Decimal:
        """Compute beta vs SPY."""
        min_len = min(len(returns), len(spy_returns))
        if min_len < 30:
            return Decimal("1.0")

        stock_ret = returns[-min_len:]
        market_ret = spy_returns[-min_len:]

        slope, _, _, _, _ = stats.linregress(market_ret, stock_ret)
        return Decimal(str(slope))

    def _optimize_cvxpy(
        self,
        tickers: list[str],
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        betas: dict[str, Decimal],
    ) -> dict[str, Decimal]:
        """Optimize using cvxpy (maximize Sharpe ratio)."""
        n = len(tickers)
        weights = cp.Variable(n)

        # Portfolio return and variance
        port_return = expected_returns @ weights
        port_variance = cp.quad_form(weights, cov_matrix)
        port_std = cp.sqrt(port_variance)

        # Maximize Sharpe ratio (approximate with return/std)
        # Note: For numerical stability, we minimize -return/std
        objective = cp.Maximize(port_return / port_std)

        # Constraints
        constraints = [
            cp.sum(weights) == 1,  # Fully invested
            weights >= 0,  # Long only
            weights <= float(self.max_weight),  # Max position size
        ]

        # Beta constraint (portfolio beta <= max_beta)
        beta_array = np.array([float(betas.get(t, Decimal("1.0"))) for t in tickers])
        port_beta = beta_array @ weights
        constraints.append(port_beta <= float(self.max_beta))

        # Solve
        problem = cp.Problem(objective, constraints)

        try:
            problem.solve(solver=cp.ECOS, max_iters=1000)

            if problem.status == cp.OPTIMAL:
                opt_weights = weights.value
                result = {
                    tickers[i]: Decimal(str(max(0, opt_weights[i])))
                    for i in range(n)
                }
                logger.info(f"CVXPY optimization successful, Sharpe proxy: {problem.value:.3f}")
                return result
            else:
                logger.warning(f"CVXPY optimization failed: {problem.status}, using fallback")
                return self._optimize_heuristic(tickers, expected_returns, cov_matrix, betas)

        except Exception as e:
            logger.error(f"CVXPY error: {e}, using fallback")
            return self._optimize_heuristic(tickers, expected_returns, cov_matrix, betas)

    def _optimize_heuristic(
        self,
        tickers: list[str],
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        betas: dict[str, Decimal],
    ) -> dict[str, Decimal]:
        """Heuristic optimizer: inverse variance weighting with constraints."""
        logger.info("Using heuristic optimizer")

        # Compute volatilities
        vols = np.sqrt(np.diag(cov_matrix))

        # Inverse vol weights
        inv_vol = 1.0 / vols
        weights = inv_vol / np.sum(inv_vol)

        # Apply max weight constraint
        weights = np.minimum(weights, float(self.max_weight))
        weights = weights / np.sum(weights)  # Renormalize

        # Check beta constraint
        beta_array = np.array([float(betas.get(t, Decimal("1.0"))) for t in tickers])
        port_beta = np.dot(beta_array, weights)

        # If beta too high, reduce equity exposure
        if port_beta > float(self.max_beta):
            # Increase bond/defensive allocation
            for i, ticker in enumerate(tickers):
                if ticker in ["IEF", "TLT", "LQD", "TIP"]:
                    weights[i] *= 1.2
                elif ticker in ["SPY"]:
                    weights[i] *= 0.8

            weights = weights / np.sum(weights)

        result = {tickers[i]: Decimal(str(weights[i])) for i in range(len(tickers))}
        return result

    def compute_target_weights(
        self, signals: list[StrategySignal], capital: Decimal
    ) -> dict[str, Decimal]:
        """For risk strategy, signals already contain optimal weights."""
        weights = {}
        total_weight = Decimal("0")

        for signal in signals:
            weight = signal.components.get("weight", signal.score)
            weights[signal.ticker] = weight
            total_weight += weight

        # Normalize to ensure sum = 1
        if total_weight > 0:
            for ticker in weights:
                weights[ticker] = weights[ticker] / total_weight

        return weights


# Global instance
risk_strategy = RiskStrategy()
