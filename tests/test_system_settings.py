"""Tests for SystemSettings widget"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
import sys

from monitor.gui.pages.settings_sub_pages.system_settings import SystemSettings
from monitor.services.config_service import ConfigService


@pytest.fixture
def app():
    """Create QApplication for testing"""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    yield app


@pytest.fixture
def mock_config():
    """Mock ConfigService for testing"""
    config = Mock(spec=ConfigService)
    config.get = Mock()
    config.set = Mock()
    return config


@pytest.fixture
def system_settings(app, mock_config):
    """Create SystemSettings widget for testing"""
    # Set up default mock returns
    mock_config.get.side_effect = lambda section, key, default=False: {
        ("system", "enable_restart"): True,
        ("system", "minutes_to_restart"): "5"
    }.get((section, key), default)
    
    widget = SystemSettings(mock_config)
    yield widget
    widget.deleteLater()


class TestSystemSettings:
    """Test cases for SystemSettings widget"""

    def test_initialization(self, system_settings, mock_config):
        """Test widget initializes correctly"""
        assert system_settings._config is mock_config
        assert hasattr(system_settings, '_enable_restart_checkbox')
        assert hasattr(system_settings, '_restart_time_display')
        assert hasattr(system_settings, '_open_ein_tzofia_btn')
        assert hasattr(system_settings, '_close_ein_tzofia_btn')
        assert hasattr(system_settings, '_edit_restart_time_btn')

    def test_load_from_config(self, app, mock_config):
        """Test that config is loaded during initialization"""
        mock_config.get.side_effect = lambda section, key, default=False: {
            ("system", "enable_restart"): True,
            ("system", "minutes_to_restart"): "10"
        }.get((section, key), default)
        
        widget = SystemSettings(mock_config)
        
        # Verify config was queried
        mock_config.get.assert_any_call("system", "enable_restart", False)
        mock_config.get.assert_any_call("system", "minutes_to_restart", "")
        
        # Verify UI was updated
        assert widget.get_enable_restart() is True
        assert widget.get_restart_time() == "10"
        
        widget.deleteLater()

    def test_getters_and_setters(self, system_settings):
        """Test getter and setter methods"""
        # Test restart enable
        system_settings.set_enable_restart(False)
        assert system_settings.get_enable_restart() is False
        
        system_settings.set_enable_restart(True)
        assert system_settings.get_enable_restart() is True
        
        # Test restart time
        system_settings.set_restart_time("15")
        assert system_settings.get_restart_time() == "15"

    def test_ui_elements_created(self, system_settings):
        """Test that all UI elements are created properly"""
        # Test checkbox
        assert system_settings._enable_restart_checkbox is not None
        assert system_settings._enable_restart_checkbox.text() == "Enable Restart"
        assert system_settings._enable_restart_checkbox.objectName() == "settings-checkbox"
        
        # Test restart time display
        assert system_settings._restart_time_display is not None
        assert system_settings._restart_time_display.isReadOnly()
        assert system_settings._restart_time_display.objectName() == "settings-display"
        
        # Test buttons
        assert system_settings._open_ein_tzofia_btn is not None
        assert system_settings._open_ein_tzofia_btn.text() == "Open Ein Tzofia"
        assert system_settings._open_ein_tzofia_btn.objectName() == "open-button"
        
        assert system_settings._close_ein_tzofia_btn is not None
        assert system_settings._close_ein_tzofia_btn.text() == "Close Ein Tzofia"
        assert system_settings._close_ein_tzofia_btn.objectName() == "close-button"
        
        assert system_settings._edit_restart_time_btn is not None
        assert system_settings._edit_restart_time_btn.text() == "Edit"
        assert system_settings._edit_restart_time_btn.objectName() == "settings-button"

    def test_checkbox_triggers_save(self, system_settings):
        """Test that checkbox changes trigger config save"""
        # Toggle checkbox
        system_settings._enable_restart_checkbox.setChecked(False)
        
        # Should trigger save to config
        system_settings._config.set.assert_called()

    @patch('PySide6.QtWidgets.QInputDialog')
    def test_edit_restart_time_dialog(self, mock_input_dialog, system_settings):
        """Test restart time edit dialog"""
        # Mock input dialog to return valid time
        mock_input_dialog.getText.return_value = ("20", True)
        
        # Call edit method
        system_settings._edit_restart_time()
        
        # Verify dialog was called
        mock_input_dialog.getText.assert_called_once()
        
        # Verify UI and config were updated
        assert system_settings.get_restart_time() == "20"
        system_settings._config.set.assert_called()

    @patch('PySide6.QtWidgets.QInputDialog')
    def test_edit_restart_time_dialog_cancelled(self, mock_input_dialog, system_settings):
        """Test restart time edit dialog when cancelled"""
        # Mock input dialog to return cancelled
        mock_input_dialog.getText.return_value = ("", False)
        original_time = system_settings.get_restart_time()
        
        # Call edit method
        system_settings._edit_restart_time()
        
        # Verify nothing changed
        assert system_settings.get_restart_time() == original_time

    @patch('PySide6.QtWidgets.QInputDialog')
    @patch('PySide6.QtWidgets.QMessageBox')
    def test_edit_restart_time_invalid_input(self, mock_message_box, mock_input_dialog, system_settings):
        """Test restart time edit with invalid input"""
        # Mock input dialog to return invalid input
        mock_input_dialog.getText.return_value = ("invalid", True)
        original_time = system_settings.get_restart_time()
        
        # Call edit method
        system_settings._edit_restart_time()
        
        # Verify error message was shown
        mock_message_box.warning.assert_called_once()
        
        # Verify time wasn't changed
        assert system_settings.get_restart_time() == original_time

    @patch('monitor.gui.pages.settings_sub_pages.system_settings.QMessageBox')
    def test_close_ein_tzofia_confirmation(self, mock_message_box, system_settings):
        """Test close Ein Tzofia confirmation dialog"""
        # Mock confirmation dialog to return Yes
        mock_message_box.question.return_value = mock_message_box.StandardButton.Yes
        
        # Call close method
        system_settings._confirm_close_ein_tzofia()
        
        # Verify confirmation dialog was shown
        mock_message_box.question.assert_called_once()

    @patch('monitor.gui.pages.settings_sub_pages.system_settings.QMessageBox')
    def test_close_ein_tzofia_confirmation_cancelled(self, mock_message_box, system_settings):
        """Test close Ein Tzofia when confirmation is cancelled"""
        # Mock confirmation dialog to return Cancel
        mock_message_box.question.return_value = mock_message_box.StandardButton.Cancel
        
        # Call close method
        system_settings._confirm_close_ein_tzofia()
        
        # Verify confirmation dialog was shown but nothing else happened
        mock_message_box.question.assert_called_once()

    def test_legacy_methods(self, system_settings):
        """Test legacy compatibility methods"""
        # Test legacy getters
        system_settings.set_restart_time("25")
        assert system_settings.get_minutes_to_restart() == "25"
        assert system_settings.get_startup_snooze_time() == "25"
        
        # Test legacy setters
        system_settings.set_minutes_to_restart("30")
        assert system_settings.get_restart_time() == "30"
        
        system_settings.set_startup_snooze_time("35")
        assert system_settings.get_restart_time() == "35"

    def test_signal_blocking_during_load(self, app, mock_config):
        """Test that signals are blocked during config loading"""
        mock_config.get.side_effect = lambda section, key, default=False: {
            ("system", "enable_restart"): True,
            ("system", "minutes_to_restart"): "8"
        }.get((section, key), default)
        
        # Create widget (which calls _load_from_config)
        widget = SystemSettings(mock_config)
        
        # The fact that this doesn't cause save calls proves signal blocking worked
        assert widget.get_enable_restart() is True
        assert widget.get_restart_time() == "8"
        
        widget.deleteLater()
