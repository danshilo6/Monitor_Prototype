from pathlib import Path
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from monitor.gui.widgets.navigation_bar import NavigationBar
from monitor.gui.widgets.custom_title_bar import CustomTitleBarWindow
from monitor.gui.pages.alerts_page import AlertsPage
from monitor.gui.pages.restart_history_page import RestartHistoryPage
from monitor.gui.pages.contacts_page import ContactsPage
from monitor.gui.pages.settings_page import SettingsPage
from monitor.gui.styles import style_manager
from monitor.services.config_service import ConfigService
from monitor.services.alert_db import AlertDatabase
from monitor.services.contact_db import ContactDatabase
from monitor.log_setup import get_logger

# UI Layout Constants
_WINDOW_WIDTH = 800
_WINDOW_HEIGHT = 600
_WINDOW_X = 100
_WINDOW_Y = 100
_CONTENT_MARGIN_PX = 12
_SIDEBAR_WIDTH = 150

class MainWindow(CustomTitleBarWindow):
    """Main application window with navigation sidebar and content area"""

    def __init__(self, config_service: ConfigService, alert_db=None, contact_db=None, thread_manager=None) -> None:
        super().__init__("Monitor")  # Initialize with custom title bar
        self.logger = get_logger("monitor.gui.main_window")
        self.logger.info("Initializing main window")
        
        self._current_page = None
        self._content_area: QWidget
        self._nav_bar: NavigationBar
        self._config_service = config_service  # Injected dependency
        self._thread_manager = thread_manager  # Optional thread manager for graceful shutdown
        
        # Initialize databases (use injected ones or create new ones)
        if alert_db is not None:
            self._alert_db = alert_db
        else:
            from monitor.services.alert_db import AlertDatabase
            self._alert_db = AlertDatabase()
            
        if contact_db is not None:
            self._contact_db = contact_db
        else:
            from monitor.services.contact_db import ContactDatabase
            self._contact_db = ContactDatabase()
        
        try:
            self._setup_window()
            self._setup_ui()
            self._apply_styles()
            self._connect_signals()
            self._update_title_with_location()
            self.logger.info("Main window initialization completed successfully")
        except Exception as e:
            self.logger.error("Failed to initialize main window", exc_info=True)
            raise

    # --------------------------------------------------------------------------
    # private setup methods
    # --------------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure main window properties"""
        self.setGeometry(_WINDOW_X, _WINDOW_Y, _WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setMinimumSize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self._setup_window_icon()
    
    def _setup_window_icon(self) -> None:
        """sets the main window's icon"""
        icon_path = Path(__file__).parent / "icons" / "ecg-monitor.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        """Initialize and layout all UI components"""
        
        # Get the content widget from the custom title bar window
        content_widget = self.get_content_widget()
        
        # ---- main layout (horizontal for navigation and content) ---------------
        main_layout = QHBoxLayout(content_widget)
        main_layout.setSpacing(0)  # No gap between sidebar and content
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ---- navigation sidebar ------------------------------------------------
        try:
            self._nav_bar = NavigationBar()
            self._nav_bar.setFixedWidth(_SIDEBAR_WIDTH)
            main_layout.addWidget(self._nav_bar)
        except Exception as e:
            self.logger.error("Failed to create navigation bar", exc_info=True)
            raise

        # ---- content area -------------------------------------------------------
        self._content_area = QWidget()
        self._content_area.setObjectName("content-area")  # For CSS targeting
        self._content_layout = QVBoxLayout(self._content_area)
        main_layout.addWidget(self._content_area, 1)  # Takes remaining space

        # Set initial content
        self._update_content("alerts")
        self.logger.debug("UI setup completed successfully")

    def _apply_styles(self) -> None:
        """Apply all stylesheets to the application"""
        try:
            # Load and combine all required styles
            combined_styles = style_manager.get_combined_styles(
                "main_window",
                "navigation_bar",
                "alerts",
                "restart_history",
                "contacts",
                "settings"
            )
            
            # Apply to the main window
            self.setStyleSheet(combined_styles)
            
        except FileNotFoundError as e:
            self.logger.warning(f"Could not load styles: {e}, using fallback styles")
            self._apply_fallback_styles()
        except Exception as e:
            self.logger.error("Unexpected error applying styles", exc_info=True)
            self._apply_fallback_styles()

    def _apply_fallback_styles(self) -> None:
        """Fallback styles if external files can't be loaded"""
        fallback_style = """
        QMainWindow { 
            background-color: #ffffff; 
            font-family: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }
        #content-area { 
            background-color: #f8f9fa; 
            padding: 20px; 
            font-size: 16px; 
            color: #333;
        }
        NavigationBar {
            background-color: #2d3142;
            border-right: 1px solid #4f5b66;
        }
        NavigationBar QPushButton {
            background-color: #4f5d75;
            color: white;
            border: none;
            padding: 12px 16px;
            margin: 2px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: bold;
        }
        NavigationBar QPushButton:hover {
            background-color: #5a6b87;
        }
        NavigationBar QPushButton:checked {
            background-color: #ef476f;
        }
        """
        self.setStyleSheet(fallback_style)

    def _connect_signals(self) -> None:
        """Connect navigation signals to handlers"""
        try:
            self._nav_bar.page_changed.connect(self._on_page_changed)
        except Exception as e:
            self.logger.error("Failed to connect signals", exc_info=True)
            raise

    # --------------------------------------------------------------------------
    # signal handlers
    # --------------------------------------------------------------------------

    def _on_page_changed(self, page_name: str) -> None:
        """Handle navigation page change"""
        try:
            self._update_content(page_name)
        except Exception as e:
            self.logger.error(f"Failed to change to page '{page_name}'", exc_info=True)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event when user clicks the X button"""
        self.logger.info("User initiated application close via X button")
        
        # If we have a thread manager, stop threads gracefully
        if self._thread_manager:
            self.logger.info("Stopping worker threads...")
            self._thread_manager.stop_threads()
            
            # Give threads a moment to stop gracefully
            from PySide6.QtCore import QTimer
            import time
            start_time = time.time()
            while self._thread_manager.is_running and (time.time() - start_time) < 3:
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
                time.sleep(0.1)
            
            if self._thread_manager.is_running:
                self.logger.warning("Some threads did not stop gracefully within 3 seconds")
            else:
                self.logger.info("All worker threads stopped successfully")
        
        self.logger.debug("Application is shutting down gracefully")
        
        # Accept the close event to allow the application to close
        event.accept()
        
        # Call the parent's closeEvent to ensure proper cleanup
        super().closeEvent(event)

    # --------------------------------------------------------------------------
    # private helpers
    # --------------------------------------------------------------------------

    def _clear_content(self) -> None:
        """Clears all existing content area"""
        for i in reversed(range(self._content_layout.count())):
            child = self._content_layout.itemAt(i).widget()
            if child:
                # Call cleanup method if page has one
                if hasattr(child, 'cleanup') and callable(child.cleanup):
                    try:
                        child.cleanup()
                        self.logger.debug(f"Called cleanup for page widget: {type(child).__name__}")
                    except Exception as e:
                        self.logger.warning(f"Error during page cleanup: {e}")
                
                # Properly remove from layout first
                self._content_layout.removeWidget(child)
                
                # Schedule for deletion instead of just removing parent
                child.deleteLater()
                self.logger.debug(f"Scheduled page widget for deletion: {type(child).__name__}")

    def _update_content(self, page_name: str) -> None:
        """Update content area based on selected page"""
        if self._current_page == page_name:
            return
            
        self.logger.debug(f"Updating content to page: {page_name}")
        self._clear_content()
        
        # Create and add new page
        try:
            page = self._create_page(page_name)
            self._content_layout.addWidget(page)
            self._current_page = page_name
            
            # Connect signals based on page type
            self._connect_page_signals(page_name, page)
            self.logger.debug(f"Successfully loaded page: {page_name}")
            
        except ValueError as e:
            self.logger.error(f"Error creating page '{page_name}': {e}")
            # Fallback to error page
            error_widget = self._create_error_widget(page_name)
            self._content_layout.addWidget(error_widget)
            self.logger.warning(f"Displayed error widget for page: {page_name}")
        except Exception as e:
            self.logger.error(f"Unexpected error loading page '{page_name}'", exc_info=True)
            error_widget = self._create_error_widget(page_name)
            self._content_layout.addWidget(error_widget)
    
    def _create_page(self, page_name: str):
        """Create a page instance based on its specific requirements
        
        Args:
            page_name: Name of the page to create
            
        Returns:
            BasePage: Instance of the requested page
            
        Raises:
            ValueError: If the page name is not recognized
        """
        self.logger.debug(f"Creating page with specific requirements: {page_name}")
        
        if page_name == "alerts":
            # Alerts page uses signals and Model/View pattern
            return AlertsPage()
        elif page_name == "restarts":
            # Restart history page uses Model/View pattern
            return RestartHistoryPage()
        elif page_name == "contacts":
            # Contacts page uses Model/View with dependency injection
            return ContactsPage(self._contact_db)
        elif page_name == "settings":
            # Settings page uses dependency injection
            return SettingsPage(self._config_service)
        else:
            raise ValueError(f"Unknown page: {page_name}")
    
    def _connect_page_signals(self, page_name: str, page):
        """Connect signals from pages to their respective services"""
        self.logger.debug(f"Connecting signals for page: {page_name}")
        try:
            if page_name == "alerts":
                # Connect alerts page to alert database via signals (Model/View + Signals)
                page.connect_external_signals(self._alert_db)
                self.logger.debug("Alerts page signals connected successfully")
            elif page_name == "restarts":
                # Restart history page doesn't need external signals - it accesses DB directly
                self.logger.debug("Restart history page uses direct DB access - no external signals to connect")
            elif page_name == "contacts":
                # Contacts page uses Model/View with DI - no additional signals needed
                self.logger.debug("Contacts page uses dependency injection - no external signals to connect")
            elif page_name == "settings":
                # Connect settings page signals for configuration updates (DI)
                general_settings = page.get_general_settings()
                if general_settings:
                    # Settings signals connected but no banner to refresh
                    self.logger.debug("Settings page signals connected successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect signals for page '{page_name}'", exc_info=True)
    
    def _create_error_widget(self, page_name: str) -> QWidget:
        """Create error widget for unknown pages"""
        self.logger.debug(f"Creating error widget for page: {page_name}")
        placeholder = QLabel()
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)    
        placeholder.setText(f"Error: Page '{page_name}' not found")
        return placeholder
    
    def _update_title_with_location(self):
        """Update the window title to include location and version information"""
        try:
            location_name = self._config_service.get("general", "location_name", "Unknown Location")
            monitor_version = self._config_service._get_monitor_version()
            self.set_title_with_location_and_version("Monitor", location_name, monitor_version)
            self.logger.debug(f"Updated title with location: {location_name} and version: {monitor_version}")
        except Exception as e:
            self.logger.error("Failed to update title with location and version", exc_info=True)
            # Fallback to basic title
            self.set_title("Monitor")
