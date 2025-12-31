"""Portfolio risk analytics engine."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from scipy import stats

from portfolio.data.prices import price_fetcher
from portfolio.db.models import Allocation, RiskAnalytics
from portfolio.utils.logging import logger


class RiskAnalyticsEngine:
    """Compute portfolio-level risk metrics."""

    def __init__(self):
        """Initialize risk analytics engine."""
        self.lookback_days = 365

    def compute_risk_metrics(
        self,
        allocations: list[Allocation],
        asof_date: date,
    ) -> RiskAnalytics:
        """
        Compute comprehensive risk metrics for portfolio.

        Args:
            allocations: List of target allocations
            asof_date: Date to compute metrics as of

        Returns:
            RiskAnalytics object with computed metrics
        """
        start_date = asof_date - timedelta(days=self.lookback_days)

        # Get tickers and weights
        tickers = list(set(a.ticker for a in allocations))
        total_dollars = sum(a.target_dollars for a in allocations)

        if total_dollars == 0:
            return self._default_risk_analytics()

        # Build weights vector
        weights_dict = {}
        for alloc in allocations:
            if alloc.ticker in weights_dict:
                weights_dict[alloc.ticker] += float(alloc.target_dollars)
            else:
                weights_dict[alloc.ticker] = float(alloc.target_dollars)

        # Normalize to weights
        for ticker in weights_dict:
            weights_dict[ticker] /= float(total_dollars)

        # Fetch price data
        logger.info(f"Fetching price data for risk analytics: {len(tickers)} tickers")
        price_data = price_fetcher.fetch_prices(tickers, start_date, asof_date)

        # Also fetch SPY for beta
        spy_data = price_fetcher.fetch_prices(["SPY"], start_date, asof_date)

        # Build returns matrix
        returns_dict = {}
        for ticker in tickers:
            if ticker not in price_data or len(price_data[ticker]) < 60:
                logger.warning(f"Insufficient data for {ticker}")
                continue

            prices = np.array([float(p.adj_close) for p in price_data[ticker]])
            returns = np.diff(prices) / prices[:-1]
            returns_dict[ticker] = returns

        if not returns_dict:
            logger.warning("No valid return data, returning default metrics")
            return self._default_risk_analytics()

        # SPY returns
        spy_returns = None
        if "SPY" in spy_data and len(spy_data["SPY"]) > 60:
            spy_prices = np.array([float(p.adj_close) for p in spy_data["SPY"]])
            spy_returns = np.diff(spy_prices) / spy_prices[:-1]

        # Compute metrics
        beta = self._compute_portfolio_beta(returns_dict, weights_dict, spy_returns)
        volatility = self._compute_portfolio_volatility(returns_dict, weights_dict)
        sharpe = self._compute_sharpe_ratio(returns_dict, weights_dict)
        max_dd = self._compute_max_drawdown(returns_dict, weights_dict)
        corr_avg = self._compute_avg_correlation(returns_dict, weights_dict)

        analytics = RiskAnalytics(
            beta_spy=beta,
            volatility_annual=volatility,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            correlation_avg=corr_avg,
        )

        logger.info(
            f"Risk metrics: beta={beta:.2f}, vol={volatility:.2%}, "
            f"sharpe={sharpe:.2f}, maxdd={max_dd:.2%}"
        )

        return analytics

    def _compute_portfolio_beta(
        self,
        returns_dict: dict[str, np.ndarray],
        weights: dict[str, float],
        spy_returns: np.ndarray | None,
    ) -> Decimal:
        """Compute portfolio beta vs SPY."""
        if spy_returns is None or len(spy_returns) < 60:
            return Decimal("1.0")

        # Compute portfolio returns
        port_returns = self._compute_portfolio_returns(returns_dict, weights)

        if port_returns is None or len(port_returns) < 60:
            return Decimal("1.0")

        # Align lengths
        min_len = min(len(port_returns), len(spy_returns))
        port_ret = port_returns[-min_len:]
        spy_ret = spy_returns[-min_len:]

        # Linear regression
        slope, _, _, _, _ = stats.linregress(spy_ret, port_ret)
        return Decimal(str(slope))

    def _compute_portfolio_volatility(
        self, returns_dict: dict[str, np.ndarray], weights: dict[str, float]
    ) -> Decimal:
        """Compute annualized portfolio volatility."""
        port_returns = self._compute_portfolio_returns(returns_dict, weights)

        if port_returns is None or len(port_returns) < 30:
            return Decimal("0.15")

        daily_vol = np.std(port_returns)
        annual_vol = daily_vol * np.sqrt(252)
        return Decimal(str(annual_vol))

    def _compute_sharpe_ratio(
        self, returns_dict: dict[str, np.ndarray], weights: dict[str, float]
    ) -> Decimal:
        """Compute Sharpe ratio (assuming 0% risk-free rate)."""
        port_returns = self._compute_portfolio_returns(returns_dict, weights)

        if port_returns is None or len(port_returns) < 30:
            return Decimal("0.0")

        mean_return = np.mean(port_returns)
        std_return = np.std(port_returns)

        if std_return == 0:
            return Decimal("0.0")

        # Annualize
        annual_return = mean_return * 252
        annual_vol = std_return * np.sqrt(252)

        sharpe = annual_return / annual_vol
        return Decimal(str(sharpe))

    def _compute_max_drawdown(
        self, returns_dict: dict[str, np.ndarray], weights: dict[str, float]
    ) -> Decimal:
        """Compute maximum drawdown."""
        port_returns = self._compute_portfolio_returns(returns_dict, weights)

        if port_returns is None or len(port_returns) < 30:
            return Decimal("0.0")

        # Cumulative returns
        cum_returns = np.cumprod(1 + port_returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdowns = (cum_returns - running_max) / running_max

        max_dd = np.min(drawdowns)
        return Decimal(str(abs(max_dd)))

    def _compute_avg_correlation(
        self, returns_dict: dict[str, np.ndarray], weights: dict[str, float]
    ) -> Decimal:
        """Compute average pairwise correlation."""
        tickers = [t for t in returns_dict.keys() if weights.get(t, 0) > 0.01]

        if len(tickers) < 2:
            return Decimal("1.0")

        # Align returns
        min_len = min(len(returns_dict[t]) for t in tickers)
        aligned_returns = np.array([returns_dict[t][-min_len:] for t in tickers])

        # Correlation matrix
        corr_matrix = np.corrcoef(aligned_returns)

        # Average off-diagonal elements
        n = len(tickers)
        if n < 2:
            return Decimal("1.0")

        sum_corr = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                sum_corr += corr_matrix[i, j]
                count += 1

        avg_corr = sum_corr / count if count > 0 else 1.0
        return Decimal(str(avg_corr))

    def _compute_portfolio_returns(
        self, returns_dict: dict[str, np.ndarray], weights: dict[str, float]
    ) -> np.ndarray | None:
        """Compute portfolio returns from individual returns and weights."""
        tickers = [t for t in returns_dict.keys() if weights.get(t, 0) > 0]

        if not tickers:
            return None

        # Align lengths
        min_len = min(len(returns_dict[t]) for t in tickers)
        aligned_returns = {t: returns_dict[t][-min_len:] for t in tickers}

        # Weighted sum
        port_returns = np.zeros(min_len)
        for ticker in tickers:
            weight = weights.get(ticker, 0)
            port_returns += weight * aligned_returns[ticker]

        return port_returns

    def _default_risk_analytics(self) -> RiskAnalytics:
        """Return default risk analytics when computation fails."""
        return RiskAnalytics(
            beta_spy=Decimal("1.0"),
            volatility_annual=Decimal("0.15"),
            sharpe_ratio=Decimal("0.0"),
            max_drawdown=Decimal("0.0"),
            correlation_avg=Decimal("0.5"),
        )

    def compute_correlation_matrix(
        self, allocations: list[Allocation], asof_date: date
    ) -> dict[tuple[str, str], Decimal]:
        """Compute pairwise correlation matrix."""
        start_date = asof_date - timedelta(days=self.lookback_days)
        tickers = list(set(a.ticker for a in allocations))

        price_data = price_fetcher.fetch_prices(tickers, start_date, asof_date)

        # Build returns
        returns_dict = {}
        for ticker in tickers:
            if ticker not in price_data or len(price_data[ticker]) < 60:
                continue

            prices = np.array([float(p.adj_close) for p in price_data[ticker]])
            returns = np.diff(prices) / prices[:-1]
            returns_dict[ticker] = returns

        if len(returns_dict) < 2:
            return {}

        # Align
        valid_tickers = list(returns_dict.keys())
        min_len = min(len(returns_dict[t]) for t in valid_tickers)
        aligned_returns = np.array([returns_dict[t][-min_len:] for t in valid_tickers])

        # Correlation matrix
        corr_matrix = np.corrcoef(aligned_returns)

        # Convert to dict
        correlations = {}
        for i, ticker1 in enumerate(valid_tickers):
            for j, ticker2 in enumerate(valid_tickers):
                if i < j:  # Only store upper triangle
                    correlations[(ticker1, ticker2)] = Decimal(str(corr_matrix[i, j]))

        return correlations


# Global instance
risk_analytics = RiskAnalyticsEngine()
