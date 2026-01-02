"""News and market data fetching for portfolio analysis."""

from typing import Optional
from datetime import datetime, timedelta
import yfinance as yf

from portfolio.utils.logging import logger


class NewsProvider:
    """Fetch news and market data for tickers."""

    def get_ticker_news(self, ticker: str, days: int = 30) -> list[dict]:
        """
        Get recent news for a ticker using yfinance.

        Args:
            ticker: Stock ticker symbol
            days: Number of days of news to fetch

        Returns:
            List of news articles with title, publisher, link, and date
        """
        try:
            stock = yf.Ticker(ticker)
            news = stock.news

            if not news:
                logger.warning(f"No news found for {ticker}")
                return []

            # Filter to recent news
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_news = []

            for article in news[:10]:  # Limit to 10 most recent
                article_date = datetime.fromtimestamp(article.get('providerPublishTime', 0))
                if article_date >= cutoff_date:
                    recent_news.append({
                        'title': article.get('title', ''),
                        'publisher': article.get('publisher', ''),
                        'link': article.get('link', ''),
                        'date': article_date.strftime('%Y-%m-%d'),
                        'summary': article.get('summary', '')[:200]  # First 200 chars
                    })

            logger.info(f"Found {len(recent_news)} recent articles for {ticker}")
            return recent_news

        except Exception as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            return []

    def get_portfolio_news(self, tickers: list[str], days: int = 30) -> dict[str, list[dict]]:
        """
        Get news for all tickers in portfolio.

        Args:
            tickers: List of ticker symbols
            days: Number of days of news to fetch

        Returns:
            Dictionary mapping ticker to list of news articles
        """
        portfolio_news = {}

        for ticker in tickers:
            news = self.get_ticker_news(ticker, days=days)
            if news:
                portfolio_news[ticker] = news

        total_articles = sum(len(articles) for articles in portfolio_news.values())
        logger.info(f"Fetched {total_articles} articles across {len(portfolio_news)} tickers")

        return portfolio_news

    def get_market_sentiment(self, ticker: str) -> dict:
        """
        Get basic market sentiment indicators for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with sentiment indicators
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Extract key sentiment indicators
            sentiment = {
                'analyst_recommendation': info.get('recommendationKey', 'N/A'),
                'target_mean_price': info.get('targetMeanPrice'),
                'current_price': info.get('currentPrice'),
                'num_analyst_opinions': info.get('numberOfAnalystOpinions'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
            }

            # Calculate price vs target
            if sentiment['target_mean_price'] and sentiment['current_price']:
                upside = (sentiment['target_mean_price'] - sentiment['current_price']) / sentiment['current_price'] * 100
                sentiment['analyst_upside_pct'] = round(upside, 2)

            return sentiment

        except Exception as e:
            logger.error(f"Failed to fetch sentiment for {ticker}: {e}")
            return {}


# Global news provider instance
news_provider = NewsProvider()
