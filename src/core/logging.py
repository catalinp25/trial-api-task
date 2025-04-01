import logging, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path



LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log levels
CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG

# Logs directory
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

def get_logger(name):
    """
    Get a logger with the given name
    
    Args:
        name: Name of the logger, usually __name__
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure logger if it hasn't been already
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console_handler)
        
        # File handler for all logs
        file_handler = RotatingFileHandler(
            logs_dir / "app.log", 
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(file_handler)
        
        # Error file handler
        error_file_handler = RotatingFileHandler(
            logs_dir / "error.log", 
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(error_file_handler)
    
    return logger