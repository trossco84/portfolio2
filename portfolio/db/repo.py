"""Data access layer for database operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from portfolio.db.client import db_client
from portfolio.db.models import (
    Allocation,
    Correlation,
    Order,
    Position,
    Price,
    RiskMetric,
    Run,
    Signal,
)
from portfolio.utils.logging import logger


class PortfolioRepository:
    """Repository for portfolio data operations."""

    def __init__(self):
        """Initialize repository."""
        self.db = db_client

    # Runs

    def create_run(self, run: Run) -> int:
        """Create a new run and return its ID."""
        query = """
            INSERT INTO runs (asof_date, nav_total, nav_momentum, nav_futuristic,
                              nav_realworld, nav_risk, nav_cash, mode, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            run.asof_date,
            run.nav_total,
            run.nav_momentum,
            run.nav_futuristic,
            run.nav_realworld,
            run.nav_risk,
            run.nav_cash,
            run.mode.value,
            run.notes,
        )
        return self.db.execute_insert(query, params)

    def get_run(self, run_id: int) -> Optional[Run]:
        """Get run by ID."""
        query = "SELECT * FROM runs WHERE id = %s"
        result = self.db.execute_one(query, (run_id,))
        return Run(**result) if result else None

    def get_run_by_date(self, asof_date: date) -> Optional[Run]:
        """Get run by asof_date."""
        query = "SELECT * FROM runs WHERE asof_date = %s"
        result = self.db.execute_one(query, (asof_date,))
        return Run(**result) if result else None

    def get_latest_run(self) -> Optional[Run]:
        """Get most recent run."""
        query = "SELECT * FROM runs ORDER BY asof_date DESC LIMIT 1"
        result = self.db.execute_one(query)
        return Run(**result) if result else None

    def list_runs(self, limit: int = 50) -> list[Run]:
        """List recent runs."""
        query = "SELECT * FROM runs ORDER BY asof_date DESC LIMIT %s"
        results = self.db.execute_query(query, (limit,))
        return [Run(**r) for r in results]

    # Prices

    def upsert_price(self, price: Price) -> None:
        """Insert or update price data."""
        query = """
            INSERT INTO prices (ticker, date, adj_close, close, open, high, low, volume, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, date)
            DO UPDATE SET
                adj_close = EXCLUDED.adj_close,
                close = EXCLUDED.close,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                volume = EXCLUDED.volume
        """
        params = (
            price.ticker,
            price.date,
            price.adj_close,
            price.close,
            price.open,
            price.high,
            price.low,
            price.volume,
            price.source,
        )
        self.db.execute_update(query, params)

    def bulk_upsert_prices(self, prices: list[Price]) -> None:
        """Bulk insert/update prices."""
        for price in prices:
            self.upsert_price(price)
        logger.info(f"Upserted {len(prices)} price records")

    def get_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[Price]:
        """Get price history for a ticker."""
        query = """
            SELECT * FROM prices
            WHERE ticker = %s AND date >= %s AND date <= %s
            ORDER BY date ASC
        """
        results = self.db.execute_query(query, (ticker, start_date, end_date))
        return [Price(**r) for r in results]

    def get_latest_price(self, ticker: str, asof_date: date) -> Optional[Price]:
        """Get most recent price for ticker on or before asof_date."""
        query = """
            SELECT * FROM prices
            WHERE ticker = %s AND date <= %s
            ORDER BY date DESC LIMIT 1
        """
        result = self.db.execute_one(query, (ticker, asof_date))
        return Price(**result) if result else None

    # Signals

    def create_signal(self, signal: Signal) -> int:
        """Create a signal."""
        query = """
            INSERT INTO signals (run_id, sleeve, ticker, signal_name, value)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (signal.run_id, signal.sleeve.value, signal.ticker, signal.signal_name, signal.value)
        return self.db.execute_insert(query, params)

    def bulk_create_signals(self, signals: list[Signal]) -> None:
        """Bulk create signals."""
        for signal in signals:
            self.create_signal(signal)

    def get_signals(self, run_id: int, sleeve: Optional[str] = None) -> list[Signal]:
        """Get signals for a run."""
        if sleeve:
            query = "SELECT * FROM signals WHERE run_id = %s AND sleeve = %s"
            params = (run_id, sleeve)
        else:
            query = "SELECT * FROM signals WHERE run_id = %s"
            params = (run_id,)
        results = self.db.execute_query(query, params)
        return [Signal(**r) for r in results]

    # Allocations

    def create_allocation(self, allocation: Allocation) -> int:
        """Create an allocation."""
        query = """
            INSERT INTO allocations (run_id, sleeve, ticker, target_weight, target_dollars)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            allocation.run_id,
            allocation.sleeve.value,
            allocation.ticker,
            allocation.target_weight,
            allocation.target_dollars,
        )
        return self.db.execute_insert(query, params)

    def bulk_create_allocations(self, allocations: list[Allocation]) -> None:
        """Bulk create allocations."""
        for allocation in allocations:
            self.create_allocation(allocation)

    def get_allocations(self, run_id: int, sleeve: Optional[str] = None) -> list[Allocation]:
        """Get allocations for a run."""
        if sleeve:
            query = "SELECT * FROM allocations WHERE run_id = %s AND sleeve = %s"
            params = (run_id, sleeve)
        else:
            query = "SELECT * FROM allocations WHERE run_id = %s"
            params = (run_id,)
        results = self.db.execute_query(query, params)
        return [Allocation(**r) for r in results]

    # Positions

    def create_position(self, position: Position) -> int:
        """Create a position."""
        query = """
            INSERT INTO positions (run_id, sleeve, ticker, shares, avg_cost, market_price, market_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            position.run_id,
            position.sleeve.value,
            position.ticker,
            position.shares,
            position.avg_cost,
            position.market_price,
            position.market_value,
        )
        return self.db.execute_insert(query, params)

    def bulk_create_positions(self, positions: list[Position]) -> None:
        """Bulk create positions."""
        for position in positions:
            self.create_position(position)

    def get_positions(self, run_id: int, sleeve: Optional[str] = None) -> list[Position]:
        """Get positions for a run."""
        if sleeve:
            query = "SELECT * FROM positions WHERE run_id = %s AND sleeve = %s"
            params = (run_id, sleeve)
        else:
            query = "SELECT * FROM positions WHERE run_id = %s"
            params = (run_id,)
        results = self.db.execute_query(query, params)
        return [Position(**r) for r in results]

    # Orders

    def create_order(self, order: Order) -> int:
        """Create an order."""
        query = """
            INSERT INTO orders (run_id, sleeve, ticker, side, qty, notional, limit_price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            order.run_id,
            order.sleeve.value,
            order.ticker,
            order.side.value,
            order.qty,
            order.notional,
            order.limit_price,
            order.status.value,
        )
        return self.db.execute_insert(query, params)

    def bulk_create_orders(self, orders: list[Order]) -> None:
        """Bulk create orders."""
        for order in orders:
            self.create_order(order)

    def get_orders(self, run_id: int) -> list[Order]:
        """Get orders for a run."""
        query = "SELECT * FROM orders WHERE run_id = %s ORDER BY created_at"
        results = self.db.execute_query(query, (run_id,))
        return [Order(**r) for r in results]

    def update_order_status(
        self,
        order_id: int,
        status: str,
        broker_order_id: Optional[str] = None,
        filled_qty: Optional[Decimal] = None,
        filled_avg_price: Optional[Decimal] = None,
    ) -> None:
        """Update order status."""
        query = """
            UPDATE orders
            SET status = %s, broker_order_id = %s, filled_qty = %s,
                filled_avg_price = %s, updated_at = NOW()
            WHERE id = %s
        """
        params = (status, broker_order_id, filled_qty, filled_avg_price, order_id)
        self.db.execute_update(query, params)

    # Risk Metrics

    def create_risk_metric(self, metric: RiskMetric) -> int:
        """Create a risk metric."""
        query = """
            INSERT INTO risk_metrics (run_id, metric_name, metric_value)
            VALUES (%s, %s, %s)
        """
        params = (metric.run_id, metric.metric_name, metric.metric_value)
        return self.db.execute_insert(query, params)

    def bulk_create_risk_metrics(self, metrics: list[RiskMetric]) -> None:
        """Bulk create risk metrics."""
        for metric in metrics:
            self.create_risk_metric(metric)

    def get_risk_metrics(self, run_id: int) -> list[RiskMetric]:
        """Get risk metrics for a run."""
        query = "SELECT * FROM risk_metrics WHERE run_id = %s"
        results = self.db.execute_query(query, (run_id,))
        return [RiskMetric(**r) for r in results]

    # Correlations

    def create_correlation(self, correlation: Correlation) -> int:
        """Create a correlation entry."""
        query = """
            INSERT INTO correlations (run_id, ticker1, ticker2, correlation)
            VALUES (%s, %s, %s, %s)
        """
        params = (correlation.run_id, correlation.ticker1, correlation.ticker2, correlation.correlation)
        return self.db.execute_insert(query, params)

    def bulk_create_correlations(self, correlations: list[Correlation]) -> None:
        """Bulk create correlations."""
        for corr in correlations:
            self.create_correlation(corr)

    def get_correlations(self, run_id: int) -> list[Correlation]:
        """Get correlations for a run."""
        query = "SELECT * FROM correlations WHERE run_id = %s"
        results = self.db.execute_query(query, (run_id,))
        return [Correlation(**r) for r in results]


# Global repository instance
repo = PortfolioRepository()
