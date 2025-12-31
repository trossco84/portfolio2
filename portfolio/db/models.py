"""Pydantic models for database schemas."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RunMode(str, Enum):
    """Portfolio run mode."""

    PAPER = "paper"
    LIVE = "live"
    INITIAL = "initial"
    BACKTEST = "backtest"


class Sleeve(str, Enum):
    """Portfolio sleeve names."""

    MOMENTUM = "momentum"
    FUTURISTIC = "futuristic"
    REALWORLD = "realworld"
    RISK = "risk"
    CASH = "cash"


class OrderSide(str, Enum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# Database models


class Run(BaseModel):
    """Portfolio run metadata."""

    id: Optional[int] = None
    asof_date: date
    created_at: Optional[datetime] = None
    nav_total: Decimal
    nav_momentum: Optional[Decimal] = None
    nav_futuristic: Optional[Decimal] = None
    nav_realworld: Optional[Decimal] = None
    nav_risk: Optional[Decimal] = None
    nav_cash: Optional[Decimal] = None
    mode: RunMode = RunMode.PAPER
    notes: Optional[str] = None


class Price(BaseModel):
    """Historical price data."""

    id: Optional[int] = None
    ticker: str
    date: date
    adj_close: Decimal
    close: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    volume: Optional[int] = None
    source: str = "yfinance"
    created_at: Optional[datetime] = None


class Signal(BaseModel):
    """Strategy signal."""

    id: Optional[int] = None
    run_id: int
    sleeve: Sleeve
    ticker: str
    signal_name: str
    value: Decimal
    created_at: Optional[datetime] = None


class Allocation(BaseModel):
    """Target allocation."""

    id: Optional[int] = None
    run_id: int
    sleeve: Sleeve
    ticker: str
    target_weight: Decimal
    target_dollars: Decimal
    created_at: Optional[datetime] = None


class Position(BaseModel):
    """Current position."""

    id: Optional[int] = None
    run_id: int
    sleeve: Sleeve
    ticker: str
    shares: Decimal
    avg_cost: Optional[Decimal] = None
    market_price: Decimal
    market_value: Decimal
    created_at: Optional[datetime] = None


class Order(BaseModel):
    """Trade order."""

    id: Optional[int] = None
    run_id: int
    sleeve: Sleeve
    ticker: str
    side: OrderSide
    qty: Decimal
    notional: Decimal
    limit_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None
    filled_qty: Optional[Decimal] = None
    filled_avg_price: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RiskMetric(BaseModel):
    """Risk metric value."""

    id: Optional[int] = None
    run_id: int
    metric_name: str
    metric_value: Decimal
    created_at: Optional[datetime] = None


class Correlation(BaseModel):
    """Pairwise correlation."""

    id: Optional[int] = None
    run_id: int
    ticker1: str
    ticker2: str
    correlation: Decimal
    created_at: Optional[datetime] = None


# Domain models (not directly mapped to tables)


class PriceFrame(BaseModel):
    """Price data for analysis."""

    ticker: str
    dates: list[date]
    prices: list[Decimal]
    volumes: Optional[list[int]] = None


class StrategySignal(BaseModel):
    """Computed strategy signal."""

    ticker: str
    score: Decimal
    components: dict[str, Decimal] = Field(default_factory=dict)


class PortfolioAllocation(BaseModel):
    """Portfolio allocation target."""

    sleeve: Sleeve
    ticker: str
    weight: Decimal
    dollars: Decimal


class TradeOrder(BaseModel):
    """Trade order to execute."""

    sleeve: Sleeve
    ticker: str
    side: OrderSide
    qty: Decimal
    notional: Decimal
    limit_price: Optional[Decimal] = None
    reason: str = ""


class RiskAnalytics(BaseModel):
    """Portfolio risk analytics."""

    beta_spy: Decimal
    volatility_annual: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    correlation_avg: Decimal
    var_95: Optional[Decimal] = None
