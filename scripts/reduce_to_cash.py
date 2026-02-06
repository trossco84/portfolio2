#!/usr/bin/env python3
"""Reduce positions to eliminate margin usage and stay within cash limits."""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from portfolio.config import settings
from portfolio.db.repo import repo
from decimal import Decimal

def main():
    print("=" * 80)
    print("REDUCING POSITIONS TO CASH-ONLY")
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

    print(f"Current cash: ${cash:,.2f}")
    print(f"Current positions: ${positions_value:,.2f}")
    print()

    # Target: $10K total invested (4 sleeves × $2K each)
    target_invested = 10000.0
    need_to_sell = positions_value - target_invested

    if need_to_sell <= 0:
        print("✓ Already within cash limits!")
        return

    print(f"Need to sell: ${need_to_sell:,.2f}")
    print()

    # Get latest run allocations
    run = repo.get_latest_run()
    allocations = repo.get_allocations(run.id)

    # Build target map
    target_map = {}
    for alloc in allocations:
        target_map[alloc.ticker] = {
            'target_dollars': float(alloc.target_dollars),
            'sleeve': alloc.sleeve.value
        }

    # Get current positions
    positions = trading_client.get_all_positions()

    # Calculate overcapitalized positions
    reductions = []
    for pos in positions:
        ticker = pos.symbol
        current_value = float(pos.market_value)
        current_price = float(pos.current_price)
        current_qty = float(pos.qty)

        target_dollars = target_map.get(ticker, {}).get('target_dollars', 0)

        # How much is this position over target?
        over_target = current_value - target_dollars

        if over_target > 0:
            # Calculate shares to sell (round down to avoid selling too much)
            shares_to_sell = int(over_target / current_price)

            if shares_to_sell > 0:
                sell_value = shares_to_sell * current_price
                reductions.append({
                    'ticker': ticker,
                    'shares': shares_to_sell,
                    'price': current_price,
                    'value': sell_value,
                    'current_qty': int(current_qty),
                    'target_dollars': target_dollars,
                    'current_value': current_value,
                    'sleeve': target_map.get(ticker, {}).get('sleeve', 'unknown')
                })

    # Sort by how much over target (largest first)
    reductions.sort(key=lambda x: x['value'], reverse=True)

    # Select positions to sell to meet target
    total_to_sell = 0
    sell_orders = []

    for reduction in reductions:
        if total_to_sell >= need_to_sell:
            break

        sell_orders.append(reduction)
        total_to_sell += reduction['value']

    print(f"📊 Identified {len(sell_orders)} positions to reduce")
    print(f"Total reduction: ${total_to_sell:,.2f}")
    print()

    # Show planned sales
    for order in sell_orders:
        print(f"  SELL {order['ticker']}: {order['shares']} shares @ ${order['price']:.2f} = ${order['value']:.2f}")
        print(f"    Current: {order['current_qty']} shares (${order['current_value']:.2f}), Target: ${order['target_dollars']:.2f}")
        print(f"    Sleeve: {order['sleeve']}")
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
    account = trading_client.get_account()
    print()
    print(f"New cash: ${float(account.cash):,.2f}")
    print(f"New positions: ${float(account.long_market_value):,.2f}")
    print(f"Using margin: {float(account.cash) < 0}")


if __name__ == "__main__":
    main()
