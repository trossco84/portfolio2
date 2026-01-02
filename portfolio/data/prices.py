"""Price data fetching via yfinance."""

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
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
        Fetch price data for tickers (batch optimized).

        Args:
            tickers: List of ticker symbols
            start_date: Start date for price history
            end_date: End date for price history
            use_cache: Whether to use cached prices from DB

        Returns:
            Dictionary mapping ticker to list of Price objects
        """
        results = {}
        tickers_to_fetch = []

        # Check cache first
        if use_cache:
            for ticker in tickers:
                try:
                    cached = self.repo.get_prices(ticker, start_date, end_date)
                    if cached and len(cached) > 0:
                        cached_dates = {p.date for p in cached}
                        date_range = (end_date - start_date).days
                        expected_days = date_range * 5 // 7
                        if len(cached_dates) >= expected_days * 0.8:
                            results[ticker] = cached
                            continue
                    tickers_to_fetch.append(ticker)
                except Exception as e:
                    logger.error(f"Error checking cache for {ticker}: {e}")
                    tickers_to_fetch.append(ticker)
        else:
            tickers_to_fetch = tickers

        # Batch fetch from yfinance
        if tickers_to_fetch:
            logger.info(f"Batch fetching {len(tickers_to_fetch)} tickers...")
            batch_results = self._fetch_batch_from_yfinance(tickers_to_fetch, start_date, end_date)

            for ticker, prices in batch_results.items():
                if prices:
                    self.repo.bulk_upsert_prices(prices)
                    results[ticker] = prices

        logger.info(f"Loaded prices for {len(results)} tickers ({len(tickers) - len(tickers_to_fetch)} from cache)")
        return results

    def _fetch_batch_from_yfinance(
        self, tickers: list[str], start_date: date, end_date: date
    ) -> dict[str, list[Price]]:
        """Batch fetch from yfinance API (much faster)."""
        start = start_date - timedelta(days=5)
        end = end_date + timedelta(days=1)

        results = {}

        try:
            # Download all tickers at once
            df = yf.download(
                tickers,
                start=start.isoformat(),
                end=end.isoformat(),
                progress=False,
                group_by='ticker',
                threads=True,
            )

            if df.empty:
                return results

            # Handle single ticker case (no multi-index)
            if len(tickers) == 1:
                ticker = tickers[0]
                prices = self._parse_dataframe(df, ticker, start_date, end_date)
                if prices:
                    results[ticker] = prices
            else:
                # Multiple tickers - iterate through each
                for ticker in tickers:
                    try:
                        ticker_df = df[ticker]
                        prices = self._parse_dataframe(ticker_df, ticker, start_date, end_date)
                        if prices:
                            results[ticker] = prices
                    except Exception as e:
                        logger.warning(f"Error parsing {ticker}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Batch download error: {e}")

        return results

    def _parse_dataframe(
        self, df: pd.DataFrame, ticker: str, start_date: date, end_date: date
    ) -> list[Price]:
        """Parse a dataframe into Price objects."""
        if df.empty:
            return []

        prices = []
        for idx, row in df.iterrows():
            try:
                adj_close = row.get("Adj Close", row.get("Close"))
                if pd.isna(adj_close):
                    continue

                price = Price(
                    ticker=ticker,
                    date=idx.date(),
                    adj_close=Decimal(str(adj_close)),
                    close=Decimal(str(row.get("Close"))) if not pd.isna(row.get("Close")) else None,
                    open=Decimal(str(row.get("Open"))) if not pd.isna(row.get("Open")) else None,
                    high=Decimal(str(row.get("High"))) if not pd.isna(row.get("High")) else None,
                    low=Decimal(str(row.get("Low"))) if not pd.isna(row.get("Low")) else None,
                    volume=int(row.get("Volume")) if not pd.isna(row.get("Volume")) and row.get("Volume") > 0 else None,
                    source="yfinance",
                )
                prices.append(price)
            except Exception as e:
                logger.warning(f"Error parsing row for {ticker} on {idx}: {e}")
                continue

        # Filter to requested date range
        prices = [p for p in prices if start_date <= p.date <= end_date]
        return prices

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
            )

            if df.empty:
                return []

            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            prices = []
            for idx, row in df.iterrows():
                try:
                    # Get values, handling potential NaN
                    adj_close = row.get("Adj Close", row.get("Close"))
                    if pd.isna(adj_close):
                        continue

                    close_val = row.get("Close")
                    open_val = row.get("Open")
                    high_val = row.get("High")
                    low_val = row.get("Low")
                    volume_val = row.get("Volume")

                    price = Price(
                        ticker=ticker,
                        date=idx.date(),
                        adj_close=Decimal(str(adj_close)),
                        close=Decimal(str(close_val)) if not pd.isna(close_val) else None,
                        open=Decimal(str(open_val)) if not pd.isna(open_val) else None,
                        high=Decimal(str(high_val)) if not pd.isna(high_val) else None,
                        low=Decimal(str(low_val)) if not pd.isna(low_val) else None,
                        volume=int(volume_val) if not pd.isna(volume_val) and volume_val > 0 else None,
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
