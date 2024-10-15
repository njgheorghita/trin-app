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



class ConfigWindow(QWidget):
    config_saved = pyqtSignal(object)  # Signal to emit when config is saved

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Configuration')
        self.setGeometry(300, 300, 250, 150)

        layout = QVBoxLayout()

        self.storage_input = QSpinBox(self)
        self.storage_input.setRange(1, 1000000)  # Set a reasonable range
        self.storage_input.setValue(self.config.storage)
        layout.addWidget(QLabel('Storage (mb):'))
        layout.addWidget(self.storage_input)

        self.history_checkbox = QCheckBox('History (always enabled)', self)
        self.history_checkbox.setChecked(self.config.history)
        self.history_checkbox.setEnabled(False) # disable checkbox
        layout.addWidget(self.history_checkbox)

        self.state_checkbox = QCheckBox('State', self)
        self.state_checkbox.setChecked(self.config.state)
        layout.addWidget(self.state_checkbox)

        self.beacon_checkbox = QCheckBox('Beacon', self)
        self.beacon_checkbox.setChecked(self.config.beacon)
        layout.addWidget(self.beacon_checkbox)

        self.http_port_input = QSpinBox(self)
        self.http_port_input.setRange(1, 65_535)  # Max port number
        self.http_port_input.setValue(self.config.http_port)
        layout.addWidget(QLabel('HTTP Port:'))
        layout.addWidget(self.http_port_input)

        save_button = QPushButton('Save', self)
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_config(self):
        self.config.storage = self.storage_input.value()
        self.config.http_port = self.http_port_input.value()
        self.config.history = self.history_checkbox.isChecked()
        self.config.state = self.state_checkbox.isChecked()
        self.config.beacon = self.beacon_checkbox.isChecked()
        print(f"Configuration saved: {vars(self.config)}")
        self.config_saved.emit(self.config)
        self.hide()

# Set up logging
# logging.basicConfig(filename='menubar_app.log', level=logging.ERROR,
                    # format='%(asctime)s - %(levelname)s - %(message)s')

class DaemonManager:
    def __init__(self, logger):
        self.daemon_process = None
        self.logger = logger

    def start_daemon(self, config):
        if self.daemon_process and self.daemon_process.poll() is None:
            self.logger.info("Daemon is already running")
            return

        try:
            trin_config = config.get_trin_config()
            cmd = ["../trin/target/debug/trin"] + trin_config
            self.daemon_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.logger.info(f"Daemon started with PID: {self.daemon_process.pid}")
        except Exception as e:
            self.logger.error(f"Failed to start daemon: {str(e)}")
            raise

    def stop_daemon(self):
        if self.daemon_process:
            try:
                process = psutil.Process(self.daemon_process.pid)
                process.terminate()
                process.wait(timeout=10)
                if process.is_running():
                    process.kill()
                self.logger.info("Daemon stopped")
            except psutil.NoSuchProcess:
                self.logger.info("Daemon was not running")
            except Exception as e:
                self.logger.error(f"Failed to stop daemon: {str(e)}")
            finally:
                self.daemon_process = None

    def is_daemon_running(self):
        print("Checking daemon status")
        if self.daemon_process is not None:
            # if daemon process is a zombie, restart it
            try:
                process = psutil.Process(self.daemon_process.pid)
                if process.status() == psutil.STATUS_ZOMBIE:
                    return False
            except psutil.NoSuchProcess:
                self.start_daemon()
                return False
        return True
    
    def status(self):
        if self.daemon_process:
            return "Running"
        else:
            return "Stopped"

    def pid(self):
        if self.daemon_process:
            return self.daemon_process.pid
        else:
            return "N/A"

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
        self.logger = setup_logging("TrinApp")
        self.daemon_manager = DaemonManager(self.logger)

        self.init_ui()

    def init_ui(self):
        # Create the tray icon
        self.tray = QSystemTrayIcon(self.app)
        self.tray.setIcon(QIcon("./assets/off.png"))

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
        print("Checking daemon status")
        if not self.daemon_manager.is_daemon_running():
            self.start_daemon()
        w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{self.config.http_port}"))
        if not w3.is_connected():
            print("XXX: Daemon is not connected")
            self.start_daemon()

    def start_daemon(self):
        print("Starting daemon")
        try:
            self.daemon_manager.start_daemon(self.config)
            print("Daemon started")
            self.tray.setIcon(QIcon("./assets/on.png"))
            self.tray.showMessage("Daemon", "Daemon started successfully")
        except Exception as e:
            print(f"Error in start_daemon: {str(e)}")
            self.tray.setIcon(QIcon("./assets/off.png"))
            self.tray.showMessage("Error", f"Failed to start daemon: {str(e)}")
            logging.error(f"Error in start_daemon: {str(e)}")

    def stop_daemon(self):
        self.daemon_manager.stop_daemon()
        self.tray.setIcon(QIcon("./assets/off.png"))
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
