#!/usr/bin/env python3
"""
Weekly portfolio run script.

This script can be run via cron or scheduled tasks.
Example cron entry (Mondays at 9 AM):
0 9 * * 1 cd /path/to/portfolio2 && python scripts/run_weekly.py
"""

import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.cli import PortfolioRunner
from portfolio.utils.logging import logger


def main():
    """Run weekly portfolio optimization."""
    logger.info("Starting weekly portfolio run")

    runner = PortfolioRunner()
    today = date.today()

    try:
        run_id = runner.run(asof_date=today, mode="paper")
        logger.info(f"Weekly run completed successfully: Run ID {run_id}")
        print(f"SUCCESS: Portfolio run {run_id} completed for {today}")
        return 0

    except Exception as e:
        logger.error(f"Weekly run failed: {e}", exc_info=True)
        print(f"ERROR: Portfolio run failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
