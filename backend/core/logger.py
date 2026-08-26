import logging
import sys
from pythonjsonlogger import jsonlogger

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # If the logger already has handlers, assume it's already configured.
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)

    logHandler = logging.StreamHandler(sys.stdout)
    # Using python-json-logger for structured GCP-ready logging
    # Include timestamp, level, name, and message in the JSON output
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)

    # Disable propagation to avoid duplicate logs if root logger is also configured
    logger.propagate = False

    return logger
