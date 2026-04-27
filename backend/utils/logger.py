"""
Logging utility for MeetingAI application.

Provides a standardized way to create configured logger instances.
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with standard configuration.
    
    If the logger has no handlers, configures it with a StreamHandler
    outputting to stdout with a standard format.
    
    Args:
        name: The name of the logger (typically __name__).
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger