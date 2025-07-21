"""Page factory for creating page instances"""

from monitor.gui.pages.alerts_page import AlertsPage
from monitor.gui.pages.contacts_page import ContactsPage
from monitor.gui.pages.settings_page import SettingsPage
from monitor.gui.pages.base_page import BasePage

class PageFactory:
    """Factory for creating page instances"""
    
    @staticmethod
    def create_page(page_name: str) -> BasePage:
        """Create a page instance based on the page name
        
        Args:
            page_name: Name of the page to create
            
        Returns:
            BasePage: Instance of the requested page
            
        Raises:
            ValueError: If the page name is not recognized
        """
        pages = {
            "alerts": AlertsPage,
            "contacts": ContactsPage,
            "settings": SettingsPage
        }
        
        page_class = pages.get(page_name)
        if page_class:
            return page_class()
        else:
            raise ValueError(f"Unknown page: {page_name}")
    
    @staticmethod
    def get_available_pages() -> list[str]:
        """Get list of available page names"""
        return ["alerts", "contacts", "settings"]
