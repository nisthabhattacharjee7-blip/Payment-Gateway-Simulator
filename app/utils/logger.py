import logging 
import sys

logging.basicConfig(
     level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance for the given module name.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)