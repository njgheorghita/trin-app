import sys
import os
from web3 import Web3
import psutil
import subprocess
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QMessageBox, QCheckBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QStandardPaths
from trin_config import TrinConfig
import atexit
import signal
import logging
from logging.handlers import RotatingFileHandler
from log import get_app_data_dir, setup_logging
from window import ConfigWindow
from daemon import DaemonManager

class MenubarApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.tray = None
        self.config = TrinConfig()
        self.version = "0.1.0"
        self.config_window = None
        
        # Set up error handling
        sys.excepthook = self.handle_exception
        
        # Ensure cleanup on normal exit
        atexit.register(self.cleanup)
        
        # Handle SIGTERM
        signal.signal(signal.SIGTERM, self.sigterm_handler)

        # Set up logging
        self.app_logger, self.daemon_logger = setup_logging("TrinApp")
        self.daemon_manager = DaemonManager(self.app_logger, self.daemon_logger)

        self.init_ui()

    def init_ui(self):
        # Create the tray icon
        self.tray = QSystemTrayIcon(self.app)
        self.tray.setIcon(QIcon("../assets/off.png"))

        # Create the menu
        menu = QMenu()

        # Add actions to the menu
        about_action = menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        start_action = menu.addAction("Start Daemon")
        start_action.triggered.connect(self.start_daemon)
        stop_action = menu.addAction("Stop Daemon")
        stop_action.triggered.connect(self.stop_daemon)
        config_action = menu.addAction("Configure")
        config_action.triggered.connect(self.show_config)
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit)

        # Add the menu to the tray
        self.tray.setContextMenu(menu)
        self.tray.show()

        # Add a timer to periodically check daemon status
        self.status_timer = QTimer(self.app)
        self.status_timer.timeout.connect(self.check_daemon_status)
        self.status_timer.start(60000)  # Check every minute

    def show_about(self):
        daemon_status = self.daemon_manager.status()
        daemon_pid = self.daemon_manager.pid()
        about_text = "Trin Menubar App\n\n" \
                f"Version: {self.version}\n" \
                f"Storage (mb): {self.config.storage}\n" \
                f"History: {self.config.history}\n" \
                f"State: {self.config.state}\n" \
                f"Beacon: {self.config.beacon}\n" \
                f"HTTP Port: {self.config.http_port}\n" \
                f"Daemon status: {daemon_status}\n" \
                f"Daemon PID: {daemon_pid}\n" \
                f"Logs: {get_app_data_dir('TrinApp')}/logs\n"
        QMessageBox.about(None, "About Trin Menubar App", about_text)

    def show_config(self):
        if not self.config_window:
            self.config_window = ConfigWindow(self.config)
            self.config_window.config_saved.connect(self.update_config)
        self.config_window.storage_input.setValue(self.config.storage)
        self.config_window.history_checkbox.setChecked(self.config.history)
        self.config_window.state_checkbox.setChecked(self.config.state)
        self.config_window.beacon_checkbox.setChecked(self.config.beacon)
        self.config_window.http_port_input.setValue(self.config.http_port)
        self.config_window.show()
        self.config_window.activateWindow()  # Bring window to front
        self.config_window.raise_()  # Raise window to top

    def update_config(self, new_config):
        self.config = new_config

    def check_daemon_status(self):
        if not self.daemon_manager.is_daemon_running():
            self.tray.setIcon(QIcon("../assets/off.png"))
            self.start_daemon()
        w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{self.config.http_port}"))
        if not w3.is_connected():
            self.tray.setIcon(QIcon("../assets/off.png"))
            self.start_daemon()

    def start_daemon(self):
        try:
            self.daemon_manager.start_daemon(self.config)
            self.tray.setIcon(QIcon("../assets/on.png"))
            self.tray.showMessage("Daemon", "Daemon started successfully")
        except Exception as e:
            self.tray.setIcon(QIcon("../assets/off.png"))
            self.tray.showMessage("Error", f"Failed to start daemon: {str(e)}")
            logging.error(f"Error in start_daemon: {str(e)}")

    def stop_daemon(self):
        self.daemon_manager.stop_daemon()
        self.tray.setIcon(QIcon("../assets/off.png"))
        self.tray.showMessage("Daemon", "Daemon stopped")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        self.cleanup()
        self.tray.showMessage("Error", "An unexpected error occurred. The application will now exit.")
        sys.exit(1)

    def cleanup(self):
        logging.info("Performing cleanup")
        self.daemon_manager.stop_daemon()

    def sigterm_handler(self, signum, frame):
        logging.info("Received SIGTERM. Exiting.")
        self.cleanup()
        sys.exit(0)

    def quit(self):
        self.cleanup()
        self.tray.hide()
        self.app.quit()

    def run(self):
        try:
            sys.exit(self.app.exec_())
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            self.cleanup()
            raise

if __name__ == '__main__':
    try:
        app = MenubarApp()
        app.run()
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
        sys.exit(1)
