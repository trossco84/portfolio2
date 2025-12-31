#!/usr/bin/env python3
"""
Verify project setup and configuration.

Run this script to check that everything is configured correctly
before running the portfolio for the first time.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_imports():
    """Check that all required packages can be imported."""
    print("Checking Python packages...")
    required = [
        ("fastapi", "FastAPI"),
        ("pydantic", "Pydantic"),
        ("psycopg", "Psycopg3"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("scipy", "SciPy"),
        ("yfinance", "yfinance"),
    ]

    optional = [
        ("cvxpy", "CVXPY (optimizer)"),
        ("alpaca", "Alpaca"),
    ]

    all_good = True

    for module, name in required:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} - MISSING (required)")
            all_good = False

    for module, name in optional:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ⚠ {name} - Not installed (optional)")

    return all_good


def check_config():
    """Check configuration."""
    print("\nChecking configuration...")

    try:
        from portfolio.config import settings

        # Check DATABASE_URL
        if not settings.database_url or "postgresql://" not in settings.database_url:
            print("  ✗ DATABASE_URL not configured properly")
            print("    Edit .env and set your Supabase connection string")
            return False
        else:
            # Mask password in output
            masked_url = settings.database_url.split("@")[0].split(":")[0] + ":***@" + settings.database_url.split("@")[1]
            print(f"  ✓ DATABASE_URL configured")

        # Check capitals
        print(f"  ✓ Total capital: ${settings.total_capital}")
        print(f"  ✓ Cash reserve: ${settings.cash_reserve}")
        print(f"  ✓ Sleeve capital: ${settings.sleeve_capital}")

        return True

    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        return False


def check_database():
    """Check database connectivity."""
    print("\nChecking database connection...")

    try:
        from portfolio.db.client import db_client

        # Try to connect
        with db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        print("  ✓ Database connection successful")

        # Check if migrations ran
        try:
            from portfolio.db.repo import repo
            runs = repo.list_runs(limit=1)
            print(f"  ✓ Database tables exist ({len(runs)} run(s) found)")
        except Exception as e:
            print(f"  ⚠ Database tables may not exist (run migrations)")
            print(f"    Run: python portfolio/db/migrations/migrate.py")

        return True

    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        print("    Check your DATABASE_URL in .env")
        return False


def check_directories():
    """Check that necessary directories exist."""
    print("\nChecking directories...")

    project_root = Path(__file__).parent.parent
    required_dirs = [
        "portfolio",
        "app",
        "tests",
        "scripts",
    ]

    optional_dirs = [
        "reports",
        "logs",
    ]

    all_good = True

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ - MISSING")
            all_good = False

    for dir_name in optional_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ℹ {dir_name}/ - Will be created on first run")

    return all_good


def check_data_fetch():
    """Test data fetching."""
    print("\nTesting price data fetching...")

    try:
        from portfolio.data.prices import price_fetcher
        from datetime import date, timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        print(f"  Fetching SPY prices for last 7 days...")
        prices = price_fetcher.fetch_prices(["SPY"], start_date, end_date, use_cache=False)

        if "SPY" in prices and len(prices["SPY"]) > 0:
            print(f"  ✓ Price fetching works ({len(prices['SPY'])} records)")
            return True
        else:
            print(f"  ⚠ No price data returned (may be a network issue)")
            return True  # Don't fail, might be temporary

    except Exception as e:
        print(f"  ✗ Price fetching failed: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("  Portfolio Setup Verification")
    print("=" * 60)
    print()

    checks = [
        ("Python packages", check_imports),
        ("Configuration", check_config),
        ("Database", check_database),
        ("Directories", check_directories),
        ("Data fetching", check_data_fetch),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nError in {name} check: {e}")
            results.append((name, False))
        print()

    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print()

    all_passed = all(result for _, result in results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print()

    if all_passed:
        print("✓ All checks passed! Your setup is ready.")
        print()
        print("Next steps:")
        print("  1. Run portfolio: python -m portfolio run --asof $(date +%Y-%m-%d) --mode paper")
        print("  2. View dashboard: uvicorn app.main:app --reload")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
