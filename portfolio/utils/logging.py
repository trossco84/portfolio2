"""Logging configuration."""

import logging
import sys

from portfolio.config import settings


def setup_logging() -> logging.Logger:
    """Configure application logging."""
    logger = logging.getLogger("portfolio")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper()))

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


logger = setup_logging()
