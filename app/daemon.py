import subprocess
import psutil
from PyQt5.QtCore import QProcess, QStandardPaths

class DaemonManager:
    def __init__(self, app_logger, daemon_logger):
        self.daemon_process = None
        self.app_logger = app_logger
        self.daemon_logger = daemon_logger
        self.start_timeout = 10000  # 10 seconds timeout for starting

    def start_daemon(self, config):
        if self.is_daemon_running():
            self.app_logger.info("Daemon is already running")
            return

        try:
            self.daemon_process = QProcess()
            self.daemon_process.readyReadStandardOutput.connect(self.handle_stdout)
            self.daemon_process.readyReadStandardError.connect(self.handle_stderr)
            command = "../../trin/target/debug/trin"
            args = config.get_trin_config()
            self.daemon_process.start(command, args)
            
            # Wait for the process to start
            if self.daemon_process.waitForStarted(self.start_timeout):
                self.daemon_pid = self.daemon_process.processId()
                self.app_logger.info(f"Daemon started with PID: {self.daemon_pid}")
            else:
                raise Exception("Failed to start daemon process")
        except Exception as e:
            self.app_logger.error(f"Failed to start daemon: {str(e)}")
            raise

    def handle_stdout(self):
        data = self.daemon_process.readAllStandardOutput()
        stdout = bytes(data).decode('utf8')
        for line in stdout.strip().split('\n'):
            self.daemon_logger.info(line)

    def handle_stderr(self):
        data = self.daemon_process.readAllStandardError()
        stderr = bytes(data).decode('utf8')
        for line in stderr.strip().split('\n'):
            self.daemon_logger.error(line)

    def stop_daemon(self):
        if self.daemon_process:
            self.daemon_process.terminate()
            if not self.daemon_process.waitForFinished(5000):  # 5 seconds timeout
                self.daemon_process.kill()
            self.app_logger.info("Daemon stopped")
            self.daemon_process = None

    def is_daemon_running(self):
        if self.daemon_process is None:
            return False
        if self.daemon_process.state() != QProcess.Running:
            return False
        
        daemon_pid = self.daemon_process.processId()
        try:
            process = psutil.Process(daemon_pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
    
    def status(self):
        if self.daemon_process:
            return "Running"
        else:
            return "Stopped"

    def pid(self):
        if self.daemon_process:
            return self.daemon_process.processId()
        else:
            return "N/A"

