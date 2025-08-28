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

        # Check EinTzofia Running checkbox
        self._check_eintzofia_running_checkbox = QCheckBox("Check if EinTzofia is running before restart")
        self._check_eintzofia_running_checkbox.setObjectName("settings-checkbox")
        self._check_eintzofia_running_checkbox.toggled.connect(self._save_to_config)
        form_layout.addRow("", self._check_eintzofia_running_checkbox)

        # Enable EinTzofia Auto-reopen checkbox
        self._enable_eintzofia_auto_reopen_checkbox = QCheckBox("Enable auto-open EinTzofia")
        self._enable_eintzofia_auto_reopen_checkbox.setObjectName("settings-checkbox")
        self._enable_eintzofia_auto_reopen_checkbox.toggled.connect(self._save_to_config)
        form_layout.addRow("", self._enable_eintzofia_auto_reopen_checkbox)

        # Enable Device Failure Emails checkbox
        self._enable_device_failure_emails_checkbox = QCheckBox("Enable device failure emails")
        self._enable_device_failure_emails_checkbox.setObjectName("settings-checkbox")
        self._enable_device_failure_emails_checkbox.toggled.connect(self._save_to_config)
        form_layout.addRow("", self._enable_device_failure_emails_checkbox)

        # Enable Restart Emails checkbox
        self._enable_restart_emails_checkbox = QCheckBox("Enable restart notification emails")
        self._enable_restart_emails_checkbox.setObjectName("settings-checkbox")
        self._enable_restart_emails_checkbox.toggled.connect(self._save_to_config)
        form_layout.addRow("", self._enable_restart_emails_checkbox)

        # Restart/Snooze Time title
        restart_time_title = QLabel("Restart/Snooze Time (minutes):")
        form_layout.addRow("", restart_time_title)
        
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
        
        form_layout.addRow("", restart_time_layout)

        # Decision Engine Cycle Timer section (properly indented inside method)
        decision_cycle_title = QLabel("Decision Engine Cycle (seconds):")
        form_layout.addRow("", decision_cycle_title)

        decision_cycle_layout = QHBoxLayout()
        self._decision_cycle_display = QLineEdit()
        self._decision_cycle_display.setObjectName("settings-display")
        self._decision_cycle_display.setReadOnly(True)
        self._decision_cycle_display.setPlaceholderText("Enter cycle time in seconds...")
        self._edit_decision_cycle_btn = QPushButton("Edit")
        self._edit_decision_cycle_btn.setObjectName("settings-button")
        self._edit_decision_cycle_btn.clicked.connect(self._edit_decision_cycle)
        decision_cycle_layout.addWidget(self._decision_cycle_display)
        decision_cycle_layout.addWidget(self._edit_decision_cycle_btn)
        form_layout.addRow("", decision_cycle_layout)

        layout.addLayout(form_layout)

        # Add stretch to push content to top
        layout.addStretch()

    def _load_from_config(self):
        # Block signals to prevent saving during load
        self._enable_restart_checkbox.blockSignals(True)
        self._check_eintzofia_running_checkbox.blockSignals(True)
        self._enable_eintzofia_auto_reopen_checkbox.blockSignals(True)
        self._enable_device_failure_emails_checkbox.blockSignals(True)
        self._enable_restart_emails_checkbox.blockSignals(True)
        self._restart_time_display.blockSignals(True)
        if hasattr(self, '_decision_cycle_display'):
            self._decision_cycle_display.blockSignals(True)
        
        # Load values (use the same value for both restart and snooze)
        self._enable_restart_checkbox.setChecked(self._config.get("system", "enable_restart", False))
        self._check_eintzofia_running_checkbox.setChecked(self._config.get("system", "check_eintzofia_running", True))
        self._enable_eintzofia_auto_reopen_checkbox.setChecked(self._config.get("system", "enable_eintzofia_auto_reopen", True))
        self._enable_device_failure_emails_checkbox.setChecked(self._config.get("system", "enable_device_failure_emails", True))
        self._enable_restart_emails_checkbox.setChecked(self._config.get("system", "enable_restart_emails", True))
        restart_time = self._config.get("system", "minutes_to_restart", "")
        self._restart_time_display.setText(str(restart_time))
        decision_cycle = self._config.get("system", "decision_cycle_seconds", "")
        if hasattr(self, '_decision_cycle_display'):
            self._decision_cycle_display.setText(str(decision_cycle))
        
        # Re-enable signals
        self._enable_restart_checkbox.blockSignals(False)
        self._check_eintzofia_running_checkbox.blockSignals(False)
        self._enable_eintzofia_auto_reopen_checkbox.blockSignals(False)
        self._enable_device_failure_emails_checkbox.blockSignals(False)
        self._enable_restart_emails_checkbox.blockSignals(False)
        self._restart_time_display.blockSignals(False)
        if hasattr(self, '_decision_cycle_display'):
            self._decision_cycle_display.blockSignals(False)

    def _save_to_config(self):
        self._config.set("system", "enable_restart", self._enable_restart_checkbox.isChecked())
        self._config.set("system", "check_eintzofia_running", self._check_eintzofia_running_checkbox.isChecked())
        self._config.set("system", "enable_eintzofia_auto_reopen", self._enable_eintzofia_auto_reopen_checkbox.isChecked())
        self._config.set("system", "enable_device_failure_emails", self._enable_device_failure_emails_checkbox.isChecked())
        self._config.set("system", "enable_restart_emails", self._enable_restart_emails_checkbox.isChecked())
        # Save the same value for both restart and snooze time
        restart_time = self._restart_time_display.text()
        self._config.set("system", "minutes_to_restart", restart_time)
        self._config.set("system", "startup_snooze_time", restart_time)
        if hasattr(self, '_decision_cycle_display'):
            self._config.set("system", "decision_cycle_seconds", self._decision_cycle_display.text())
    
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
    
    def _edit_decision_cycle(self):
        """Open dialog to edit decision engine cycle seconds"""
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        current = self._decision_cycle_display.text()
        value, ok = QInputDialog.getText(
            self,
            "Edit Decision Cycle",
            "Enter cycle time in seconds:",
            text=current
        )
        if ok and value:
            try:
                float(value)
                self._decision_cycle_display.setText(value)
                self._save_to_config()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
    
    def get_enable_restart(self) -> bool:
        """Get the enable restart checkbox state"""
        return self._enable_restart_checkbox.isChecked()
    
    def get_check_eintzofia_running(self) -> bool:
        """Get the check EinTzofia running checkbox state"""
        return self._check_eintzofia_running_checkbox.isChecked()
    
    def get_restart_time(self) -> str:
        """Get the restart/snooze time value"""
        return self._restart_time_display.text()
    
    def set_enable_restart(self, enabled: bool):
        """Set the enable restart checkbox state"""
        self._enable_restart_checkbox.setChecked(enabled)
    
    def set_check_eintzofia_running(self, enabled: bool):
        """Set the check EinTzofia running checkbox state"""
        self._check_eintzofia_running_checkbox.setChecked(enabled)
    
    def set_restart_time(self, time: str):
        """Set the restart/snooze time value"""
        self._restart_time_display.setText(time)
    
    def get_decision_cycle_seconds(self) -> str:
        return getattr(self, '_decision_cycle_display', None).text() if hasattr(self, '_decision_cycle_display') else ""

    def set_decision_cycle_seconds(self, seconds: str):
        if hasattr(self, '_decision_cycle_display'):
            self._decision_cycle_display.setText(seconds)
    
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