"""Price data fetching via yfinance."""

from datetime import date, timedelta
from decimal import Decimal

import yfinance as yf

from portfolio.db.models import Price
from portfolio.db.repo import repo
from portfolio.utils.logging import logger


class PriceFetcher:
    """Fetch and cache historical price data."""

    def __init__(self):
        """Initialize price fetcher."""
        self.repo = repo

    def fetch_prices(
        self,
        tickers: list[str],
        start_date: date,
        end_date: date,
        use_cache: bool = True,
    ) -> dict[str, list[Price]]:
        """
        Fetch price data for tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date for price history
            end_date: End date for price history
            use_cache: Whether to use cached prices from DB

        Returns:
            Dictionary mapping ticker to list of Price objects
        """
        results = {}

        for ticker in tickers:
            try:
                # Try cache first
                if use_cache:
                    cached = self.repo.get_prices(ticker, start_date, end_date)
                    if cached and len(cached) > 0:
                        # Check if we have enough coverage
                        cached_dates = {p.date for p in cached}
                        date_range = (end_date - start_date).days
                        # If we have at least 80% of expected trading days, use cache
                        expected_days = date_range * 5 // 7  # Rough estimate
                        if len(cached_dates) >= expected_days * 0.8:
                            results[ticker] = cached
                            logger.info(f"Using cached prices for {ticker}: {len(cached)} records")
                            continue

                # Fetch from yfinance
                logger.info(f"Fetching {ticker} from {start_date} to {end_date}")
                prices = self._fetch_from_yfinance(ticker, start_date, end_date)

                if prices:
                    # Cache in database
                    self.repo.bulk_upsert_prices(prices)
                    results[ticker] = prices
                else:
                    logger.warning(f"No price data returned for {ticker}")

            except Exception as e:
                logger.error(f"Error fetching {ticker}: {e}")
                # Try to use whatever cache we have
                cached = self.repo.get_prices(ticker, start_date, end_date)
                if cached:
                    results[ticker] = cached
                    logger.info(f"Using partial cached data for {ticker}")

        return results

    def _fetch_from_yfinance(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[Price]:
        """Fetch from yfinance API."""
        # Add buffer to ensure we get data
        start = start_date - timedelta(days=5)
        end = end_date + timedelta(days=1)

        try:
            df = yf.download(
                ticker,
                start=start.isoformat(),
                end=end.isoformat(),
                progress=False,
                show_errors=False,
            )

            if df.empty:
                return []

            prices = []
            for idx, row in df.iterrows():
                try:
                    price = Price(
                        ticker=ticker,
                        date=idx.date(),
                        adj_close=Decimal(str(row["Adj Close"])),
                        close=Decimal(str(row["Close"])) if "Close" in row else None,
                        open=Decimal(str(row["Open"])) if "Open" in row else None,
                        high=Decimal(str(row["High"])) if "High" in row else None,
                        low=Decimal(str(row["Low"])) if "Low" in row else None,
                        volume=int(row["Volume"]) if "Volume" in row and row["Volume"] > 0 else None,
                        source="yfinance",
                    )
                    prices.append(price)
                except Exception as e:
                    logger.warning(f"Error parsing row for {ticker} on {idx}: {e}")
                    continue

            # Filter to requested date range
            prices = [p for p in prices if start_date <= p.date <= end_date]
            return prices

        except Exception as e:
            logger.error(f"yfinance error for {ticker}: {e}")
            return []

    def get_latest_price(self, ticker: str, asof_date: date) -> Decimal | None:
        """Get the most recent price for a ticker on or before asof_date."""
        price = self.repo.get_latest_price(ticker, asof_date)
        return price.adj_close if price else None


# Global instance
price_fetcher = PriceFetcher()
