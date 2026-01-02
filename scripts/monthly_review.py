#!/usr/bin/env python3
"""
Monthly deep-dive portfolio review with news and market context.

Runs on the first Monday of each month to provide comprehensive analysis.
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from portfolio.db.repo import repo
from portfolio.db.client import db_client
from portfolio.data.news import news_provider
from portfolio.ai.monthly_analysis import monthly_analyzer
from portfolio.notifications import email_notifier
from portfolio.utils.logging import logger


def main():
    """Run monthly portfolio deep-dive."""
    print("="*80)
    print("MONTHLY PORTFOLIO DEEP-DIVE")
    print("="*80)
    print(f"Date: {date.today()}")
    print(f"Mode: {'Paper' if settings.alpaca_paper else 'Live'}")
    print()

    # Get latest run
    today = date.today()
    run = repo.get_latest_run()

    if not run:
        print("❌ No portfolio run found")
        return 1

    run_id = run.id
    print(f"📊 Analyzing run {run_id} ({run.asof_date})")

    # Get portfolio data
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

            # All positions
            cur.execute("""
                SELECT ticker, shares, market_price, market_value, sleeve
                FROM positions
                WHERE run_id = %s
                ORDER BY market_value DESC
            """, (run_id,))
            positions = [dict(row) for row in cur.fetchall()]

    # Fetch news for all holdings
    print("\n📰 Fetching news for portfolio holdings...")
    tickers = [pos['ticker'] for pos in positions]
    news_data = news_provider.get_portfolio_news(tickers, days=30)

    # Fetch analyst sentiment
    print("💹 Fetching analyst sentiment...")
    sentiment_data = {}
    for ticker in tickers:
        sentiment = news_provider.get_market_sentiment(ticker)
        if sentiment:
            sentiment_data[ticker] = sentiment

    # Generate AI analysis
    print("\n🤖 Generating comprehensive monthly analysis...")

    portfolio_data = {
        'nav_total': float(nav_total),
        'nav_cash': float(nav_cash),
        'sleeve_breakdown': sleeve_data
    }

    monthly_analysis = monthly_analyzer.analyze_with_news(
        portfolio_data=portfolio_data,
        positions=positions,
        metrics=metrics,
        news_data=news_data,
        sentiment_data=sentiment_data,
        recommended_trades=None  # Could add rebalance trades here
    )

    # Build comprehensive email
    email_body = f"""
📊 MONTHLY PORTFOLIO DEEP-DIVE - {run_date}

{'='*80}
PORTFOLIO SUMMARY
{'='*80}

Total Value:  ${float(nav_total):,.2f}
Cash:         ${float(nav_cash):,.2f}
Invested:     ${float(nav_total - nav_cash):,.2f}

{'='*80}
RISK METRICS (30-DAY)
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
    email_body += "MONTHLY ANALYSIS WITH NEWS & MARKET CONTEXT\n"
    email_body += f"{'='*80}\n\n"
    email_body += monthly_analysis + "\n"

    # Add news highlights
    email_body += f"\n{'='*80}\n"
    email_body += "TOP NEWS HIGHLIGHTS (Past 30 Days)\n"
    email_body += f"{'='*80}\n\n"

    # Show top 10 news items
    all_news = []
    for ticker, articles in news_data.items():
        for article in articles[:2]:  # Top 2 per ticker
            all_news.append((ticker, article))

    all_news.sort(key=lambda x: x[1]['date'], reverse=True)

    for ticker, article in all_news[:10]:
        email_body += f"**{ticker}** - {article['title']}\n"
        email_body += f"  {article['publisher']} | {article['date']}\n\n"

    # Dashboard link
    dashboard_url = getattr(settings, 'dashboard_url', "http://localhost:8000")
    email_body += f"\n🔗 View Dashboard: {dashboard_url}\n"

    # Save to file
    email_file = Path(__file__).parent.parent / f"reports/{run_date}/monthly_deep_dive.txt"
    email_file.parent.mkdir(parents=True, exist_ok=True)
    email_file.write_text(email_body)

    print(f"✓ Monthly report saved to {email_file}")
    print("\n" + email_body)

    # Send email
    subject = f"📊 Monthly Portfolio Deep-Dive - {run_date}"
    email_sent = email_notifier.send_email(subject, email_body)

    if email_sent:
        print("✓ Email sent successfully")
    else:
        print("⚠️  Email not sent (no email service configured)")

    print("\n" + "="*80)
    print("MONTHLY REVIEW COMPLETE")
    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
