import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
def setup_logger(name: str = None, level: str = "INFO") -> logging.Logger:
    """
    Set up and configure logger
    Args:
        name: Logger name (default: root logger)
        level: Logging level (default: INFO)
    Returns:
        Configured logger instance
    """
    # Map string levels to logging constants
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level = level_map.get(level.upper(), logging.INFO)
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    # Create file handler
    logs_dir = Path("./logs")
    logs_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir / f"{name or 'app'}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger