from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from widgets.navigation_bar import NavigationBar
from styles import style_manager

# UI Layout Constants
_WINDOW_WIDTH = 1000
_WINDOW_HEIGHT = 700
_WINDOW_X = 100
_WINDOW_Y = 100
_CONTENT_MARGIN_PX = 12
_SIDEBAR_WIDTH = 200

class MainWindow(QMainWindow):
    """Main application window with navigation sidebar and content area"""

    def __init__(self) -> None:
        super().__init__()
        self._content_area: QLabel = None
        self._nav_bar: NavigationBar = None
        self._setup_window()
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()

    # --------------------------------------------------------------------------
    # private setup methods
    # --------------------------------------------------------------------------

    def _setup_window(self) -> None:
        """Configure main window properties"""
        self.setWindowTitle("Monitor Prototype")
        self.setGeometry(_WINDOW_X, _WINDOW_Y, _WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setMinimumSize(800, 600)

    def _setup_ui(self) -> None:
        """Initialize and layout all UI components"""
        # ---- main layout -------------------------------------------------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setSpacing(0)  # No gap between sidebar and content
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- navigation sidebar ------------------------------------------------
        self._nav_bar = NavigationBar()
        self._nav_bar.setFixedWidth(_SIDEBAR_WIDTH)
        layout.addWidget(self._nav_bar)

        # ---- content area -------------------------------------------------------
        self._content_area = QLabel()
        self._content_area.setObjectName("content-area")  # For CSS targeting
        self._content_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._content_area, 1)  # Takes remaining space

        # Set initial content
        self._update_content("alerts")

    def _apply_styles(self) -> None:
        """Apply all stylesheets to the application"""
        try:
            # Load and combine all required styles
            combined_styles = style_manager.get_combined_styles(
                "main_window",
                "navigation_bar"
            )
            
            # Apply to the main window
            self.setStyleSheet(combined_styles)
            
        except FileNotFoundError as e:
            print(f"Warning: Could not load styles: {e}")
            # Fallback to minimal inline styles if files don't exist
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
            padding: 40px; 
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

    def _update_content(self, page_name: str) -> None:
        """Update content area based on selected page"""
        content_data = self._get_page_content(page_name)
        
        formatted_content = f"""
        <div style="text-align: center;">
            <h1 style="color: #2d3142; margin-bottom: 20px;">{content_data['title']}</h1>
            <p style="color: #666; font-size: 14px; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                {content_data['description']}
            </p>
            <div style="margin-top: 30px; padding: 20px; background-color: #e9ecef; border-radius: 8px; max-width: 400px; margin-left: auto; margin-right: auto;">
                <strong>Status:</strong> {content_data['status']}
            </div>
        </div>
        """
        
        self._content_area.setText(formatted_content)

    def _get_page_content(self, page_name: str) -> dict:
        """Get content data for the specified page"""
        content_map = {
            "alerts": {
                "title": "System Alerts",
                "description": "This page displays real-time alerts and notifications about system issues, device failures, and critical events that require immediate attention.",
                "status": "3 active alerts require attention"
            },
            "contacts": {
                "title": "Contact Directory",
                "description": "Access your complete contact directory with emergency contacts, technical support teams, and system administrators. Quickly reach the right people when issues arise.",
                "status": "27 contacts available"
            },
            "settings": {
                "title": "Application Settings",
                "description": "Configure monitoring thresholds, notification preferences, display options, and system behaviors. Customize the application to meet your specific monitoring needs.",
                "status": "All settings configured"
            }
        }
        
        return content_map.get(page_name, {
            "title": "Unknown Page",
            "description": f"The requested page '{page_name}' could not be found.",
            "status": "Page not found"
        })
