#!/usr/bin/env python3
"""Generate descriptions for all tickers in the portfolio."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.ai.analysis import portfolio_analyzer
from portfolio.db.repo import repo
from portfolio.utils.logging import logger
from datetime import date


def main():
    """Generate descriptions for all unique tickers."""
    print("="*80)
    print("GENERATING TICKER DESCRIPTIONS")
    print("="*80)
    print()

    if not portfolio_analyzer.client:
        print("❌ No Anthropic API key configured")
        print("   Set ANTHROPIC_API_KEY in your .env file")
        return 1

    # Get latest run to find all current tickers
    today = date.today()
    run = repo.get_run_by_date(today)

    if not run:
        print(f"❌ No run found for {today}")
        return 1

    # Get all positions
    positions = repo.get_positions(run.id)
    tickers = sorted(set(pos.ticker for pos in positions))

    print(f"Found {len(tickers)} unique tickers: {', '.join(tickers)}")
    print()

    descriptions = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Generating description for {ticker}...", end=" ", flush=True)
        description = portfolio_analyzer.get_ticker_description(ticker)
        descriptions[ticker] = description
        print(f"✓")
        print(f"    {description}")
        print()

    # Save to a Python file that can be imported
    output_file = Path(__file__).parent.parent / "portfolio" / "data" / "ticker_descriptions.py"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write('"""Auto-generated ticker descriptions."""\n\n')
        f.write('TICKER_DESCRIPTIONS = {\n')
        for ticker in sorted(descriptions.keys()):
            desc = descriptions[ticker].replace('"', '\\"')
            f.write(f'    "{ticker}": "{desc}",\n')
        f.write('}\n')

    print("="*80)
    print(f"✓ Descriptions saved to {output_file}")
    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
