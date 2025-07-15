"""Advanced settings tab"""

from PySide6.QtWidgets import (QVBoxLayout, QWidget, QLineEdit, QPushButton, 
                               QFormLayout, QCheckBox, QMessageBox, QLabel)
from PySide6.QtCore import Qt

class AdvancedSettings(QWidget):
    """Advanced settings tab widget"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the advanced settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create form layout for better alignment
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Enable Restart checkbox
        self._enable_restart_checkbox = QCheckBox("Enable Restart")
        self._enable_restart_checkbox.setObjectName("settings-checkbox")
        form_layout.addRow("", self._enable_restart_checkbox)
        
        # Force Close Ein Tzofia button
        self._force_close_btn = QPushButton("Force Close Ein Tzofia")
        self._force_close_btn.setObjectName("settings-button")
        self._force_close_btn.clicked.connect(self._confirm_force_close)
        form_layout.addRow("", self._force_close_btn)
        
        # Minutes to Restart input
        self._minutes_to_restart_input = QLineEdit()
        self._minutes_to_restart_input.setObjectName("settings-input")
        self._minutes_to_restart_input.setPlaceholderText("Enter minutes...")
        form_layout.addRow("Minutes to Restart:", self._minutes_to_restart_input)
        
        # Startup Snooze time input
        self._startup_snooze_input = QLineEdit()
        self._startup_snooze_input.setObjectName("settings-input")
        self._startup_snooze_input.setPlaceholderText("Enter snooze time...")
        form_layout.addRow("Startup Snooze Time:", self._startup_snooze_input)
        
        layout.addLayout(form_layout)
        
        # Add stretch to push content to top
        layout.addStretch()
    
    def _confirm_force_close(self):
        """Show confirmation dialog for force close"""
        reply = QMessageBox.question(
            self,
            "Confirm Force Close",
            "Are you sure you want to force close Ein Tzofia?\n\nThis will terminate the application immediately.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement force close logic
            print("Force closing Ein Tzofia...")
            # You can add the actual force close implementation here
    
    def get_enable_restart(self) -> bool:
        """Get the enable restart checkbox state"""
        return self._enable_restart_checkbox.isChecked()
    
    def get_minutes_to_restart(self) -> str:
        """Get the minutes to restart value"""
        return self._minutes_to_restart_input.text()
    
    def get_startup_snooze_time(self) -> str:
        """Get the startup snooze time value"""
        return self._startup_snooze_input.text()
    
    def set_enable_restart(self, enabled: bool):
        """Set the enable restart checkbox state"""
        self._enable_restart_checkbox.setChecked(enabled)
    
    def set_minutes_to_restart(self, minutes: str):
        """Set the minutes to restart value"""
        self._minutes_to_restart_input.setText(minutes)
    
    def set_startup_snooze_time(self, snooze_time: str):
        """Set the startup snooze time value"""
        self._startup_snooze_input.setText(snooze_time)
