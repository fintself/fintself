# fintself/utils/logging.py
import sys

from loguru import logger

# Basic Loguru configuration
logger.remove()  # Removes the default configuration
logger.add(
    sys.stderr,
    level="INFO",  # Default log level for the console
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# You can add a file logger if needed
# logger.add("fintself.log", rotation="10 MB", level="DEBUG", compression="zip")

# Export the logger to be used in other parts of the code
__all__ = ["logger"]
