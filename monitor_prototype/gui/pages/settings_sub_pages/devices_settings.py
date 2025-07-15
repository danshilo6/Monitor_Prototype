"""Devices settings tab"""

from PySide6.QtWidgets import (QVBoxLayout, QWidget, QLineEdit, QFormLayout)
from PySide6.QtCore import Qt

class DevicesSettings(QWidget):
    """Devices settings tab widget"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
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
        
        layout.addLayout(form_layout)
        
        # Add stretch to push content to top
        layout.addStretch()
    
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
