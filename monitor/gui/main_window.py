from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from monitor.gui.widgets.navigation_bar import NavigationBar
from monitor.gui.widgets.info_banner import InfoBanner
from monitor.gui.pages.page_factory import PageFactory
from monitor.gui.styles import style_manager
from monitor.services.config_service import ConfigService
from monitor.services.alert_db import AlertDatabase
from monitor.services.contact_db import ContactDatabase
from monitor.log_setup import get_logger

# UI Layout Constants
_WINDOW_WIDTH = 600
_WINDOW_HEIGHT = 700
_WINDOW_X = 100
_WINDOW_Y = 100
_CONTENT_MARGIN_PX = 12
_SIDEBAR_WIDTH = 200

class MainWindow(QMainWindow):
    """Main application window with navigation sidebar and content area"""

    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self.logger = get_logger("monitor.gui.main_window")
        self.logger.info("Initializing main window")
        
        self._current_page = None
        self._content_area: QWidget
        self._nav_bar: NavigationBar
        self._info_banner: InfoBanner
        self._config_service = config_service  # Injected dependency
        
        # Initialize databases early to avoid lazy loading delays
        self._alert_db = AlertDatabase()
        self._contact_db = ContactDatabase()
        
        try:
            self._setup_window()
            self._setup_ui()
            self._apply_styles()
            self._connect_signals()
            self.logger.info("Main window initialization completed successfully")
        except Exception as e:
            self.logger.error("Failed to initialize main window", exc_info=True)
            raise

    # --------------------------------------------------------------------------
    # private setup methods
    # --------------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure main window properties"""
        self.setWindowTitle("Monitor")
        self.setGeometry(_WINDOW_X, _WINDOW_Y, _WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setMinimumSize(800, 600)
        self._setup_window_icon()
    
    def _setup_window_icon(self) -> None:
        """sets the main window's icon"""
        icon_path = Path(__file__).parent / "icons" / "ecg-monitor.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        """Initialize and layout all UI components"""
        self.logger.debug("Setting up UI components")
        
        # ---- main layout (vertical to stack banner on top) --------------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ---- info banner (top) --------------------------------------------------
        try:
            self._info_banner = InfoBanner(self._config_service)
            main_layout.addWidget(self._info_banner)
            self.logger.debug("Info banner created and added")
        except Exception as e:
            self.logger.error("Failed to create info banner", exc_info=True)
            raise

        # ---- horizontal layout for navigation and content ----------------------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)  # No gap between sidebar and content
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ---- navigation sidebar ------------------------------------------------
        try:
            self._nav_bar = NavigationBar()
            self._nav_bar.setFixedWidth(_SIDEBAR_WIDTH)
            content_layout.addWidget(self._nav_bar)
            self.logger.debug(f"Navigation bar created with width: {_SIDEBAR_WIDTH}px")
        except Exception as e:
            self.logger.error("Failed to create navigation bar", exc_info=True)
            raise

        # ---- content area -------------------------------------------------------
        self._content_area = QWidget()
        self._content_area.setObjectName("content-area")  # For CSS targeting
        self._content_layout = QVBoxLayout(self._content_area)
        content_layout.addWidget(self._content_area, 1)  # Takes remaining space

        # Add horizontal layout to main layout
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, 1)  # Takes remaining space

        # Set initial content
        self._update_content("alerts")
        self.logger.debug("UI setup completed successfully")

    def _apply_styles(self) -> None:
        """Apply all stylesheets to the application"""
        self.logger.debug("Applying stylesheets")
        try:
            # Load and combine all required styles
            combined_styles = style_manager.get_combined_styles(
                "main_window",
                "navigation_bar",
                "info_banner",
                "alerts",
                "contacts",
                "settings"
            )
            
            # Apply to the main window
            self.setStyleSheet(combined_styles)
            self.logger.debug("Stylesheets applied successfully")
            
        except FileNotFoundError as e:
            self.logger.warning(f"Could not load styles: {e}, using fallback styles")
            self._apply_fallback_styles()
        except Exception as e:
            self.logger.error("Unexpected error applying styles", exc_info=True)
            self._apply_fallback_styles()

    def _apply_fallback_styles(self) -> None:
        """Fallback styles if external files can't be loaded"""
        self.logger.debug("Applying fallback styles")
        fallback_style = """
        QMainWindow { 
            background-color: #ffffff; 
            font-family: "Segoe UI", Arial, sans-serif;
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
        self.logger.debug("Connecting signal handlers")
        try:
            self._nav_bar.page_changed.connect(self._on_page_changed)
            self.logger.debug("Navigation signals connected successfully")
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
            self.logger.debug(f"Page change to '{page_name}' completed successfully")
        except Exception as e:
            self.logger.error(f"Failed to change to page '{page_name}'", exc_info=True)

    # --------------------------------------------------------------------------
    # private helpers
    # --------------------------------------------------------------------------

    def _clear_content(self) -> None:
        """Clears all existing content area"""
        self.logger.debug("Clearing content area")
        widgets_cleared = 0
        for i in reversed(range(self._content_layout.count())):
            child = self._content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
                widgets_cleared += 1
        self.logger.debug(f"Cleared {widgets_cleared} widgets from content area")

    def _update_content(self, page_name: str) -> None:
        """Update content area based on selected page"""
        if self._current_page == page_name:
            self.logger.debug(f"Page '{page_name}' already active, skipping update")
            return
            
        self.logger.debug(f"Updating content to page: {page_name}")
        self._clear_content()
        
        # Create and add new page
        try:
            page = PageFactory.create_page(page_name, self._config_service, self._alert_db, self._contact_db)
            self._content_layout.addWidget(page)
            self._current_page = page_name
            
            # Connect signals if it's a settings page
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
    
    def _connect_page_signals(self, page_name: str, page):
        """Connect signals from pages to main window"""
        self.logger.debug(f"Connecting signals for page: {page_name}")
        try:
            if page_name == "settings":
                # Connect the location changed signal from general settings
                general_settings = page.get_general_settings()
                if general_settings:
                    general_settings.location_changed.connect(self.refresh_banner_location)
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

    def refresh_banner(self):
        """Refresh the info banner (called when settings change)"""
        self.logger.debug("Refreshing info banner")
        try:
            if hasattr(self, '_info_banner'):
                self._info_banner.refresh()
                self.logger.debug("Info banner refreshed successfully")
        except Exception as e:
            self.logger.error("Failed to refresh info banner", exc_info=True)
    
    def refresh_banner_location(self):
        """Refresh only the location in the banner (for better performance)"""
        self.logger.debug("Refreshing banner location")
        try:
            if hasattr(self, '_info_banner'):
                self._info_banner.refresh_location()
                self.logger.debug("Banner location refreshed successfully")
        except Exception as e:
            self.logger.error("Failed to refresh banner location", exc_info=True)
