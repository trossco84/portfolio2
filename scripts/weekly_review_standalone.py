#!/usr/bin/env python3
"""
Database-free weekly portfolio review.

Connects directly to Alpaca for live positions and generates AI analysis.
"""

import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from alpaca.trading.client import TradingClient
from portfolio.ai.analysis import portfolio_analyzer
from portfolio.notifications import email_notifier


def main():
    """Run weekly review without database."""
    print("="*80)
    print("WEEKLY PORTFOLIO REVIEW (Standalone)")
    print("="*80)
    print(f"Date: {date.today()}")
    print(f"Mode: {'Paper' if settings.alpaca_paper else 'Live'}")
    print()

    try:
        # Connect to Alpaca
        trading_client = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=settings.alpaca_paper
        )

        # Get account and positions
        account = trading_client.get_account()
        positions = trading_client.get_all_positions()

        # Portfolio summary
        cash = float(account.cash)
        positions_value = float(account.long_market_value)
        total_equity = float(account.equity)
        buying_power = float(account.buying_power)

        print(f"Total Equity:     ${total_equity:,.2f}")
        print(f"Cash:             ${cash:,.2f}")
        print(f"Positions Value:  ${positions_value:,.2f}")
        print(f"Buying Power:     ${buying_power:,.2f}")
        print(f"Positions:        {len(positions)}")
        print()

        # Group positions by sleeve
        MOMENTUM = ['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'META', 'AMZN', 'AMD', 'NFLX']
        FUTURISTIC = ['PLTR', 'OKLO', 'SMR', 'AVGO', 'ARM', 'UEC', 'CCJ', 'UUUU', 'MU']
        REALWORLD = ['JNJ', 'PG', 'KO', 'PEP', 'WMT', 'UNP', 'DUK', 'SO', 'EXC', 'AEP']
        RISK = ['SPY', 'TLT', 'GLD', 'SHY']

        sleeve_data = {
            'momentum': {'count': 0, 'value': 0},
            'futuristic': {'count': 0, 'value': 0},
            'realworld': {'count': 0, 'value': 0},
            'risk': {'count': 0, 'value': 0}
        }

        positions_list = []

        for pos in positions:
            ticker = pos.symbol
            market_value = float(pos.market_value)

            pos_data = {
                'ticker': ticker,
                'shares': float(pos.qty),
                'market_price': float(pos.current_price),
                'market_value': market_value,
                'sleeve': 'other'
            }

            if ticker in MOMENTUM:
                sleeve_data['momentum']['count'] += 1
                sleeve_data['momentum']['value'] += market_value
                pos_data['sleeve'] = 'momentum'
            elif ticker in FUTURISTIC:
                sleeve_data['futuristic']['count'] += 1
                sleeve_data['futuristic']['value'] += market_value
                pos_data['sleeve'] = 'futuristic'
            elif ticker in REALWORLD:
                sleeve_data['realworld']['count'] += 1
                sleeve_data['realworld']['value'] += market_value
                pos_data['sleeve'] = 'realworld'
            elif ticker in RISK:
                sleeve_data['risk']['count'] += 1
                sleeve_data['risk']['value'] += market_value
                pos_data['sleeve'] = 'risk'

            positions_list.append(pos_data)

        # Calculate metrics
        equity = total_equity if total_equity > 0 else 1
        metrics = {
            'cash_ratio': cash / equity,
            'positions_ratio': positions_value / equity,
            'using_margin': cash < 0,
            'position_count': len(positions)
        }

        # Generate AI analysis
        print("🤖 Generating AI portfolio analysis...")

        portfolio_data = {
            'nav_total': total_equity,
            'nav_cash': cash,
            'positions_value': positions_value,
            'sleeve_breakdown': sleeve_data
        }

        ai_analysis = portfolio_analyzer.analyze_portfolio(
            portfolio_data=portfolio_data,
            positions=positions_list,
            metrics=metrics,
            recommended_trades=[]  # No trades for now
        )

        # Build email
        email_body = f"""
📊 WEEKLY PORTFOLIO REVIEW - {date.today()}

{'='*80}
PORTFOLIO SUMMARY
{'='*80}

Total Value:  ${total_equity:,.2f}
Cash:         ${cash:,.2f}
Invested:     ${positions_value:,.2f}

Margin Status: {'⚠️  USING MARGIN' if cash < 0 else '✓ Cash Positive'}

{'='*80}
HOLDINGS BY SLEEVE
{'='*80}

"""

        for sleeve, data in sorted(sleeve_data.items()):
            pct = (data['value'] / total_equity * 100) if total_equity > 0 else 0
            email_body += f"{sleeve.upper():<15} {data['count']:>3} positions  ${data['value']:>10,.2f}  ({pct:>5.1f}%)\n"

        email_body += f"\n{'='*80}\n"
        email_body += "AI ANALYSIS\n"
        email_body += f"{'='*80}\n\n"
        email_body += ai_analysis + "\n"
        email_body += f"\n{'='*80}\n"

        # Dashboard link
        dashboard_url = getattr(settings, 'dashboard_url', "https://portfolio-dashboard.fly.dev")
        email_body += f"\n🔗 View Dashboard: {dashboard_url}\n"

        # Save to file
        today_str = date.today().isoformat()
        email_file = Path(__file__).parent.parent / f"reports/weekly_review_{today_str}.txt"
        email_file.parent.mkdir(parents=True, exist_ok=True)
        email_file.write_text(email_body)

        print(f"✓ Email report saved to {email_file}")
        print("\n" + email_body)

        # Send email
        subject = f"📊 Weekly Portfolio Review - {date.today()}"
        email_sent = email_notifier.send_email(subject, email_body)

        if email_sent:
            print("✓ Email sent successfully")
        else:
            print("⚠️  Email not sent (no email service configured)")

        print("\n" + "="*80)
        print("WEEKLY REVIEW COMPLETE")
        print("="*80)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
