"""Settings page with multiple sub-pages"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QTabWidget
from PySide6.QtCore import Qt
from .base_page import BasePage
from .settings_sub_pages import GeneralSettings, AdvancedSettings, DevicesSettings

class SettingsPage(BasePage):
    """Settings page with tabbed sub-pages"""
    
    def __init__(self):
        self._general_settings = None
        self._advanced_settings = None
        self._devices_settings = None
        
        super().__init__()
    
    def setup_ui(self):
        """Setup the settings page UI with tabs"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Page header
        header = QLabel("Settings")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Create tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("settings-tabs")
        
        # Create sub-pages
        self._general_settings = GeneralSettings()
        self._advanced_settings = AdvancedSettings()
        self._devices_settings = DevicesSettings()
        
        # Add tabs
        self._tab_widget.addTab(self._general_settings, "General")
        self._tab_widget.addTab(self._advanced_settings, "System")
        self._tab_widget.addTab(self._devices_settings, "Devices")
        
        layout.addWidget(self._tab_widget)
    
    def get_general_settings(self) -> GeneralSettings:
        """Get the general settings widget"""
        return self._general_settings
    
    def get_advanced_settings(self) -> AdvancedSettings:
        """Get the advanced settings widget"""
        return self._advanced_settings
    
    def get_devices_settings(self) -> DevicesSettings:
        """Get the devices settings widget"""
        return self._devices_settings
    
    def get_title(self) -> str:
        """Return the page title"""
        return "Application Settings"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "Configure application preferences and advanced options"