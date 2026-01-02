#!/usr/bin/env python3
"""Test Alpaca API connection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import settings
from alpaca.trading.client import TradingClient


def main():
    print("Testing Alpaca API connection...")
    print(f"API Key: {settings.alpaca_api_key[:10]}... (length: {len(settings.alpaca_api_key) if settings.alpaca_api_key else 0})")
    print(f"Secret Key: {settings.alpaca_secret_key[:10] if settings.alpaca_secret_key else 'None'}... (length: {len(settings.alpaca_secret_key) if settings.alpaca_secret_key else 0})")
    print(f"Paper trading: {settings.alpaca_paper}")

    if not settings.has_alpaca_credentials:
        print("\n❌ No Alpaca credentials found!")
        return 1

    try:
        client = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=settings.alpaca_paper
        )

        print("\nFetching account info...")
        account = client.get_account()

        print(f"\n✅ SUCCESS!")
        print(f"Account Status: {account.status}")
        print(f"Account Value: ${float(account.equity):,.2f}")
        print(f"Cash: ${float(account.cash):,.2f}")
        print(f"Buying Power: ${float(account.buying_power):,.2f}")

        return 0

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
