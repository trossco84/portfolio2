#!/usr/bin/env python3
"""
Execute live trades with Alpaca based on portfolio recommendations.

DANGER: This script places REAL ORDERS with REAL MONEY.
Only run this if you understand what it does.
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.db.repo import repo
from portfolio.config import settings
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import date


def get_account_buying_power(client: TradingClient) -> float:
    """Get available buying power from Alpaca account."""
    account = client.get_account()
    return float(account.buying_power)


def get_current_price(client: TradingClient, ticker: str) -> float | None:
    """Get current market price for a ticker."""
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest

        data_client = StockHistoricalDataClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key
        )

        request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        quotes = data_client.get_stock_latest_quote(request)

        if ticker in quotes:
            quote = quotes[ticker]
            # Use midpoint of bid/ask
            return (float(quote.bid_price) + float(quote.ask_price)) / 2
        return None
    except Exception as e:
        print(f"Error getting price for {ticker}: {e}")
        return None


def calculate_affordable_orders(
    allocations: list,
    max_budget: float,
    client: TradingClient
) -> list[dict]:
    """
    Calculate which orders we can afford with current budget.

    Strategy:
    1. Get current live prices
    2. For expensive stocks, reduce shares to what we can afford
    3. Prioritize diversity - try to get at least 1 share of each affordable stock
    4. Allocate remaining budget proportionally
    """
    # Get current prices and filter to affordable stocks
    stock_data = []
    for alloc in allocations:
        price = get_current_price(client, alloc.ticker)
        if price and price > 0:
            min_cost = price  # Cost for 1 share
            if min_cost <= max_budget * 0.5:  # Only consider if 1 share is < 50% of budget
                stock_data.append({
                    'ticker': alloc.ticker,
                    'sleeve': alloc.sleeve,
                    'target_dollars': float(alloc.target_dollars),
                    'current_price': price,
                    'min_shares': 1,
                })

    if not stock_data:
        print("No affordable stocks found!")
        return []

    # Sort by sleeve to ensure diversity
    stock_data.sort(key=lambda x: (x['sleeve'], -x['target_dollars']))

    # Phase 1: Buy 1 share of each affordable stock (diversity first)
    orders = []
    remaining_budget = max_budget

    for stock in stock_data:
        cost_for_one = stock['current_price']
        if cost_for_one <= remaining_budget - 50:  # Leave $50 buffer
            orders.append({
                'ticker': stock['ticker'],
                'sleeve': stock['sleeve'],
                'shares': 1,
                'price': stock['current_price'],
                'notional': cost_for_one
            })
            remaining_budget -= cost_for_one

    # Phase 2: Add more shares to positions proportionally if budget allows
    if remaining_budget > 100:
        # Sort by target allocation (buy more of highest conviction)
        orders.sort(key=lambda x: -x['notional'])

        for order in orders:
            if remaining_budget < 50:
                break

            # Try to add more shares up to target
            current_notional = order['shares'] * order['price']

            # Find original target
            target = next(s for s in stock_data if s['ticker'] == order['ticker'])
            target_notional = target['target_dollars']

            if current_notional < target_notional:
                # Calculate how many more shares we can afford
                remaining_target = target_notional - current_notional
                max_additional_shares = int(min(
                    remaining_target / order['price'],
                    (remaining_budget - 50) / order['price']
                ))

                if max_additional_shares > 0:
                    additional_cost = max_additional_shares * order['price']
                    order['shares'] += max_additional_shares
                    order['notional'] += additional_cost
                    remaining_budget -= additional_cost

    return orders


def execute_orders(orders: list[dict], client: TradingClient, dry_run: bool = True):
    """Execute orders via Alpaca."""
    print(f"\n{'='*80}")
    print(f"{'DRY RUN - ' if dry_run else ''}EXECUTING {len(orders)} ORDERS")
    print(f"{'='*80}\n")

    total_notional = 0
    successful = 0
    failed = 0

    for i, order in enumerate(orders, 1):
        ticker = order['ticker']
        shares = order['shares']
        notional = order['notional']

        print(f"[{i}/{len(orders)}] {ticker}: {shares} shares @ ${order['price']:.2f} = ${notional:.2f}")

        if not dry_run:
            try:
                order_request = MarketOrderRequest(
                    symbol=ticker,
                    qty=shares,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )

                response = client.submit_order(order_request)
                print(f"  ✓ Order submitted: {response.id}")
                successful += 1
                total_notional += notional

            except Exception as e:
                print(f"  ✗ Order failed: {e}")
                failed += 1
        else:
            total_notional += notional
            successful += 1

    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total invested: ${total_notional:.2f}")
    print(f"{'='*80}\n")


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("LIVE TRADING EXECUTION SCRIPT")
    print("="*80)

    # Safety check
    if settings.alpaca_paper:
        print("\n⚠️  ALPACA_PAPER=true - This will use paper trading")
    else:
        print("\n🔴 ALPACA_PAPER=false - This will use LIVE TRADING with REAL MONEY")
        print("\nThis script will:")
        print("  1. Connect to your Alpaca account")
        print("  2. Check your buying power")
        print("  3. Get current market prices")
        print("  4. Place MARKET ORDERS for multiple stocks")
        print("\nMarket orders execute immediately at current market prices.")
        print("There is NO UNDO for executed orders.\n")

    # Get latest run allocations
    run = repo.get_run_by_date(date(2025, 12, 31))
    if not run:
        print("❌ No run found for 2025-12-31")
        return 1

    allocations = repo.get_allocations(run_id=run.id)
    print(f"\n📊 Found {len(allocations)} recommended positions from run {run.id}")

    # Initialize Alpaca client
    print(f"\n🔌 Connecting to Alpaca ({'paper' if settings.alpaca_paper else 'LIVE'})...")
    client = TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper
    )

    # Get account info
    try:
        buying_power = get_account_buying_power(client)
        print(f"✓ Account connected")
        print(f"  Buying power: ${buying_power:,.2f}")
    except Exception as e:
        print(f"❌ Failed to connect to Alpaca: {e}")
        return 1

    # Ask for budget limit
    print(f"\n💰 You mentioned having ~$2,995 available")
    max_budget_input = input(f"Enter max budget to invest (press Enter for $2,950): ").strip()
    max_budget = float(max_budget_input) if max_budget_input else 2950.0

    if max_budget > buying_power:
        print(f"⚠️  Warning: Max budget ${max_budget:.2f} exceeds buying power ${buying_power:.2f}")
        max_budget = min(max_budget, buying_power)
        print(f"   Adjusting to ${max_budget:.2f}")

    # Calculate affordable orders
    print(f"\n📈 Fetching current prices and calculating orders (this may take a minute)...")
    orders = calculate_affordable_orders(allocations, max_budget, client)

    if not orders:
        print("❌ No orders generated!")
        return 1

    # Show orders
    print(f"\n✓ Generated {len(orders)} orders:")
    by_sleeve = {}
    for order in orders:
        sleeve = order['sleeve']
        if sleeve not in by_sleeve:
            by_sleeve[sleeve] = []
        by_sleeve[sleeve].append(order)

    for sleeve, sleeve_orders in sorted(by_sleeve.items()):
        total = sum(o['notional'] for o in sleeve_orders)
        print(f"\n  {sleeve.upper()}: {len(sleeve_orders)} stocks, ${total:.2f}")
        for order in sleeve_orders:
            print(f"    {order['ticker']}: {order['shares']} shares @ ${order['price']:.2f} = ${order['notional']:.2f}")

    total_cost = sum(o['notional'] for o in orders)
    print(f"\n  TOTAL: {len(orders)} stocks, ${total_cost:.2f}")
    print(f"  Remaining: ${max_budget - total_cost:.2f}")

    # Confirm execution
    print(f"\n{'='*80}")
    print("⚠️  FINAL CONFIRMATION")
    print(f"{'='*80}")
    print(f"Mode: {'PAPER TRADING' if settings.alpaca_paper else '🔴 LIVE TRADING 🔴'}")
    print(f"Orders: {len(orders)} market orders")
    print(f"Total: ${total_cost:.2f}")
    print(f"\nType 'EXECUTE' to submit orders, or anything else to cancel: ", end='')

    confirmation = input().strip()

    if confirmation == 'EXECUTE':
        print("\n🚀 Executing orders...")
        execute_orders(orders, client, dry_run=False)
        print("\n✓ Done! Check your Alpaca dashboard for order status.")
        return 0
    else:
        print("\n❌ Cancelled. No orders were placed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
