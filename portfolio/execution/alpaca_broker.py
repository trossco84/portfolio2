"""Alpaca broker integration."""

from decimal import Decimal

from portfolio.config import settings
from portfolio.db.models import OrderSide, OrderStatus, TradeOrder
from portfolio.utils.logging import logger

# Try to import alpaca
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderSide as AlpacaOrderSide
    from alpaca.trading.enums import TimeInForce
    from alpaca.trading.requests import LimitOrderRequest

    HAS_ALPACA = True
except ImportError:
    HAS_ALPACA = False
    logger.warning("alpaca-py not installed, Alpaca broker unavailable")


class AlpacaBroker:
    """Alpaca broker for live/paper trading."""

    def __init__(self):
        """Initialize Alpaca broker."""
        self.enabled = settings.has_alpaca_credentials and HAS_ALPACA

        if self.enabled:
            self.client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=settings.alpaca_paper,
            )
            logger.info(
                f"Alpaca broker initialized (paper={settings.alpaca_paper})"
            )
        else:
            self.client = None
            logger.info("Alpaca broker not configured")

    def submit_orders(self, orders: list[TradeOrder]) -> list[dict]:
        """
        Submit orders to Alpaca.

        Args:
            orders: List of trade orders

        Returns:
            List of execution results
        """
        if not self.enabled:
            logger.error("Alpaca broker not enabled")
            return []

        results = []

        for order in orders:
            try:
                result = self._submit_order(order)
                results.append(result)
            except Exception as e:
                logger.error(f"Error submitting order for {order.ticker}: {e}")
                results.append({
                    "ticker": order.ticker,
                    "side": order.side.value,
                    "qty": order.qty,
                    "status": OrderStatus.REJECTED.value,
                    "message": str(e),
                })

        return results

    def _submit_order(self, order: TradeOrder) -> dict:
        """Submit a single order to Alpaca."""
        # Convert side
        alpaca_side = (
            AlpacaOrderSide.BUY if order.side == OrderSide.BUY else AlpacaOrderSide.SELL
        )

        # Create limit order request
        order_request = LimitOrderRequest(
            symbol=order.ticker,
            qty=float(order.qty),
            side=alpaca_side,
            time_in_force=TimeInForce.DAY,
            limit_price=float(order.limit_price) if order.limit_price else None,
        )

        # Submit
        alpaca_order = self.client.submit_order(order_request)

        logger.info(
            f"Alpaca order submitted: {alpaca_order.symbol} {alpaca_order.side} "
            f"{alpaca_order.qty} @ {alpaca_order.limit_price}"
        )

        return {
            "ticker": order.ticker,
            "side": order.side.value,
            "qty": order.qty,
            "status": OrderStatus.SUBMITTED.value,
            "broker_order_id": alpaca_order.id,
            "filled_qty": Decimal("0"),
            "filled_avg_price": None,
            "message": f"Submitted to Alpaca: {alpaca_order.id}",
        }


# Global instance
alpaca_broker = AlpacaBroker()
