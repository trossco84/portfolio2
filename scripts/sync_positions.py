#!/usr/bin/env python3
"""
Sync current Alpaca positions to database.

This updates the database with actual holdings from your Alpaca account.
"""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from portfolio.db.repo import repo
from portfolio.db.models import Position, Sleeve
from alpaca.trading.client import TradingClient
from datetime import date, datetime


def get_alpaca_positions(client: TradingClient) -> list[dict]:
    """Fetch all current positions from Alpaca."""
    positions = client.get_all_positions()

    result = []
    for pos in positions:
        result.append({
            'ticker': pos.symbol,
            'shares': float(pos.qty),
            'avg_cost': float(pos.avg_entry_price),
            'market_price': float(pos.current_price),
            'market_value': float(pos.market_value),
            'unrealized_pl': float(pos.unrealized_pl),
            'unrealized_pl_pct': float(pos.unrealized_plpc) * 100,
        })

    return result


def assign_sleeve(ticker: str, run_id: int) -> Sleeve:
    """Determine which sleeve a ticker belongs to based on latest allocations."""
    # Get allocations from latest run
    allocations = repo.get_allocations(run_id=run_id)

    for alloc in allocations:
        if alloc.ticker == ticker:
            return alloc.sleeve

    # Default to momentum if not found
    return Sleeve.MOMENTUM


def sync_positions_to_db(run_id: int, alpaca_positions: list[dict]):
    """Save Alpaca positions to database for a given run."""
    position_records = []

    for pos in alpaca_positions:
        sleeve = assign_sleeve(pos['ticker'], run_id)

        position_records.append(
            Position(
                run_id=run_id,
                sleeve=sleeve,
                ticker=pos['ticker'],
                shares=Decimal(str(pos['shares'])),
                avg_cost=Decimal(str(pos['avg_cost'])),
                market_price=Decimal(str(pos['market_price'])),
                market_value=Decimal(str(pos['market_value'])),
            )
        )

    if position_records:
        # Clear existing positions for this run
        import psycopg
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM positions WHERE run_id = %s", (run_id,))
                conn.commit()

        # Insert new positions
        repo.bulk_create_positions(position_records)

    return position_records


def main():
    """Main sync."""
    print("="*80)
    print("SYNCING ALPACA POSITIONS TO DATABASE")
    print("="*80)

    # Connect to Alpaca
    print(f"\nConnecting to Alpaca ({'paper' if settings.alpaca_paper else 'live'})...")
    client = TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper
    )

    # Get account info
    account = client.get_account()
    print(f"✓ Connected")
    print(f"  Account value: ${float(account.equity):,.2f}")
    print(f"  Cash: ${float(account.cash):,.2f}")
    print(f"  Buying power: ${float(account.buying_power):,.2f}")

    # Get positions
    print("\nFetching positions...")
    alpaca_positions = get_alpaca_positions(client)
    print(f"✓ Found {len(alpaca_positions)} positions")

    if alpaca_positions:
        total_value = sum(p['market_value'] for p in alpaca_positions)
        total_pl = sum(p['unrealized_pl'] for p in alpaca_positions)

        print(f"\nPositions summary:")
        print(f"  Total value: ${total_value:,.2f}")
        print(f"  Unrealized P/L: ${total_pl:,.2f} ({total_pl/total_value*100:+.2f}%)")
        print()

        for pos in sorted(alpaca_positions, key=lambda x: x['market_value'], reverse=True):
            print(f"  {pos['ticker']:<6} {pos['shares']:>8.0f} shares @ ${pos['market_price']:>8.2f} = ${pos['market_value']:>10.2f} (P/L: {pos['unrealized_pl_pct']:+.2f}%)")

    # Get latest run
    today = date.today()
    run = repo.get_run_by_date(today)

    if not run:
        print(f"\nNo run found for {today}")
        print("Creating a new run entry...")

        from portfolio.db.models import Run
        run_obj = Run(
            asof_date=today,
            nav_total=Decimal(str(account.equity)),
            nav_cash=Decimal(str(account.cash)),
            nav_momentum=Decimal('0'),
            nav_futuristic=Decimal('0'),
            nav_realworld=Decimal('0'),
            nav_risk=Decimal('0'),
            mode='live',
            notes=f"Synced {len(alpaca_positions)} positions from Alpaca"
        )
        run_id = repo.create_run(run_obj)
        print(f"✓ Created run {run_id}")
    else:
        run_id = run.id
        print(f"\n✓ Using run {run_id} for {today}")

    # Sync positions
    print(f"\nSyncing positions to database...")
    positions = sync_positions_to_db(run_id, alpaca_positions)
    print(f"✓ Synced {len(positions)} positions to run {run_id}")

    print("\n" + "="*80)
    print("SYNC COMPLETE")
    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
