#!/usr/bin/env python3
"""Proportionally reduce all positions to eliminate margin usage."""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from portfolio.config import settings

def main():
    print("=" * 80)
    print("PROPORTIONAL POSITION REDUCTION TO ELIMINATE MARGIN")
    print("=" * 80)
    print()

    # Connect to Alpaca
    trading_client = TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper
    )

    # Get account status
    account = trading_client.get_account()
    cash = float(account.cash)
    positions_value = float(account.long_market_value)
    equity = float(account.equity)

    print(f"Current cash: ${cash:,.2f}")
    print(f"Current positions: ${positions_value:,.2f}")
    print(f"Total equity: ${equity:,.2f}")
    print()

    if cash >= 0:
        print("✓ Already cash positive! No reduction needed.")
        return

    # Calculate reduction ratio
    # Config: $10K total, $2K cash reserve = $8K invested (4 sleeves × $2K)
    target_invested = 8000.0
    reduction_ratio = target_invested / positions_value

    print(f"Target invested: ${target_invested:,.2f}")
    print(f"Reduction ratio: {reduction_ratio:.4f} ({(1-reduction_ratio)*100:.1f}% reduction)")
    print()

    # Get positions and calculate sales
    positions = trading_client.get_all_positions()
    sell_orders = []

    for pos in positions:
        current_qty = float(pos.qty)
        current_price = float(pos.current_price)
        current_value = float(pos.market_value)

        # New target for this position
        new_target_value = current_value * reduction_ratio
        new_target_qty = int(new_target_value / current_price)

        # Shares to sell
        shares_to_sell = int(current_qty) - new_target_qty

        if shares_to_sell > 0:
            sell_value = shares_to_sell * current_price
            sell_orders.append({
                'ticker': pos.symbol,
                'shares': shares_to_sell,
                'price': current_price,
                'value': sell_value,
                'current_qty': int(current_qty),
                'new_qty': new_target_qty
            })

    # Sort by value (largest first)
    sell_orders.sort(key=lambda x: x['value'], reverse=True)

    total_proceeds = sum(o['value'] for o in sell_orders)

    print(f"📊 Will sell from {len(sell_orders)} positions")
    print(f"Total proceeds: ${total_proceeds:,.2f}")
    print(f"Estimated new cash: ${cash + total_proceeds:,.2f}")
    print()

    # Show all sales
    for order in sell_orders:
        print(f"  SELL {order['ticker']}: {order['shares']} shares @ ${order['price']:.2f} = ${order['value']:.2f}")
        print(f"    {order['current_qty']} → {order['new_qty']} shares")

    print()

    # Confirm
    response = input("Execute these sales? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return

    # Execute sales
    print()
    print("Executing sales...")
    successful = 0
    failed = 0

    for order in sell_orders:
        ticker = order['ticker']
        shares = order['shares']

        try:
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )

            response = trading_client.submit_order(order_request)
            print(f"  ✓ SELL {ticker}: {shares} shares - Order {response.id}")
            successful += 1

        except Exception as e:
            print(f"  ✗ SELL {ticker}: {shares} shares - FAILED: {e}")
            failed += 1

    print()
    print("=" * 80)
    print(f"COMPLETE: {successful} successful, {failed} failed")
    print("=" * 80)

    # Show new status
    import time
    time.sleep(2)  # Wait for orders to settle

    account = trading_client.get_account()
    print()
    print(f"New cash: ${float(account.cash):,.2f}")
    print(f"New positions: ${float(account.long_market_value):,.2f}")
    print(f"Using margin: {float(account.cash) < 0}")


if __name__ == "__main__":
    main()
