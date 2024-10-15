from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton
from PyQt5.QtCore import pyqtSignal


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
        self.config_saved.emit(self.config)
        self.hide()
