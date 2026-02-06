"""Configuration management using pydantic-settings."""

from decimal import Decimal
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database (optional - not needed for standalone scripts)
    database_url: Optional[str] = Field(default=None, description="Supabase Postgres connection string")

    # Portfolio configuration
    total_capital: Decimal = Field(default=Decimal("25000"), description="Total portfolio capital")
    cash_reserve: Decimal = Field(default=Decimal("5000"), description="Cash reserve (not traded)")
    sleeve_capital: Decimal = Field(default=Decimal("5000"), description="Capital per sleeve")

    # Trade constraints
    min_trade_size: Decimal = Field(default=Decimal("50"), description="Minimum trade size in dollars")
    max_position_pct: Decimal = Field(
        default=Decimal("0.20"), description="Max position size as % of sleeve"
    )

    # Alpaca (optional)
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    alpaca_paper: bool = True

    # News/Sentiment (optional)
    news_api_key: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None

    # Dashboard
    dashboard_username: Optional[str] = None
    dashboard_password: Optional[str] = None
    dashboard_url: Optional[str] = None

    # Email notifications
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    sendgrid_api_key: Optional[str] = None

    # AI/LLM
    anthropic_api_key: Optional[str] = None

    # Environment
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    @field_validator("total_capital", "cash_reserve", "sleeve_capital", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        """Parse string or number to Decimal."""
        if isinstance(v, str):
            return Decimal(v)
        return Decimal(str(v))

    @property
    def tradeable_capital(self) -> Decimal:
        """Capital available for trading (excludes cash reserve)."""
        return self.total_capital - self.cash_reserve

    @property
    def has_alpaca_credentials(self) -> bool:
        """Check if Alpaca API credentials are configured."""
        return bool(self.alpaca_api_key and self.alpaca_secret_key)

    @property
    def has_news_api(self) -> bool:
        """Check if news API is configured."""
        return bool(self.news_api_key)

    @property
    def has_reddit_api(self) -> bool:
        """Check if Reddit API is configured."""
        return bool(self.reddit_client_id and self.reddit_client_secret)


# Global settings instance
settings = Settings()
