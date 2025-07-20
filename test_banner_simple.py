"""
Simple test to verify banner functionality without running the full app
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from monitor_prototype.services.config_service import ConfigService
from monitor_prototype.gui.widgets.info_banner import InfoBanner

class TestBannerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Banner Test")
        self.setGeometry(100, 100, 600, 150)
        
        # Create config service
        self.config_service = ConfigService()
        
        # Setup UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create banner
        self.banner = InfoBanner(self.config_service)
        layout.addWidget(self.banner)
        
        # Create test button
        btn_update = QPushButton("Update Location to 'Test Location'")
        btn_update.clicked.connect(self.update_location)
        layout.addWidget(btn_update)
        
    def update_location(self):
        """Test location update"""
        self.config_service.set("general", "location_name", "Test Location")
        self.banner.refresh_location()  # Manually refresh for testing

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestBannerWindow()
    window.show()
    sys.exit(app.exec())
