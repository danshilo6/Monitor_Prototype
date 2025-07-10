import sys
import os
import pytest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'monitor_prototype', 'gui'))

from widgets.navigation_bar import NavigationBar

class TestNavigationBar:
    """Test class for NavigationBar widget"""

    EXPECTED_BUTTONS = ["failing_devices", "contacts", "settings"]

    def setup_method(self):
        """This runs before each test -  creates a QApplication if needed"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        self.nav_bar = NavigationBar()

    def test_navigation_bar_created_successfully(self):
        assert self.nav_bar is not None

    def test_has_correct_number_of_buttons(self):
        assert len(self.nav_bar._btn_map) == len(self.EXPECTED_BUTTONS)

    def test_has_correct_button_names(self):
        for button_name in self.EXPECTED_BUTTONS:
            assert button_name in self.nav_bar._btn_map