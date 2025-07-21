"""Alerts page for displaying and managing system alerts"""

from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from monitor.gui.pages.base_page import BasePage
from monitor.gui.widgets.alerts_list import AlertsList
from monitor.services.alert_models import generate_dummy_alerts
from monitor.services.alert_db import AlertDatabase

class AlertsPage(BasePage):
    """Alerts management page with persistent storage"""

    def __init__(self):
        self.alert_db = AlertDatabase()
        super().__init__()
    
    def setup_ui(self):
        """Setup the alerts page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add header
        header = QLabel("Alerts List")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Changed to center
        layout.addWidget(header)
        
        # Create alerts list widget
        self._alerts_list = AlertsList()
        self._alerts_list.set_alert_database(self.alert_db)  # Connect database
        layout.addWidget(self._alerts_list)
        
        # Load alerts from database
        self._load_alerts()
    
    def _load_alerts(self):
        """Load alerts from database"""
        # Load existing alerts from database
        saved_alerts = self.alert_db.get_active_alerts()
        
        # ------ remove later --------------------------------------
        # If no saved alerts, generate dummy data (for testing)
        if not saved_alerts:
            dummy_alerts = generate_dummy_alerts()
            for alert in dummy_alerts:
                self.alert_db.add_alert(alert)  # Save to database
            saved_alerts = self.alert_db.get_active_alerts()
        # ----------------------------------------------------------
        # Display alerts in UI
        for alert in saved_alerts:
            self._alerts_list.add_alert(alert)
    
    def get_title(self) -> str:
        """Return the page title"""
        return "System Alerts"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "This page displays real-time alerts and notifications about system issues, device failures, and critical events that require immediate attention."
    
    def refresh_alerts(self):
        """Refresh the alerts list from database"""
        # Clear current display
        self._alerts_list._alerts.clear()
        self._alerts_list._table.setRowCount(0)
        
        # Reload from database
        self._load_alerts()
    
    def add_new_alert(self, alert):
        """Add new alert (called by monitoring system)"""
        self.alert_db.add_alert(alert)
        self._alerts_list.add_alert(alert)
    
    def cleanup(self):
        """Clean up resources when page is destroyed"""
        # Clean up any resources if needed
        pass
