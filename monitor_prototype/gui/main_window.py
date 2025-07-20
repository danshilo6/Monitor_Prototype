from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from .widgets.navigation_bar import NavigationBar
from .widgets.info_banner import InfoBanner
from .pages.page_factory import PageFactory
from .styles import style_manager
from ..services.config_service import ConfigService

# UI Layout Constants
_WINDOW_WIDTH = 600
_WINDOW_HEIGHT = 700
_WINDOW_X = 100
_WINDOW_Y = 100
_CONTENT_MARGIN_PX = 12
_SIDEBAR_WIDTH = 200

class MainWindow(QMainWindow):
    """Main application window with navigation sidebar and content area"""
    
    _instance = None  # Singleton instance

    def __init__(self) -> None:
        super().__init__()
        MainWindow._instance = self  # Store reference for global access
        self._current_page = None
        self._content_area: QWidget
        self._nav_bar: NavigationBar
        self._info_banner: InfoBanner
        self._config_service = ConfigService.get_instance()  # Use singleton instance
        self._setup_window()
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()

    @classmethod
    def get_instance(cls):
        """Get the current MainWindow instance"""
        return cls._instance

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
            print("icon set successfully")
        else:
            print("icon not found")

    def _setup_ui(self) -> None:
        """Initialize and layout all UI components"""
        # ---- main layout (vertical to stack banner on top) --------------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ---- info banner (top) --------------------------------------------------
        self._info_banner = InfoBanner(self._config_service)
        main_layout.addWidget(self._info_banner)

        # ---- horizontal layout for navigation and content ----------------------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)  # No gap between sidebar and content
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ---- navigation sidebar ------------------------------------------------
        self._nav_bar = NavigationBar()
        self._nav_bar.setFixedWidth(_SIDEBAR_WIDTH)
        content_layout.addWidget(self._nav_bar)

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

    def _apply_styles(self) -> None:
        """Apply all stylesheets to the application"""
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
            
        except FileNotFoundError as e:
            print(f"Warning: Could not load styles: {e}")
            self._apply_fallback_styles()

    def _apply_fallback_styles(self) -> None:
        """Fallback styles if external files can't be loaded"""
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
        self._nav_bar.page_changed.connect(self._on_page_changed)

    # --------------------------------------------------------------------------
    # signal handlers
    # --------------------------------------------------------------------------

    def _on_page_changed(self, page_name: str) -> None:
        """Handle navigation page change"""
        self._update_content(page_name)

    # --------------------------------------------------------------------------
    # private helpers
    # --------------------------------------------------------------------------

    def _clear_content(self) -> None:
        """Clears all existing content area"""
        for i in reversed(range(self._content_layout.count())):
            child = self._content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

    def _update_content(self, page_name: str) -> None:
        """Update content area based on selected page"""
        if self._current_page == page_name:
            return
        self._clear_content()
        # Create and add new page
        try:
            page = PageFactory.create_page(page_name)
            self._content_layout.addWidget(page)
            self._current_page = page_name
        except ValueError as e:
            print(f"Error creating page: {e}")
            # Fallback to error page
            error_widget = self._create_error_widget(page_name)
            self._content_layout.addWidget(error_widget)
    
    def _create_error_widget(self, page_name: str) -> QWidget:
        """Create error widget for unknown pages"""
        placeholder = QLabel()
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)    
        placeholder.setText(f"Error: Page '{page_name}' not found")
        return placeholder

    def refresh_banner(self):
        """Refresh the info banner (called when settings change)"""
        if hasattr(self, '_info_banner'):
            self._info_banner.refresh()
    
    def refresh_banner_location(self):
        """Refresh only the location in the banner (for better performance)"""
        if hasattr(self, '_info_banner'):
            self._info_banner.refresh_location()
