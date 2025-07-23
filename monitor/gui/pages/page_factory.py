"""Page factory for creating page instances"""

from monitor.gui.pages.alerts_page import AlertsPage
from monitor.gui.pages.contacts_page import ContactsPage
from monitor.gui.pages.settings_page import SettingsPage
from monitor.gui.pages.base_page import BasePage
from monitor.services.config_service import ConfigService
from monitor.services.alert_db import AlertDatabase
from monitor.services.contact_db import ContactDatabase

class PageFactory:
    """Factory for creating page instances"""
    
    @staticmethod
    def create_page(page_name: str, config_service: ConfigService, 
                   alert_db: AlertDatabase, contact_db: ContactDatabase) -> BasePage:
        """Create a page instance based on the page name
        
        Args:
            page_name: Name of the page to create
            config_service: ConfigService instance to inject
            alert_db: AlertDatabase instance to inject
            contact_db: ContactDatabase instance to inject
            
        Returns:
            BasePage: Instance of the requested page
            
        Raises:
            ValueError: If the page name is not recognized
        """
        if page_name == "alerts":
            return AlertsPage(alert_db)
        elif page_name == "contacts":
            return ContactsPage(contact_db)
        elif page_name == "settings":
            return SettingsPage(config_service)
        else:
            raise ValueError(f"Unknown page: {page_name}")
    
    @staticmethod
    def get_available_pages() -> list[str]:
        """Get list of available page names"""
        return ["alerts", "contacts", "settings"]
