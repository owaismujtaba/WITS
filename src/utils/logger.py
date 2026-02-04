import os
import sys
import logging

def setup_logger(name='wits_automation', log_dir='logs', log_file=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Clear handlers to avoid duplicates (safe re-init)
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Ensure logs directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Log file path
    if log_file is None:
        log_file = f"{name}.log"

    log_path = os.path.join(log_dir, log_file)

    # File handler
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
