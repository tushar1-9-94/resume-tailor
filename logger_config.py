"""
Logger configuration module for consistent logging across the application.
Provides structured logging with different levels and formatting.
"""
import logging
import os
import sys
from datetime import datetime


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Set up and configure a logger with consistent formatting.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to environment variable LOG_LEVEL or INFO
    
    Returns:
        Configured logger instance
    """
    # Determine log level from environment or default to INFO
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level, logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create detailed formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance. Creates one if it doesn't exist.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Module-level logger for this module
logger = setup_logger(__name__)
logger.info("Logger configuration module loaded")