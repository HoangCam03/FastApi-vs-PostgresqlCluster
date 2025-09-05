import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler



requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.INFO)

# Handler cho requests.log (7 ngày)
requests_handler = TimedRotatingFileHandler(
    "logs/requests.log",
    when="midnight",
    interval=1,
    backupCount=7
)
requests_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
requests_logger.addHandler(requests_handler)

# Cấu hình logger cho debug
debug_logger = logging.getLogger("debug")
debug_logger.setLevel(logging.DEBUG)

# Handler cho debug.log (7 ngày)
debug_handler = TimedRotatingFileHandler(
    "logs/debug.log",
    when="midnight",
    interval=1,
    backupCount=7
)
debug_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
debug_logger.addHandler(debug_handler)

def log_request(method: str, path: str, status_code: int, duration: float = None):
    """Log request vào requests.log"""
    message = f"{method} {path} - Status: {status_code}"
    if duration:
        message += f" - Duration: {duration:.3f}s"
    requests_logger.info(message)

def log_debug(message: str, level: str = "INFO"):
    """Log debug message vào debug.log"""
    if level.upper() == "DEBUG":
        debug_logger.debug(message)
    elif level.upper() == "INFO":
        debug_logger.info(message)
    elif level.upper() == "WARNING":
        debug_logger.warning(message)
    elif level.upper() == "ERROR":
        debug_logger.error(message)
