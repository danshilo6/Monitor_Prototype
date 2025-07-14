"""Alerts page for displaying and managing system alerts"""

from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from .base_page import BasePage
from widgets.alerts_list import AlertsList
from widgets.alert_data import generate_dummy_alerts

class AlertsPage(BasePage):
    """Alerts management page"""
    
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
        layout.addWidget(self._alerts_list)
        
        # Load dummy data
        self._load_alerts()
    
    def _load_alerts(self):
        """Load alerts data into the list"""
        dummy_alerts = generate_dummy_alerts()
        for alert in dummy_alerts:
            self._alerts_list.add_alert(alert)
    
    def get_title(self) -> str:
        """Return the page title"""
        return "System Alerts"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "This page displays real-time alerts and notifications about system issues, device failures, and critical events that require immediate attention."
    
    def refresh_alerts(self):
        """Refresh the alerts list (for future use)"""
        # This method can be called to refresh data from a real data source
        pass
    
    def cleanup(self):
        """Clean up resources when page is destroyed"""
        # Clean up any resources if needed
        pass
