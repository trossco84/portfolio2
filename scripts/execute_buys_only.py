#!/usr/bin/env python3
"""Execute only BUY orders from latest run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from portfolio.db.repo import repo
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest


def main():
    print("="*80)
    print("EXECUTING BUY ORDERS ONLY")
    print("="*80)
    print()

    # Get latest run
    run = repo.get_latest_run()
    print(f"Using run {run.id} from {run.asof_date}")

    # Get allocations
    allocations = repo.get_allocations(run.id)
    print(f"Found {len(allocations)} allocations")

    # Connect to Alpaca
    trading_client = TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper
    )

    data_client = StockHistoricalDataClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key
    )

    # Get account info
    account = trading_client.get_account()
    print(f"\nAccount:")
    print(f"  Cash: ${float(account.cash):,.2f}")
    print(f"  Buying Power: ${float(account.buying_power):,.2f}")

    # Get current positions
    current_positions = {}
    try:
        positions = trading_client.get_all_positions()
        for pos in positions:
            current_positions[pos.symbol] = float(pos.qty)
    except:
        pass

    print(f"\nCurrent positions: {len(current_positions)}")

    # Calculate BUY orders needed
    buy_orders = []

    for alloc in allocations:
        ticker = alloc.ticker
        target_dollars = float(alloc.target_dollars)
        current_shares = current_positions.get(ticker, 0)

        # Get current price
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            quotes = data_client.get_stock_latest_quote(request)

            if ticker in quotes:
                quote = quotes[ticker]
                price = (float(quote.bid_price) + float(quote.ask_price)) / 2

                target_shares = int(target_dollars / price)
                shares_to_buy = target_shares - current_shares

                if shares_to_buy > 0:
                    buy_orders.append({
                        'ticker': ticker,
                        'shares': shares_to_buy,
                        'price': price,
                        'sleeve': alloc.sleeve.value
                    })
        except Exception as e:
            print(f"  ⚠️  Could not get price for {ticker}: {e}")

    print(f"\n📊 Identified {len(buy_orders)} BUY orders")

    total_cost = sum(order['shares'] * order['price'] for order in buy_orders)
    print(f"Total estimated cost: ${total_cost:,.2f}")
    print()

    # Check against cash limits to avoid margin
    available_cash = float(account.cash)

    if total_cost > available_cash:
        print(f"⚠️  WARNING: Total cost (${total_cost:,.2f}) exceeds available cash (${available_cash:,.2f})")

        if available_cash <= 0:
            print("❌ ERROR: Already using margin! Cannot buy more positions.")
            print("   Run 'python scripts/reduce_to_cash.py' first to reduce positions.")
            return 1

        print("Will only execute orders up to available cash to avoid margin.")
        print()

        # Filter orders to stay within cash
        filtered_orders = []
        running_total = 0
        for order in buy_orders:
            order_cost = order['shares'] * order['price']
            if running_total + order_cost <= available_cash:
                filtered_orders.append(order)
                running_total += order_cost

        buy_orders = filtered_orders
        print(f"Reduced to {len(buy_orders)} orders totaling ${running_total:,.2f}")
        print()

    # Execute orders
    successful = 0
    failed = 0

    for order in buy_orders:
        ticker = order['ticker']
        shares = order['shares']
        sleeve = order['sleeve']

        try:
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )

            response = trading_client.submit_order(order_request)
            print(f"  ✓ BUY {ticker}: {shares} shares ({sleeve}) - Order {response.id}")
            successful += 1

        except Exception as e:
            print(f"  ✗ BUY {ticker}: {e}")
            failed += 1

    print()
    print("="*80)
    print(f"EXECUTION COMPLETE: {successful} successful, {failed} failed")
    print("="*80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
