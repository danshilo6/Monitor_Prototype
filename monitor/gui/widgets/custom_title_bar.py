from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                                 QVBoxLayout, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QPainter, QPen, QColor, QIcon, QPixmap
from pathlib import Path


class CustomTitleBar(QWidget):
    """Custom title bar with minimize, maximize/restore, and close buttons"""
    
    # Signals for window control
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    
    def __init__(self, title: str = "Monitor", parent=None):
        super().__init__(parent)
        self._title = title
        self._is_maximized = False
        self._drag_position = QPoint()
        
        self.setFixedHeight(40)
        self.setObjectName("custom-title-bar")
        
        self._setup_ui()
        self._load_stylesheet()
        
    def _setup_ui(self):
        """Setup the title bar UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(8)
        
        # Title label
        self._title_label = QLabel(self._title)
        self._title_label.setObjectName("title-bar-title")
        font = QFont()
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Medium)
        self._title_label.setFont(font)
        
        # Version label
        self._version_label = QLabel()
        self._version_label.setObjectName("title-bar-version")
        version_font = QFont()
        version_font.setPointSize(8)
        version_font.setWeight(QFont.Weight.Normal)
        self._version_label.setFont(version_font)
        
        # Spacer to push buttons to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Control buttons
        self._minimize_btn = self._create_control_button("−", "minimize-btn")
        self._maximize_btn = self._create_control_button("□", "maximize-btn")
        self._close_btn = self._create_control_button("×", "close-btn")
        
        # Connect button signals
        self._minimize_btn.clicked.connect(self.minimize_clicked.emit)
        self._maximize_btn.clicked.connect(self._on_maximize_clicked)
        self._close_btn.clicked.connect(self.close_clicked.emit)
        
        # Add widgets to layout
        layout.addWidget(self._title_label)
        layout.addSpacing(4)
        layout.addWidget(self._version_label)
        layout.addWidget(spacer)
        layout.addWidget(self._minimize_btn)
        layout.addWidget(self._maximize_btn)
        layout.addWidget(self._close_btn)
        
    def _create_control_button(self, text: str, object_name: str) -> QPushButton:
        """Create a control button for the title bar"""
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setFixedSize(45, 40)
        button.setFlat(True)
        
        # Set font for the symbols
        font = QFont()
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Bold)
        button.setFont(font)
        
        return button
        
    def _setup_icon(self):
        """Setup the application icon"""
        try:
            # Get the path to the icon
            icon_path = Path(__file__).parent.parent / "icons" / "ecg-monitor.png"
            if icon_path.exists():
                # Load the original image and check its resolution
                pixmap = QPixmap(str(icon_path))
                # Only scale if the image is significantly larger than our target
                if pixmap.width() > 64 or pixmap.height() > 64:
                    scaled_pixmap = pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation)
                else:
                    # Use original if it's already small to avoid quality loss
                    scaled_pixmap = pixmap
                self._icon_label.setPixmap(scaled_pixmap)
                self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                # Use a nice Unicode symbol as fallback
                self._icon_label.setText("⚡")
                font = QFont()
                font.setPointSize(18)
                font.setWeight(QFont.Weight.Bold)
                self._icon_label.setFont(font)
                self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._icon_label.setStyleSheet("color: #4fc3f7;")
        except Exception:
            # Fallback if loading fails - use a monitor symbol
            self._icon_label.setText("⚡")
            font = QFont()
            font.setPointSize(18)
            font.setWeight(QFont.Weight.Bold)
            self._icon_label.setFont(font)
            self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._icon_label.setStyleSheet("color: #4fc3f7;")
        
    def _on_maximize_clicked(self):
        """Handle maximize/restore button click"""
        self._is_maximized = not self._is_maximized
        
        # Update button symbol
        if self._is_maximized:
            self._maximize_btn.setText("❐")  # Restore symbol
        else:
            self._maximize_btn.setText("□")  # Maximize symbol
            
        self.maximize_clicked.emit()
        
    def set_title(self, title: str):
        """Set the title bar text"""
        self._title = title
        self._title_label.setText(title)
        
    def set_title_with_location(self, base_title: str, location: str):
        """Update the title to include location information"""
        if location and location.strip():
            full_title = f"{base_title} - {location}"
        else:
            full_title = base_title
        self._title = full_title
        self._title_label.setText(full_title)
        
    def set_version(self, version: str):
        """Set the version text"""
        if version and version.strip():
            self._version_label.setText(f"v{version}")
        else:
            self._version_label.setText("")
            
    def set_title_with_location_and_version(self, base_title: str, location: str, version: str):
        """Update the title with location and version information"""
        if location and location.strip():
            full_title = f"{base_title} - {location}"
        else:
            full_title = base_title
        self._title = full_title
        self._title_label.setText(full_title)
        
        # Set version
        self.set_version(version)
        
    def set_maximized_state(self, is_maximized: bool):
        """Update the maximized state (called by parent window)"""
        self._is_maximized = is_maximized
        if is_maximized:
            self._maximize_btn.setText("❐")  # Restore symbol
        else:
            self._maximize_btn.setText("□")  # Maximize symbol
    
    def _load_stylesheet(self):
        """Load the stylesheet for the title bar"""
        try:
            stylesheet_path = Path(__file__).parent.parent / "styles" / "custom_title_bar.qss"
            if stylesheet_path.exists():
                with open(stylesheet_path, 'r', encoding='utf-8') as file:
                    stylesheet = file.read()
                    self.setStyleSheet(stylesheet)
            else:
                # Fallback to basic styling if stylesheet file is not found
                self.setStyleSheet("""
                    #custom-title-bar {
                        background-color: #2c2c2c;
                        border-bottom: 1px solid #404040;
                    }
                    #title-bar-title {
                        color: #ffffff;
                        font-weight: bold;
                    }
                    #title-bar-version {
                        color: #b0b0b0;
                    }
                    #minimize-btn, #maximize-btn, #close-btn {
                        color: #ffffff;
                    }
                    #close-btn:hover {
                        background-color: #dc3545;
                        color: white;
                    }
                """)
        except Exception as e:
            # Fallback to minimal styling if loading fails
            self.setStyleSheet("#custom-title-bar { background-color: #2c2c2c; color: #ffffff; }")
        
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if (event.buttons() == Qt.MouseButton.LeftButton and 
            not self._drag_position.isNull() and 
            not self._is_maximized):
            
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to maximize/restore window"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_maximize_clicked()
            event.accept()


class CustomTitleBarWindow(QWidget):
    """A window wrapper that includes the custom title bar"""
    
    def __init__(self, title: str = "Monitor", parent=None):
        super().__init__(parent)
        self._title_bar = None
        self._content_widget = None
        self._setup_custom_window(title)
        
    def _setup_custom_window(self, title: str):
        """Setup the window with custom title bar"""
        # Remove default window frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create and add title bar
        self._title_bar = CustomTitleBar(title, self)
        main_layout.addWidget(self._title_bar)
        
        # Connect title bar signals
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        self._title_bar.maximize_clicked.connect(self._toggle_maximize)
        self._title_bar.close_clicked.connect(self.close)
        
        # Create content area
        self._content_widget = QWidget()
        self._content_widget.setObjectName("content-widget")
        main_layout.addWidget(self._content_widget)
        
        # Apply window styles
        self._load_window_stylesheet()
        
    def _toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
            self._title_bar.set_maximized_state(False)
        else:
            self.showMaximized()
            self._title_bar.set_maximized_state(True)
            
    def set_content_widget(self, widget: QWidget):
        """Set the content widget for the window"""
        if self._content_widget:
            # Remove existing content
            layout = self._content_widget.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            else:
                # Create layout if it doesn't exist
                layout = QVBoxLayout(self._content_widget)
                layout.setContentsMargins(0, 0, 0, 0)
                
            # Add new content
            layout.addWidget(widget)
            
    def get_content_widget(self) -> QWidget:
        """Get the content widget"""
        return self._content_widget
        
    def set_title(self, title: str):
        """Set the window title"""
        self._title_bar.set_title(title)
        
    def set_title_with_location(self, base_title: str, location: str):
        """Set the window title with location information"""
        self._title_bar.set_title_with_location(base_title, location)
        
    def set_version(self, version: str):
        """Set the version information"""
        self._title_bar.set_version(version)
        
    def set_title_with_location_and_version(self, base_title: str, location: str, version: str):
        """Set the window title with location and version information"""
        self._title_bar.set_title_with_location_and_version(base_title, location, version)
        
    def _load_window_stylesheet(self):
        """Load the stylesheet for the window"""
        try:
            stylesheet_path = Path(__file__).parent.parent / "styles" / "custom_title_bar.qss"
            if stylesheet_path.exists():
                with open(stylesheet_path, 'r', encoding='utf-8') as file:
                    stylesheet = file.read()
                    self.setStyleSheet(stylesheet)
            else:
                # Fallback styling
                self.setStyleSheet("""
                    #content-widget {
                        background-color: #1e1e1e;
                        border: 1px solid #404040;
                        border-top: none;
                    }
                """)
        except Exception:
            # Minimal fallback
            self.setStyleSheet("#content-widget { background-color: #1e1e1e; }")
        
    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # Update title bar maximize state based on actual window state
        self._title_bar.set_maximized_state(self.isMaximized())
