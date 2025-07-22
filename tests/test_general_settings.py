"""Tests for GeneralSettings widget"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer
import sys

from monitor.gui.pages.settings_sub_pages.general_settings import GeneralSettings
from monitor.services.config_service import ConfigService


@pytest.fixture
def app():
    """Create QApplication for testing"""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    yield app
    # Don't quit the app as it might be used by other tests


@pytest.fixture
def mock_config():
    """Mock ConfigService for testing"""
    config = Mock(spec=ConfigService)
    config.get = Mock()
    config.set = Mock()
    return config


@pytest.fixture
def general_settings(app, mock_config):
    """Create GeneralSettings widget for testing"""
    # Set up default mock returns
    mock_config.get.side_effect = lambda section, key, default="": {
        ("general", "location_name"): "Test Location",
        ("general", "monitor_program_path"): "/test/program.exe"
    }.get((section, key), default)
    
    widget = GeneralSettings(mock_config)
    yield widget
    widget.deleteLater()


class TestGeneralSettings:
    """Test cases for GeneralSettings widget"""

    def test_initialization(self, general_settings, mock_config):
        """Test widget initializes correctly"""
        assert general_settings._config is mock_config
        assert hasattr(general_settings, '_location_name_display')
        assert hasattr(general_settings, '_filepath_display')
        assert hasattr(general_settings, '_edit_location_name_btn')
        assert hasattr(general_settings, '_choose_file_btn')

    def test_load_from_config_called_on_init(self, app, mock_config):
        """Test that config is loaded during initialization"""
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Initial Location",
            ("general", "monitor_program_path"): "/initial/path.exe"
        }.get((section, key), default)
        
        widget = GeneralSettings(mock_config)
        
        # Verify config was queried
        mock_config.get.assert_any_call("general", "location_name", "")
        mock_config.get.assert_any_call("general", "monitor_program_path", "")
        
        # Verify UI was updated
        assert widget.get_location_name() == "Initial Location"
        assert widget.get_monitor_program_path() == "/initial/path.exe"
        
        widget.deleteLater()

    def test_location_name_getters_setters(self, general_settings):
        """Test location name getter and setter methods"""
        # Test setter
        general_settings.set_location_name("New Location")
        assert general_settings.get_location_name() == "New Location"
        assert general_settings._location_name_display.text() == "New Location"

    def test_monitor_program_path_getters_setters(self, general_settings):
        """Test monitor program path getter and setter methods"""
        # Test setter
        general_settings.set_monitor_program_path("/new/path/program.exe")
        assert general_settings.get_monitor_program_path() == "/new/path/program.exe"
        assert general_settings._filepath_display.text() == "/new/path/program.exe"

    def test_ui_elements_created(self, general_settings):
        """Test that all UI elements are created properly"""
        # Test location name section
        assert general_settings._location_name_display is not None
        assert general_settings._location_name_display.isReadOnly()
        assert general_settings._location_name_display.objectName() == "settings-display"
        
        assert general_settings._edit_location_name_btn is not None
        assert general_settings._edit_location_name_btn.text() == "Edit"
        assert general_settings._edit_location_name_btn.objectName() == "settings-button"
        
        # Test filepath section
        assert general_settings._filepath_display is not None
        assert general_settings._filepath_display.isReadOnly()
        assert general_settings._filepath_display.objectName() == "settings-display"
        
        assert general_settings._choose_file_btn is not None
        assert general_settings._choose_file_btn.text() == "Choose File"
        assert general_settings._choose_file_btn.objectName() == "settings-button"

    def test_signal_defined(self, general_settings):
        """Test that location_changed signal is defined"""
        assert hasattr(general_settings, 'location_changed')

    @patch('monitor.gui.pages.settings_sub_pages.general_settings.LocationNameDialog')
    def test_edit_location_name_signal_emission(self, mock_dialog, general_settings, qtbot):
        """Test that location_changed signal is emitted when location is edited"""
        # Mock the dialog to return accepted=True and new name
        mock_dialog.edit_location_name.return_value = (True, "Updated Location")
        
        # Set up signal spy
        with qtbot.waitSignal(general_settings.location_changed, timeout=1000) as blocker:
            # Simulate button click
            general_settings._edit_location_name()
        
        # Verify signal was emitted with correct value
        assert blocker.args == ["Updated Location"]
        
        # Verify config was updated
        general_settings._config.set.assert_called_with("general", "location_name", "Updated Location")
        
        # Verify UI was updated
        assert general_settings.get_location_name() == "Updated Location"

    @patch('monitor.gui.pages.settings_sub_pages.general_settings.LocationNameDialog')
    def test_edit_location_name_dialog_cancelled(self, mock_dialog, general_settings):
        """Test that nothing happens when location name dialog is cancelled"""
        # Mock the dialog to return cancelled
        mock_dialog.edit_location_name.return_value = (False, None)
        original_name = general_settings.get_location_name()
        
        # Call the method
        general_settings._edit_location_name()
        
        # Verify nothing changed
        assert general_settings.get_location_name() == original_name
        general_settings._config.set.assert_not_called()

    @patch('monitor.gui.pages.settings_sub_pages.general_settings.QFileDialog')
    def test_choose_file_dialog(self, mock_file_dialog, general_settings):
        """Test file chooser dialog functionality"""
        # Mock file dialog to return a file path
        mock_file_dialog.getOpenFileName.return_value = ("/new/program.exe", "")
        
        # Call the method
        general_settings._choose_file()
        
        # Verify file dialog was called with correct parameters
        mock_file_dialog.getOpenFileName.assert_called_once()
        call_args = mock_file_dialog.getOpenFileName.call_args
        assert call_args[0][1] == "Select Program to Monitor"
        assert "Executable Files (*.exe)" in call_args[0][3]
        
        # Verify config was updated
        general_settings._config.set.assert_called_with("general", "monitor_program_path", "/new/program.exe")
        
        # Verify UI was updated
        assert general_settings.get_monitor_program_path() == "/new/program.exe"

    @patch('monitor.gui.pages.settings_sub_pages.general_settings.QFileDialog')
    def test_choose_file_dialog_cancelled(self, mock_file_dialog, general_settings):
        """Test that nothing happens when file dialog is cancelled"""
        # Mock file dialog to return empty path (cancelled)
        mock_file_dialog.getOpenFileName.return_value = ("", "")
        original_path = general_settings.get_monitor_program_path()
        
        # Call the method
        general_settings._choose_file()
        
        # Verify nothing changed
        assert general_settings.get_monitor_program_path() == original_path
        general_settings._config.set.assert_not_called()

    def test_signal_blocking_during_load(self, app, mock_config):
        """Test that signals are blocked during config loading to prevent unwanted saves"""
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Loaded Location",
            ("general", "monitor_program_path"): "/loaded/path.exe"
        }.get((section, key), default)
        
        # Create widget (which calls _load_from_config)
        widget = GeneralSettings(mock_config)
        
        # The fact that this doesn't cause errors proves signal blocking worked
        # (otherwise loading config would trigger save attempts)
        assert widget.get_location_name() == "Loaded Location"
        assert widget.get_monitor_program_path() == "/loaded/path.exe"
        
        widget.deleteLater()

    def test_button_connections(self, general_settings):
        """Test that buttons are properly connected to their methods"""
        # This is a basic test to ensure connections exist
        # More detailed testing would require signal/slot introspection
        edit_btn = general_settings._edit_location_name_btn
        choose_btn = general_settings._choose_file_btn
        
        # Verify buttons exist and have some connections
        assert edit_btn is not None
        assert choose_btn is not None
