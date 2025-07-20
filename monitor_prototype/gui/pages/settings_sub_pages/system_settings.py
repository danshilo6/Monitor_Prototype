"""System settings tab"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, 
                               QFormLayout, QCheckBox, QMessageBox, QLabel)
from PySide6.QtCore import Qt

class SystemSettings(QWidget):
    """System settings tab widget"""

    def __init__(self, config_service):
        super().__init__()
        self._config = config_service
        self._setup_ui()
        self._load_from_config()
    
    def _setup_ui(self):
        """Setup the system settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Create form layout for better alignment
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Enable Restart checkbox
        self._enable_restart_checkbox = QCheckBox("Enable Restart")
        self._enable_restart_checkbox.setObjectName("settings-checkbox")
        self._enable_restart_checkbox.toggled.connect(self._save_to_config)
        form_layout.addRow("", self._enable_restart_checkbox)

        # Open Ein Tzofia button
        self._open_ein_tzofia_btn = QPushButton("Open Ein Tzofia")
        self._open_ein_tzofia_btn.setObjectName("open-button")
        self._open_ein_tzofia_btn.clicked.connect(self._open_ein_tzofia)
        form_layout.addRow("", self._open_ein_tzofia_btn)

        # Close Ein Tzofia button
        self._close_ein_tzofia_btn = QPushButton("Close Ein Tzofia")
        self._close_ein_tzofia_btn.setObjectName("close-button")
        self._close_ein_tzofia_btn.clicked.connect(self._confirm_close_ein_tzofia)
        form_layout.addRow("", self._close_ein_tzofia_btn)

        # Minutes to Restart input (combined with snooze time)
        restart_time_layout = QHBoxLayout()
        
        # Time display (read-only)
        self._restart_time_display = QLineEdit()
        self._restart_time_display.setObjectName("settings-display")
        self._restart_time_display.setReadOnly(True)
        self._restart_time_display.setPlaceholderText("Enter restart/snooze time...")
        
        # Edit button
        self._edit_restart_time_btn = QPushButton("Edit")
        self._edit_restart_time_btn.setObjectName("settings-button")
        self._edit_restart_time_btn.clicked.connect(self._edit_restart_time)
        
        # Add to layout
        restart_time_layout.addWidget(self._restart_time_display)
        restart_time_layout.addWidget(self._edit_restart_time_btn)
        
        form_layout.addRow("Restart/Snooze Time (minutes):", restart_time_layout)

        layout.addLayout(form_layout)

        # Add stretch to push content to top
        layout.addStretch()

    def _load_from_config(self):
        # Block signals to prevent saving during load
        self._enable_restart_checkbox.blockSignals(True)
        self._restart_time_display.blockSignals(True)
        
        # Load values (use the same value for both restart and snooze)
        self._enable_restart_checkbox.setChecked(self._config.get("system", "enable_restart", False))
        restart_time = self._config.get("system", "minutes_to_restart", "")
        self._restart_time_display.setText(str(restart_time))
        
        # Re-enable signals
        self._enable_restart_checkbox.blockSignals(False)
        self._restart_time_display.blockSignals(False)

    def _save_to_config(self):
        self._config.set("system", "enable_restart", self._enable_restart_checkbox.isChecked())
        # Save the same value for both restart and snooze time
        restart_time = self._restart_time_display.text()
        self._config.set("system", "minutes_to_restart", restart_time)
        self._config.set("system", "startup_snooze_time", restart_time)
    
    def _edit_restart_time(self):
        """Open dialog to edit restart/snooze time"""
        from PySide6.QtWidgets import QInputDialog
        current_time = self._restart_time_display.text()
        
        time_value, ok = QInputDialog.getText(
            self,
            "Edit Restart/Snooze Time", 
            "Enter time in minutes:",
            text=current_time
        )
        
        if ok and time_value:
            # Validate that it's a number
            try:
                float(time_value)  # Check if it's a valid number
                self._restart_time_display.setText(time_value)
                self._save_to_config()
            except ValueError:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
    
    def _open_ein_tzofia(self):
        """Open Ein Tzofia - placeholder implementation"""
        print("Opening Ein Tzofia...")
        # TODO: Implement open logic
    
    def _confirm_close_ein_tzofia(self):
        """Show confirmation dialog for closing Ein Tzofia"""
        reply = QMessageBox.question(
            self,
            "Confirm Close",
            "Are you sure you want to close Ein Tzofia?\n\nThis will terminate the application.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement close logic
            print("Closing Ein Tzofia...")
            # You can add the actual close implementation here
    
    def get_enable_restart(self) -> bool:
        """Get the enable restart checkbox state"""
        return self._enable_restart_checkbox.isChecked()
    
    def get_restart_time(self) -> str:
        """Get the restart/snooze time value"""
        return self._restart_time_display.text()
    
    def set_enable_restart(self, enabled: bool):
        """Set the enable restart checkbox state"""
        self._enable_restart_checkbox.setChecked(enabled)
    
    def set_restart_time(self, time: str):
        """Set the restart/snooze time value"""
        self._restart_time_display.setText(time)
    
    # Legacy methods for backward compatibility
    def get_minutes_to_restart(self) -> str:
        """Get the minutes to restart value (legacy)"""
        return self.get_restart_time()
    
    def get_startup_snooze_time(self) -> str:
        """Get the startup snooze time value (legacy)"""
        return self.get_restart_time()
    
    def set_minutes_to_restart(self, minutes: str):
        """Set the minutes to restart value (legacy)"""
        self.set_restart_time(minutes)
    
    def set_startup_snooze_time(self, snooze_time: str):
        """Set the startup snooze time value (legacy)"""
        self.set_restart_time(snooze_time) 