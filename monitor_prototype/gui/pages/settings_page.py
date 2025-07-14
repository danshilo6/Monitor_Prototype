"""Settings page for application configuration"""

from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from .base_page import BasePage

class SettingsPage(BasePage):
    """Application settings page"""
    
    def setup_ui(self):
        """Setup the settings page UI"""
        layout = QVBoxLayout(self)
        
        # Create placeholder content
        placeholder = QLabel()
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        formatted_content = f"""
        <div style="text-align: center;">
            <h1 style="color: #2d3142; margin-bottom: 20px;">{self.get_title()}</h1>
            <p style="color: #666; font-size: 14px; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                {self.get_description()}
            </p>
            <div style="margin-top: 30px; padding: 20px; background-color: #e9ecef; border-radius: 8px; max-width: 400px; margin-left: auto; margin-right: auto;">
                <strong>Status:</strong> All settings configured
            </div>
        </div>
        """
        
        placeholder.setText(formatted_content)
        layout.addWidget(placeholder)
    
    def get_title(self) -> str:
        """Return the page title"""
        return "Application Settings"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "Configure monitoring thresholds, notification preferences, display options, and system behaviors. Customize the application to meet your specific monitoring needs."
