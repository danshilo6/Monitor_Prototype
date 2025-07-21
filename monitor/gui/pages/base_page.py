"""Base page class for all application pages"""

from PySide6.QtWidgets import QWidget

class BasePage(QWidget):
    """Base class for all application pages"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the page's UI components - override in subclasses"""
        raise NotImplementedError("Subclasses must implement setup_ui()")
    
    def get_title(self) -> str:
        """Return the page title - override in subclasses"""
        raise NotImplementedError("Subclasses must implement get_title()")
    
    def get_description(self) -> str:
        """Return the page description (optional override)"""
        return "Page description not provided"
    
    def cleanup(self):
        """Clean up resources when page is destroyed (optional override)"""
        pass
