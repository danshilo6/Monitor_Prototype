"""Devices settings tab"""


from PySide6.QtWidgets import (QVBoxLayout, QWidget, QLineEdit, QFormLayout, QPushButton, QMessageBox)
from PySide6.QtCore import Qt


class DevicesSettings(QWidget):
    """Devices settings tab widget"""

    def __init__(self, config_service):
        super().__init__()
        self._config = config_service
        self._setup_ui()
        self._load_from_config()
    
    def _setup_ui(self):
        """Setup the devices settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Create form layout for better alignment
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Relay Fail Count Threshold input
        self._relay_fail_threshold_input = QLineEdit()
        self._relay_fail_threshold_input.setObjectName("settings-input")
        self._relay_fail_threshold_input.setPlaceholderText("Enter threshold count...")
        self._relay_fail_threshold_input.returnPressed.connect(self._focus_next_field)
        form_layout.addRow("Relay Fail Count Threshold:", self._relay_fail_threshold_input)

        # Camera Fail Count Threshold input
        self._camera_fail_threshold_input = QLineEdit()
        self._camera_fail_threshold_input.setObjectName("settings-input")
        self._camera_fail_threshold_input.setPlaceholderText("Enter threshold count...")
        self._camera_fail_threshold_input.returnPressed.connect(self._focus_next_field)
        form_layout.addRow("Camera Fail Count Threshold:", self._camera_fail_threshold_input)

        # Minutes since last camera log input
        self._camera_log_minutes_input = QLineEdit()
        self._camera_log_minutes_input.setObjectName("settings-input")
        self._camera_log_minutes_input.setPlaceholderText("Enter minutes...")
        # No returnPressed for last field (nowhere to go)
        form_layout.addRow("Minutes Since Last Camera Log:", self._camera_log_minutes_input)

        # Save button
        self._save_button = QPushButton("Save Settings")
        self._save_button.setObjectName("blue-button")
        self._save_button.clicked.connect(self._confirm_save)
        form_layout.addRow("", self._save_button)

        layout.addLayout(form_layout)

        # Add stretch to push content to top
        layout.addStretch()

    def _load_from_config(self):
        # Block signals to prevent saving during load
        self._relay_fail_threshold_input.blockSignals(True)
        self._camera_fail_threshold_input.blockSignals(True)
        self._camera_log_minutes_input.blockSignals(True)
        
        # Load values
        self._relay_fail_threshold_input.setText(self._config.get("devices", "relay_fail_threshold", ""))
        self._camera_fail_threshold_input.setText(self._config.get("devices", "camera_fail_threshold", ""))
        self._camera_log_minutes_input.setText(self._config.get("devices", "camera_log_minutes", ""))
        
        # Re-enable signals
        self._relay_fail_threshold_input.blockSignals(False)
        self._camera_fail_threshold_input.blockSignals(False)
        self._camera_log_minutes_input.blockSignals(False)

    def _save_to_config(self):
        self._config.set("devices", "relay_fail_threshold", self._relay_fail_threshold_input.text())
        self._config.set("devices", "camera_fail_threshold", self._camera_fail_threshold_input.text())
        self._config.set("devices", "camera_log_minutes", self._camera_log_minutes_input.text())
    
    def get_relay_fail_threshold(self) -> str:
        """Get the relay fail count threshold value"""
        return self._relay_fail_threshold_input.text()
    
    def get_camera_fail_threshold(self) -> str:
        """Get the camera fail count threshold value"""
        return self._camera_fail_threshold_input.text()
    
    def get_camera_log_minutes(self) -> str:
        """Get the minutes since last camera log value"""
        return self._camera_log_minutes_input.text()
    
    def set_relay_fail_threshold(self, threshold: str):
        """Set the relay fail count threshold value"""
        self._relay_fail_threshold_input.setText(threshold)
    
    def set_camera_fail_threshold(self, threshold: str):
        """Set the camera fail count threshold value"""
        self._camera_fail_threshold_input.setText(threshold)
    
    def set_camera_log_minutes(self, minutes: str):
        """Set the minutes since last camera log value"""
        self._camera_log_minutes_input.setText(minutes)
    
    def _focus_next_field(self):
        """Focus the next input field when Enter is pressed"""
        current_widget = self.sender()
        
        if current_widget == self._relay_fail_threshold_input:
            self._camera_fail_threshold_input.setFocus()
        elif current_widget == self._camera_fail_threshold_input:
            self._camera_log_minutes_input.setFocus()

    def _confirm_save(self):
        """Show confirmation dialog before saving device settings."""
        reply = QMessageBox.question(
            self,
            "Confirm Save",
            "Are you sure you want to save the device settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._save_to_config()
            QMessageBox.information(
                self,
                "Settings Saved",
                "Device settings have been saved successfully!"
            )
