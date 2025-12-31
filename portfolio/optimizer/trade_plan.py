"""Generate trade plans from current positions to target allocations."""

from datetime import date
from decimal import Decimal

from portfolio.config import settings
from portfolio.data.prices import price_fetcher
from portfolio.db.models import Allocation, OrderSide, Position, Sleeve, TradeOrder
from portfolio.utils.logging import logger


class TradePlanGenerator:
    """Generate executable trade orders from target allocations."""

    def __init__(self):
        """Initialize trade plan generator."""
        self.min_trade_size = settings.min_trade_size
        self.max_position_pct = settings.max_position_pct

    def generate_trade_plan(
        self,
        current_positions: list[Position],
        target_allocations: list[Allocation],
        asof_date: date,
    ) -> list[TradeOrder]:
        """
        Generate trade orders to move from current to target allocations.

        Args:
            current_positions: Current holdings
            target_allocations: Target allocations
            asof_date: Date for price quotes

        Returns:
            List of TradeOrder objects
        """
        # Build current holdings dict (by sleeve and ticker)
        current_holdings = {}
        for pos in current_positions:
            if pos.sleeve == Sleeve.CASH:
                continue
            key = (pos.sleeve, pos.ticker)
            current_holdings[key] = {
                "shares": pos.shares,
                "value": pos.market_value,
            }

        # Build target allocations dict
        target_dict = {}
        for alloc in target_allocations:
            key = (alloc.sleeve, alloc.ticker)
            target_dict[key] = {
                "weight": alloc.target_weight,
                "dollars": alloc.target_dollars,
            }

        # Get all tickers we need prices for
        all_tickers = set()
        for sleeve, ticker in current_holdings.keys():
            all_tickers.add(ticker)
        for sleeve, ticker in target_dict.keys():
            all_tickers.add(ticker)

        # Fetch current prices
        prices = {}
        for ticker in all_tickers:
            price = price_fetcher.get_latest_price(ticker, asof_date)
            if price:
                prices[ticker] = price
            else:
                logger.warning(f"No price available for {ticker}")

        # Generate orders
        orders = []

        # All possible (sleeve, ticker) combinations
        all_keys = set(current_holdings.keys()) | set(target_dict.keys())

        for sleeve, ticker in all_keys:
            if ticker not in prices:
                logger.warning(f"Skipping {ticker} - no price data")
                continue

            current_value = current_holdings.get((sleeve, ticker), {}).get("value", Decimal("0"))
            current_shares = current_holdings.get((sleeve, ticker), {}).get("shares", Decimal("0"))
            target_value = target_dict.get((sleeve, ticker), {}).get("dollars", Decimal("0"))

            current_price = prices[ticker]

            # Compute target shares
            if target_value > 0 and current_price > 0:
                target_shares = target_value / current_price
            else:
                target_shares = Decimal("0")

            # Delta
            delta_shares = target_shares - current_shares
            delta_value = delta_shares * current_price

            # Apply min trade size filter
            if abs(delta_value) < self.min_trade_size:
                continue

            # Create order
            if delta_shares > 0:
                # Buy
                order = TradeOrder(
                    sleeve=sleeve,
                    ticker=ticker,
                    side=OrderSide.BUY,
                    qty=abs(delta_shares),
                    notional=abs(delta_value),
                    limit_price=current_price,
                    reason=f"Increase position from {current_shares:.2f} to {target_shares:.2f} shares",
                )
                orders.append(order)
            else:
                # Sell
                # Can only sell what we own
                sellable_shares = min(abs(delta_shares), current_shares)
                if sellable_shares > 0:
                    order = TradeOrder(
                        sleeve=sleeve,
                        ticker=ticker,
                        side=OrderSide.SELL,
                        qty=sellable_shares,
                        notional=sellable_shares * current_price,
                        limit_price=current_price,
                        reason=f"Decrease position from {current_shares:.2f} to {target_shares:.2f} shares",
                    )
                    orders.append(order)

        logger.info(f"Generated {len(orders)} trade orders")

        # Sort by notional size (largest first)
        orders.sort(key=lambda o: o.notional, reverse=True)

        return orders

    def validate_trade_plan(
        self, orders: list[TradeOrder], sleeve_capital: dict[Sleeve, Decimal]
    ) -> tuple[bool, list[str]]:
        """
        Validate that trade plan respects constraints.

        Args:
            orders: List of trade orders
            sleeve_capital: Capital per sleeve

        Returns:
            (is_valid, list of warnings)
        """
        warnings = []

        # Group by sleeve
        sleeve_orders = {}
        for order in orders:
            if order.sleeve not in sleeve_orders:
                sleeve_orders[order.sleeve] = []
            sleeve_orders[order.sleeve].append(order)

        # Check each sleeve
        for sleeve, sleeve_orders_list in sleeve_orders.items():
            capital = sleeve_capital.get(sleeve, Decimal("0"))

            # Total buy value
            buy_value = sum(
                o.notional for o in sleeve_orders_list if o.side == OrderSide.BUY
            )

            # Check if buys exceed capital (allowing for some wiggle room from sells)
            if buy_value > capital * Decimal("1.1"):
                warnings.append(
                    f"{sleeve.value}: Buy orders (${buy_value:.2f}) exceed capital (${capital:.2f})"
                )

            # Check max position size
            for order in sleeve_orders_list:
                if order.side == OrderSide.BUY:
                    position_pct = order.notional / capital
                    if position_pct > self.max_position_pct:
                        warnings.append(
                            f"{sleeve.value}/{order.ticker}: Position size "
                            f"{position_pct:.1%} exceeds max {self.max_position_pct:.1%}"
                        )

        is_valid = len(warnings) == 0
        return is_valid, warnings


# Global instance
trade_planner = TradePlanGenerator()
