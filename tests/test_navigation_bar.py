import sys
import os
import pytest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'monitor_prototype', 'gui'))

from widgets.navigation_bar import NavigationBar

class TestNavigationBar:
    """Test class for NavigationBar widget"""

    EXPECTED_BUTTONS = ["alerts", "contacts", "settings"]
    EXPECTED_DEFAULT_PAGE = "alerts"

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
        assert self.nav_bar._button_manager.button_count == len(self.EXPECTED_BUTTONS)

    def test_has_correct_button_names(self):
        for button_name in self.EXPECTED_BUTTONS:
            assert self.nav_bar._button_manager.get_button(button_name) is not None

    def test_default_selection(self):
        selected_name = self.nav_bar._button_manager.selected_name
        assert selected_name == self.EXPECTED_DEFAULT_PAGE

    def test_button_selection_changes(self):
        for button_name in self.EXPECTED_BUTTONS:
            self.nav_bar.select(button_name)
            selected_name = self.nav_bar._button_manager.selected_name
            assert selected_name == button_name, f"Expected {button_name} to be selected, but {selected_name} was selected"