"""Sentiment data fetchers (news and Reddit). Stubs if no API keys."""

from datetime import date
from decimal import Decimal

from portfolio.config import settings
from portfolio.utils.logging import logger


class NewsSentimentFetcher:
    """Fetch news sentiment scores. Stub implementation."""

    def __init__(self):
        """Initialize news sentiment fetcher."""
        self.has_api = settings.has_news_api

    def get_sentiment(self, ticker: str, start_date: date, end_date: date) -> Decimal:
        """
        Get aggregated sentiment score for ticker.

        Returns a score between -1 (very negative) and +1 (very positive).
        Returns 0 if no API key configured.
        """
        if not self.has_api:
            logger.debug(f"No news API configured, returning neutral sentiment for {ticker}")
            return Decimal("0.0")

        # TODO: Implement actual news API integration (NewsAPI, Alpha Vantage, etc.)
        # For now, return neutral
        logger.warning("News API integration not yet implemented, returning neutral")
        return Decimal("0.0")


class RedditSentimentFetcher:
    """Fetch Reddit sentiment scores. Stub implementation."""

    def __init__(self):
        """Initialize Reddit sentiment fetcher."""
        self.has_api = settings.has_reddit_api

    def get_sentiment(self, ticker: str, start_date: date, end_date: date) -> Decimal:
        """
        Get aggregated Reddit sentiment score for ticker.

        Returns a score between -1 (very negative) and +1 (very positive).
        Returns 0 if no API key configured.
        """
        if not self.has_api:
            logger.debug(f"No Reddit API configured, returning neutral sentiment for {ticker}")
            return Decimal("0.0")

        # TODO: Implement actual Reddit API integration (PRAW)
        # For now, return neutral
        logger.warning("Reddit API integration not yet implemented, returning neutral")
        return Decimal("0.0")


# Global instances
news_sentiment = NewsSentimentFetcher()
reddit_sentiment = RedditSentimentFetcher()
