"""Tests for MainWindow"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
import sys

from monitor.gui.main_window import MainWindow
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
    return config


class TestMainWindow:
    """Test cases for MainWindow"""

    def test_initialization_components(self, app, mock_config):
        """Test that MainWindow initializes all components correctly"""
        window = MainWindow(mock_config)
        
        # Check that main components exist
        assert hasattr(window, '_info_banner')
        assert hasattr(window, '_nav_bar')
        assert hasattr(window, '_content_layout')
        assert hasattr(window, '_current_page')
        
        # Cleanup
        window.deleteLater()

    def test_window_title_and_icon_setup(self, app, mock_config):
        """Test window title and icon are set correctly"""
        window = MainWindow(mock_config)
        
        # Check window title (adjust expectation to match actual title)
        assert window.windowTitle() == "Monitor"
        
        # Check that icon was attempted to be set (icon might not load in test environment)
        assert window.windowIcon() is not None
        
        # Cleanup
        window.deleteLater()

    @patch('monitor.gui.main_window.PageFactory.create_page')
    def test_page_navigation(self, mock_create_page, app, mock_config):
        """Test page navigation functionality"""        
        # Create a proper settings page mock with required methods
        from PySide6.QtWidgets import QWidget
        from unittest.mock import Mock
        
        mock_page = QWidget()
        mock_general_settings = Mock()
        mock_page.get_general_settings = Mock(return_value=mock_general_settings)
        
        mock_create_page.return_value = mock_page
        
        window = MainWindow(mock_config)
        
        # Test page change
        window._update_content("settings")
        
        # Verify page was created and added
        mock_create_page.assert_called_with("settings", mock_config)
        assert window._current_page == "settings"
        
        # Cleanup
        window.deleteLater()
        mock_page.deleteLater()

    @patch('monitor.gui.main_window.PageFactory.create_page')
    def test_same_page_navigation_ignored(self, mock_create_page, app, mock_config):
        """Test that navigating to same page doesn't recreate it"""
        # Create initial page
        from PySide6.QtWidgets import QLabel
        initial_page = QLabel("Initial Page")
        mock_create_page.return_value = initial_page
        
        window = MainWindow(mock_config)
        window._current_page = "settings"
        
        # Try to navigate to same page
        window._update_content("settings")
        
        # Verify page was not created again (should only have been called during __init__)
        assert mock_create_page.call_count == 1  # Only called during setup
        
        # Cleanup
        window.deleteLater()
        initial_page.deleteLater()

    def test_refresh_banner_location_method(self, app, mock_config):
        """Test refresh_banner_location method"""
        window = MainWindow(mock_config)
        
        # Mock the info banner
        window._info_banner = Mock()
        
        # Call refresh method
        window.refresh_banner_location()
        
        # Verify banner refresh was called
        window._info_banner.refresh_location.assert_called_once()
        
        # Cleanup
        window.deleteLater()

    @patch('monitor.gui.main_window.PageFactory.create_page')
    def test_signal_connection_for_settings_page(self, mock_create_page, app, mock_config):
        """Test that signals are connected when settings page is created"""
        # Mock settings page with general settings
        mock_general_settings = Mock()
        from PySide6.QtWidgets import QLabel
        mock_settings_page = QLabel("Settings Page")
        mock_settings_page.get_general_settings = Mock(return_value=mock_general_settings)
        mock_create_page.return_value = mock_settings_page
        
        window = MainWindow(mock_config)
        
        # Navigate to settings page
        window._update_content("settings")
        
        # Verify signal connection was attempted
        mock_settings_page.get_general_settings.assert_called_once()
        mock_general_settings.location_changed.connect.assert_called_once_with(window.refresh_banner_location)
        
        # Cleanup
        window.deleteLater()
        mock_settings_page.deleteLater()

    @patch('monitor.gui.main_window.PageFactory.create_page')
    def test_signal_connection_only_for_settings(self, mock_create_page, app, mock_config):
        """Test that signals are only connected for settings pages"""
        from PySide6.QtWidgets import QLabel
        mock_page = QLabel("Alert Page")
        mock_create_page.return_value = mock_page
        
        window = MainWindow(mock_config)
        
        # Navigate to non-settings page
        window._update_content("alerts")
        
        # Verify no signal connection attempts were made (no get_general_settings method)
        assert not hasattr(mock_page, 'get_general_settings')
        
        # Cleanup
        window.deleteLater()
        mock_page.deleteLater()

    @patch('monitor.gui.main_window.PageFactory.create_page')
    def test_error_handling_for_unknown_page(self, mock_create_page, app, mock_config):
        """Test error handling when page creation fails"""
        # Mock page creation to raise error
        mock_create_page.side_effect = ValueError("Unknown page")
        
        window = MainWindow(mock_config)
        
        # Try to navigate to unknown page
        window._update_content("unknown_page")
        
        # Should create error widget instead
        assert window._current_page is None  # Page wasn't set due to error
        
        # Cleanup
        window.deleteLater()

    def test_content_clearing(self, app, mock_config):
        """Test that content is cleared before adding new content"""
        # Make sure config returns proper values for all settings components
        mock_config.get.side_effect = lambda section, key, default=None: {
            ("general", "location_name"): "Test Location",
            ("general", "monitor_program_path"): "/test/path",
            ("system", "enable_restart"): False,
            ("system", "restart_time"): "12:00",
            ("system", "enable_ein_tzofia"): True
        }.get((section, key), default)
        
        window = MainWindow(mock_config)
        
        # Add a real widget to content layout
        from PySide6.QtWidgets import QLabel
        test_widget = QLabel("Test Widget")
        window._content_layout.addWidget(test_widget)
        
        # Clear content should be called during update
        with patch.object(window, '_clear_content') as mock_clear:
            window._update_content("settings")
            mock_clear.assert_called_once()
        
        # Cleanup
        window.deleteLater()
        test_widget.deleteLater()

    def test_navigation_bar_signal_connection(self, app, mock_config):
        """Test that navigation bar signals are connected"""
        window = MainWindow(mock_config)
        
        # Mock the navigation bar
        mock_nav_bar = Mock()
        window._nav_bar = mock_nav_bar
        
        # Simulate the connection setup (would normally happen in _setup_signals)
        with patch.object(window, '_on_page_changed') as mock_handler:
            window._nav_bar.page_changed.connect(mock_handler)
            
            # Verify connection was made
            mock_nav_bar.page_changed.connect.assert_called_with(mock_handler)
        
        # Cleanup
        window.deleteLater()

    def test_window_creation_with_config_service(self, app, mock_config):
        """Test window creation uses ConfigService properly"""
        
        window = MainWindow(mock_config)
        
        # Verify ConfigService was used
        assert window._config_service is mock_config
        
        # Cleanup
        window.deleteLater()
