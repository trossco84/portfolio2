#!/usr/bin/env python3
"""
Weekly portfolio review and rebalancing.

This script:
1. Syncs current positions from Alpaca
2. Runs portfolio analysis
3. Generates recommended trades (conservative - only when needed)
4. Sends email with summary
5. Optionally auto-executes trades
"""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from portfolio.db.repo import repo
from portfolio.db.models import Sleeve
from alpaca.trading.client import TradingClient
from datetime import date, datetime
import subprocess


def sync_positions():
    """Sync current positions from Alpaca."""
    print("📊 Syncing positions from Alpaca...")
    result = subprocess.run(
        [sys.executable, Path(__file__).parent / "sync_positions.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ Sync failed: {result.stderr}")
        return False

    print("✓ Positions synced")
    return True


def run_portfolio_analysis(asof_date: date, mode: str = "live") -> int | None:
    """Run portfolio analysis to get new recommendations."""
    print(f"\n📈 Running portfolio analysis for {asof_date}...")

    # Check if run already exists
    existing_run = repo.get_run_by_date(asof_date)
    if existing_run:
        print(f"✓ Using existing run {existing_run.id}")
        return existing_run.id

    # Run portfolio
    result = subprocess.run(
        [
            sys.executable, "-m", "portfolio", "run",
            "--asof", asof_date.isoformat(),
            "--mode", mode
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    if result.returncode != 0:
        print(f"❌ Portfolio run failed: {result.stderr}")
        return None

    # Get the run ID
    run = repo.get_run_by_date(asof_date)
    if run:
        print(f"✓ Portfolio analysis complete (run {run.id})")
        return run.id

    return None


def calculate_rebalance_trades(run_id: int, threshold: float = 0.15) -> list[dict]:
    """
    Calculate trades needed to rebalance portfolio.

    Conservative approach:
    - Only rebalance if position drift > threshold (15% default)
    - Favor holds over trades for long-term strategy
    - Group small trades to minimize transaction costs
    """
    print(f"\n🔄 Calculating rebalance trades (threshold: {threshold*100:.0f}%)...")

    # Get current positions and target allocations
    from portfolio.db.client import db_client

    positions = {}  # ticker -> shares
    targets = {}    # ticker -> target_dollars

    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            # Current positions
            cur.execute("""
                SELECT ticker, shares, market_price
                FROM positions
                WHERE run_id = %s
            """, (run_id,))

            rows = cur.fetchall()
            if rows:
                for row in rows:
                    positions[row['ticker']] = {
                        'shares': float(row['shares']),
                        'current_value': float(row['shares'] * row['market_price']),
                        'price': float(row['market_price'])
                    }

            # Target allocations
            cur.execute("""
                SELECT ticker, target_dollars
                FROM allocations
                WHERE run_id = %s
            """, (run_id,))

            rows = cur.fetchall()
            if rows:
                for row in rows:
                    targets[row['ticker']] = float(row['target_dollars'])

    # Calculate trades
    trades = []

    # Check existing positions for sells/reduces
    for ticker, pos in positions.items():
        target = targets.get(ticker, 0)
        current = pos['current_value']
        drift = abs(current - target) / max(target, current) if target > 0 else 1.0

        if drift > threshold:
            if target == 0:
                # Full exit
                trades.append({
                    'ticker': ticker,
                    'action': 'SELL',
                    'shares': int(pos['shares']),
                    'reason': 'No longer in portfolio',
                    'current_value': current,
                    'target_value': 0
                })
            elif current > target * (1 + threshold):
                # Reduce position
                target_shares = int(target / pos['price'])
                reduce_shares = int(pos['shares']) - target_shares
                if reduce_shares > 0:
                    trades.append({
                        'ticker': ticker,
                        'action': 'SELL',
                        'shares': reduce_shares,
                        'reason': f'Reduce (drift: {drift*100:.1f}%)',
                        'current_value': current,
                        'target_value': target
                    })

    # Check targets for buys/increases
    for ticker, target in targets.items():
        if ticker not in positions:
            # New position
            if target > 50:  # Only buy if position size > $50
                trades.append({
                    'ticker': ticker,
                    'action': 'BUY',
                    'shares': 'CALCULATE',  # Will calculate from current price
                    'reason': 'New position',
                    'current_value': 0,
                    'target_value': target
                })
        else:
            pos = positions[ticker]
            current = pos['current_value']
            drift = abs(current - target) / target if target > 0 else 0

            if drift > threshold and current < target * (1 - threshold):
                # Increase position
                current_shares = int(pos['shares'])
                target_shares = int(target / pos['price'])
                add_shares = target_shares - current_shares
                if add_shares > 0:
                    trades.append({
                        'ticker': ticker,
                        'action': 'BUY',
                        'shares': add_shares,
                        'reason': f'Increase (drift: {drift*100:.1f}%)',
                        'current_value': current,
                        'target_value': target
                    })

    print(f"✓ Identified {len(trades)} rebalance trades")
    return trades


def send_email_report(run_id: int, trades: list[dict]):
    """Send email with weekly summary."""
    print("\n📧 Generating email report...")

    # Get run data
    from portfolio.db.client import db_client

    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            # Run summary
            cur.execute("""
                SELECT asof_date, nav_total, nav_cash
                FROM runs
                WHERE id = %s
            """, (run_id,))
            run_row = cur.fetchone()
            run_date = run_row['asof_date']
            nav_total = run_row['nav_total']
            nav_cash = run_row['nav_cash']

            # Risk metrics
            cur.execute("""
                SELECT metric_name, metric_value
                FROM risk_metrics
                WHERE run_id = %s
            """, (run_id,))
            metrics = {row['metric_name']: float(row['metric_value']) for row in cur.fetchall()}

            # Positions by sleeve
            cur.execute("""
                SELECT sleeve, COUNT(*) as count, SUM(market_value) as total
                FROM positions
                WHERE run_id = %s
                GROUP BY sleeve
            """, (run_id,))
            sleeve_data = {row['sleeve']: {'count': row['count'], 'value': float(row['total'])} for row in cur.fetchall()}

    # Build email
    email_body = f"""
📊 WEEKLY PORTFOLIO REVIEW - {run_date}

{'='*80}
PORTFOLIO SUMMARY
{'='*80}

Total Value:  ${float(nav_total):,.2f}
Cash:         ${float(nav_cash):,.2f}
Invested:     ${float(nav_total - nav_cash):,.2f}

{'='*80}
RISK METRICS
{'='*80}

Beta (vs SPY):        {metrics.get('beta_spy', 0):.2f}
Volatility (annual):  {metrics.get('volatility_annual', 0):.2%}
Sharpe Ratio:         {metrics.get('sharpe_ratio', 0):.2f}
Max Drawdown:         {metrics.get('max_drawdown', 0):.2%}

{'='*80}
HOLDINGS BY SLEEVE
{'='*80}

"""

    for sleeve, data in sorted(sleeve_data.items()):
        email_body += f"{sleeve.upper():<15} {data['count']:>3} positions  ${data['value']:>10,.2f}\n"

    email_body += f"\n{'='*80}\n"

    if trades:
        email_body += f"RECOMMENDED TRADES ({len(trades)})\n"
        email_body += f"{'='*80}\n\n"

        for trade in trades:
            action = trade['action']
            ticker = trade['ticker']
            shares = trade['shares']
            reason = trade['reason']
            email_body += f"{action:<6} {ticker:<6} {shares:>6} shares - {reason}\n"

        email_body += f"\n💡 Rebalancing threshold: Positions drifted >15% from target\n"
    else:
        email_body += "NO TRADES RECOMMENDED\n"
        email_body += f"{'='*80}\n\n"
        email_body += "✓ Portfolio is well-balanced. No rebalancing needed.\n"

    # Dashboard link
    dashboard_url = getattr(settings, 'dashboard_url', "http://localhost:8000")
    email_body += f"\n🔗 View Dashboard: {dashboard_url}\n"

    # Save to file
    email_file = Path(__file__).parent.parent / f"reports/{run_date}/weekly_email.txt"
    email_file.parent.mkdir(parents=True, exist_ok=True)
    email_file.write_text(email_body)

    print(f"✓ Email report saved to {email_file}")
    print("\n" + email_body)

    # Send email
    from portfolio.notifications import email_notifier

    subject = f"📊 Weekly Portfolio Review - {run_date}"
    if trades:
        subject += f" ({len(trades)} trades recommended)"

    email_sent = email_notifier.send_email(subject, email_body)

    if email_sent:
        print("✓ Email sent successfully")
    else:
        print("⚠️  Email not sent (no email service configured)")

    return email_body


def execute_rebalance_trades(run_id: int, trades: list[dict]) -> bool:
    """Execute rebalance trades via Alpaca."""
    if not trades:
        return True

    print(f"\n🤖 Auto-executing {len(trades)} rebalance trades...")

    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    client = TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=settings.alpaca_paper
    )

    successful = 0
    failed = 0

    for trade in trades:
        ticker = trade['ticker']
        action = trade['action']
        shares = trade['shares']

        if shares == 'CALCULATE':
            # Get current price and calculate shares
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
                price = (float(quote.bid_price) + float(quote.ask_price)) / 2
                shares = int(trade['target_value'] / price)
            else:
                print(f"  ✗ {ticker}: Could not get price")
                failed += 1
                continue

        if shares <= 0:
            continue

        try:
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=shares,
                side=OrderSide.BUY if action == 'BUY' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )

            response = client.submit_order(order_request)
            print(f"  ✓ {action} {ticker}: {shares} shares (order {response.id})")
            successful += 1

        except Exception as e:
            print(f"  ✗ {action} {ticker}: {e}")
            failed += 1

    print(f"\n✓ Executed {successful}/{len(trades)} trades successfully")
    if failed > 0:
        print(f"⚠️  {failed} trades failed")

    return failed == 0


def main():
    """Main weekly review."""
    import argparse

    parser = argparse.ArgumentParser(description='Weekly portfolio review')
    parser.add_argument('--auto-execute', action='store_true',
                       help='Automatically execute recommended trades')
    args = parser.parse_args()

    print("="*80)
    print("WEEKLY PORTFOLIO REVIEW")
    print("="*80)
    print(f"Date: {date.today()}")
    print(f"Mode: {'Paper' if settings.alpaca_paper else 'Live'}")
    if args.auto_execute:
        print("🤖 Auto-execution: ENABLED")
    print()

    # Step 1: Sync positions
    if not sync_positions():
        return 1

    # Step 2: Run analysis
    today = date.today()
    run_id = run_portfolio_analysis(today, mode='live' if not settings.alpaca_paper else 'paper')

    if not run_id:
        print("❌ Portfolio analysis failed")
        return 1

    # Step 3: Calculate rebalance trades (conservative threshold)
    trades = calculate_rebalance_trades(run_id, threshold=0.15)

    # Step 4: Send email report
    send_email_report(run_id, trades)

    # Step 5: Auto-execute if enabled
    if trades and args.auto_execute:
        execute_success = execute_rebalance_trades(run_id, trades)
        if not execute_success:
            print("⚠️  Some trades failed to execute")
            return 1
    elif trades:
        print(f"\n⏸️  {len(trades)} trades recommended")
        print("   To execute: python scripts/execute_live_trades.py")
        print("   Or run with --auto-execute flag")
    else:
        print("\n✓ No rebalancing needed - portfolio is balanced")

    print("\n" + "="*80)
    print("WEEKLY REVIEW COMPLETE")
    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
