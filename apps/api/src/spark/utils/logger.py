"""
Centralized logging configuration for Spark API.

Usage:
    from spark.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys

# Configure standard root logger slightly so everything follows the format
# but provide a helper for consistency.

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_formatter = logging.Formatter(_LOG_FORMAT)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)


def get_logger(name: str) -> logging.Logger:
    """Get a consistently formatted stdout logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_handler)
        logger.setLevel(logging.INFO)
    return logger
