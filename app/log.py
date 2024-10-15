import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtCore import QStandardPaths


def get_app_data_dir(app_name):
    if sys.platform == 'darwin':
        return os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), app_name)
    elif sys.platform == 'win32':
        return os.path.join(os.environ.get('APPDATA', ''), app_name)
    else:  # linux and other unix-like
        return os.path.join(os.path.expanduser('~'), f'.{app_name.lower()}')

def setup_logging(app_name):
    log_dir = os.path.join(get_app_data_dir(app_name), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Setup for main app logger
    app_log_file = os.path.join(log_dir, f'{app_name}.log')
    app_handler = RotatingFileHandler(app_log_file, maxBytes=5*1024*1024, backupCount=5)
    app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app_handler.setFormatter(app_formatter)

    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(app_handler)

    # Setup for daemon logger
    daemon_log_file = os.path.join(log_dir, f'{app_name}_daemon.log')
    daemon_handler = RotatingFileHandler(daemon_log_file, maxBytes=5*1024*1024, backupCount=5)
    daemon_formatter = logging.Formatter('%(asctime)s - DAEMON - %(levelname)s - %(message)s')
    daemon_handler.setFormatter(daemon_formatter)

    daemon_logger = logging.getLogger(f"{app_name}_daemon")
    daemon_logger.setLevel(logging.INFO)
    daemon_logger.addHandler(daemon_handler)

    return app_logger, daemon_logger
