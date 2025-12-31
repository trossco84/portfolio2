"""Paper trading broker (simulation)."""

from decimal import Decimal

from portfolio.db.models import Order, OrderStatus, TradeOrder
from portfolio.utils.logging import logger


class PaperBroker:
    """Simulated paper trading broker."""

    def submit_orders(self, orders: list[TradeOrder]) -> list[dict]:
        """
        Submit orders to paper broker (simulation).

        Args:
            orders: List of trade orders

        Returns:
            List of execution results
        """
        results = []

        for order in orders:
            # Simulate immediate fill at limit price
            result = {
                "ticker": order.ticker,
                "side": order.side.value,
                "qty": order.qty,
                "status": OrderStatus.FILLED.value,
                "broker_order_id": f"PAPER-{order.ticker}-{order.side.value}",
                "filled_qty": order.qty,
                "filled_avg_price": order.limit_price,
                "message": "Paper trade simulated",
            }

            logger.info(
                f"Paper trade: {order.side.value.upper()} {order.qty} {order.ticker} "
                f"@ ${order.limit_price:.2f}"
            )

            results.append(result)

        return results


# Global instance
paper_broker = PaperBroker()
