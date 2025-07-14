"""Contacts page for managing contact directory"""

from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from .base_page import BasePage

class ContactsPage(BasePage):
    """Contact directory page"""
    
    def setup_ui(self):
        """Setup the contacts page UI"""
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
                <strong>Status:</strong> 27 contacts available
            </div>
        </div>
        """
        
        placeholder.setText(formatted_content)
        layout.addWidget(placeholder)
    
    def get_title(self) -> str:
        """Return the page title"""
        return "Contact Directory"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "Access your complete contact directory with emergency contacts, technical support teams, and system administrators. Quickly reach the right people when issues arise."
