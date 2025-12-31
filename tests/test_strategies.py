"""Tests for strategy modules."""

from datetime import date
from decimal import Decimal

import pytest

from portfolio.db.models import StrategySignal
from portfolio.strategies.momentum.strategy import MomentumStrategy
from portfolio.strategies.futuristic.strategy import FuturisticStrategy
from portfolio.strategies.realworld.strategy import RealWorldStrategy
from portfolio.strategies.risk.strategy import RiskStrategy


def test_momentum_strategy_weights():
    """Test momentum strategy weight computation."""
    strategy = MomentumStrategy()

    # Create mock signals
    signals = [
        StrategySignal(
            ticker="AAPL",
            score=Decimal("0.5"),
            components={"volatility": Decimal("0.2")},
        ),
        StrategySignal(
            ticker="MSFT",
            score=Decimal("0.3"),
            components={"volatility": Decimal("0.15")},
        ),
    ]

    capital = Decimal("5000")
    weights = strategy.compute_target_weights(signals, capital)

    # Should return dict
    assert isinstance(weights, dict)

    # Weights should sum to approximately 1
    total = sum(weights.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.01")

    # All weights should be non-negative
    for w in weights.values():
        assert w >= 0

    # No weight should exceed max
    for w in weights.values():
        assert w <= Decimal("0.20")


def test_futuristic_strategy_weights():
    """Test futuristic strategy weight computation."""
    strategy = FuturisticStrategy()

    signals = [
        StrategySignal(ticker="NVDA", score=Decimal("0.4"), components={}),
        StrategySignal(ticker="ISRG", score=Decimal("0.3"), components={}),
    ]

    capital = Decimal("5000")
    weights = strategy.compute_target_weights(signals, capital)

    assert isinstance(weights, dict)
    total = sum(weights.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.01")


def test_realworld_strategy_weights():
    """Test real-world strategy weight computation."""
    strategy = RealWorldStrategy()

    signals = [
        StrategySignal(ticker="PG", score=Decimal("0.5"), components={}),
        StrategySignal(ticker="KO", score=Decimal("0.4"), components={}),
    ]

    capital = Decimal("5000")
    weights = strategy.compute_target_weights(signals, capital)

    assert isinstance(weights, dict)
    total = sum(weights.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.01")


def test_risk_strategy_weights():
    """Test risk strategy weight computation."""
    strategy = RiskStrategy()

    signals = [
        StrategySignal(
            ticker="SPY",
            score=Decimal("0.5"),
            components={"weight": Decimal("0.5"), "beta": Decimal("1.0")},
        ),
        StrategySignal(
            ticker="IEF",
            score=Decimal("0.3"),
            components={"weight": Decimal("0.3"), "beta": Decimal("0.2")},
        ),
        StrategySignal(
            ticker="TLT",
            score=Decimal("0.2"),
            components={"weight": Decimal("0.2"), "beta": Decimal("0.1")},
        ),
    ]

    capital = Decimal("5000")
    weights = strategy.compute_target_weights(signals, capital)

    assert isinstance(weights, dict)
    total = sum(weights.values())
    assert abs(total - Decimal("1.0")) < Decimal("0.01")
