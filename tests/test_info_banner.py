"""Tests for InfoBanner widget"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
import sys

from monitor.gui.widgets.info_banner import InfoBanner
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


@pytest.fixture
def info_banner(app, mock_config):
    """Create InfoBanner widget for testing"""
    # Set up default mock returns
    mock_config.get.side_effect = lambda section, key, default="": {
        ("general", "location_name"): "Test Location",
        ("versions", "monitor_version"): "1.0.0",
        ("versions", "ein_tzofia_version"): "2.0.0"
    }.get((section, key), default)
    
    banner = InfoBanner(mock_config)
    yield banner
    banner.deleteLater()


class TestInfoBanner:
    """Test cases for InfoBanner widget"""

    @patch('monitor_prototype.services.config_service.ConfigService.get_instance')
    def test_initialization(self, mock_get_instance, app, mock_config):
        """Test banner initializes correctly"""
        mock_get_instance.return_value = mock_config
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Test Location",
            ("versions", "monitor_version"): "1.0.0",
            ("versions", "ein_tzofia_version"): "2.0.0"
        }.get((section, key), default)
        
        banner = InfoBanner(mock_config)
        
        # Check that required attributes exist
        assert hasattr(banner, '_location_label')
        assert hasattr(banner, '_monitor_version_label')
        assert hasattr(banner, '_ein_tzofia_version_label')
        
        # Verify banner data was loaded with correct parameters
        mock_config.get.assert_any_call("general", "location_name", "Unknown Location")
        # Note: refresh_versions uses named parameters
        mock_config.get.assert_any_call(section="versions", key="monitor_version", default="Unknown")
        mock_config.get.assert_any_call(section="versions", key="ein_tzofia_version", default="Unknown")
        
        banner.deleteLater()

    @patch('monitor_prototype.services.config_service.ConfigService.get_instance')
    def test_banner_data_display(self, mock_get_instance, app, mock_config):
        """Test that banner displays correct data"""
        mock_get_instance.return_value = mock_config
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "My Location",
            ("versions", "monitor_version"): "3.0.0",
            ("versions", "ein_tzofia_version"): "4.0.0"
        }.get((section, key), default)
        
        banner = InfoBanner(mock_config)
        
        # Check that the banner labels contain expected information
        location_text = banner._location_label.text()
        monitor_text = banner._monitor_version_label.text()
        ein_tzofia_text = banner._ein_tzofia_version_label.text()
        
        assert "My Location" in location_text
        assert "3.0.0" in monitor_text
        assert "4.0.0" in ein_tzofia_text
        
        banner.deleteLater()

    @patch('monitor_prototype.services.config_service.ConfigService.get_instance')
    def test_default_values_when_config_empty(self, mock_get_instance, app, mock_config):
        """Test banner shows default values when config is empty"""
        mock_get_instance.return_value = mock_config
        mock_config.get.side_effect = lambda section, key, default="": default
        
        banner = InfoBanner(mock_config)
        
        location_text = banner._location_label.text()
        monitor_text = banner._monitor_version_label.text()
        ein_tzofia_text = banner._ein_tzofia_version_label.text()
        
        assert "Unknown Location" in location_text
        assert "Unknown" in monitor_text
        assert "Unknown" in ein_tzofia_text
        
        banner.deleteLater()

    def test_refresh_location(self, info_banner, mock_config):
        """Test refresh_location method updates location display"""
        
        # Change the mock to return new location
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Updated Location",
            ("versions", "monitor_version"): "1.0.0",
            ("versions", "ein_tzofia_version"): "2.0.0"
        }.get((section, key), default)
        
        # Call refresh
        info_banner.refresh_location()
        
        # Check that location was updated
        location_text = info_banner._location_label.text()
        assert "Updated Location" in location_text

    def test_refresh_versions(self, info_banner, mock_config):
        """Test refresh_versions method updates version display"""
        
        # Change the mock to return new versions
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Test Location",
            ("versions", "monitor_version"): "5.0.0",
            ("versions", "ein_tzofia_version"): "6.0.0"
        }.get((section, key), default)
        
        # Call refresh
        info_banner.refresh_versions()
        
        # Check that versions were updated
        monitor_text = info_banner._monitor_version_label.text()
        ein_tzofia_text = info_banner._ein_tzofia_version_label.text()
        assert "5.0.0" in monitor_text
        assert "6.0.0" in ein_tzofia_text

    def test_banner_styling(self, info_banner, mock_config):
        """Test that banner has correct styling"""
        
        # Check object name for styling
        assert info_banner.objectName() == "info-banner"
        # Check that labels exist (can't verify their objectName without knowing the implementation)
        assert hasattr(info_banner, '_location_label')
        assert hasattr(info_banner, '_monitor_version_label')
        assert hasattr(info_banner, '_ein_tzofia_version_label')

    def test_multiple_refresh_calls(self, info_banner, mock_config):
        """Test that multiple refresh calls work correctly"""
        
        # First refresh
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "First Location",
            ("versions", "monitor_version"): "1.0.0",
            ("versions", "ein_tzofia_version"): "1.0.0"
        }.get((section, key), default)
        
        info_banner.refresh_location()
        info_banner.refresh_versions()
        
        location_text = info_banner._location_label.text()
        monitor_text = info_banner._monitor_version_label.text()
        assert "First Location" in location_text
        assert "1.0.0" in monitor_text
        
        # Second refresh with different values
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Second Location",
            ("versions", "monitor_version"): "2.0.0",
            ("versions", "ein_tzofia_version"): "2.0.0"
        }.get((section, key), default)
        
        info_banner.refresh_location()
        info_banner.refresh_versions()
        
        location_text = info_banner._location_label.text()
        monitor_text = info_banner._monitor_version_label.text()
        assert "Second Location" in location_text
        assert "2.0.0" in monitor_text

    def test_banner_format_consistency(self, info_banner, mock_config):
        """Test that banner format remains consistent"""
        mock_config.get.side_effect = lambda section, key, default="": {
            ("general", "location_name"): "Test Location",
            ("versions", "monitor_version"): "1.0.0",
            ("versions", "ein_tzofia_version"): "2.0.0"
        }.get((section, key), default)
        
        info_banner.refresh_location()
        info_banner.refresh_versions()
        
        location_text = info_banner._location_label.text()
        monitor_text = info_banner._monitor_version_label.text()
        ein_tzofia_text = info_banner._ein_tzofia_version_label.text()
        
        # Check expected format in separate labels
        assert "Test Location" in location_text
        assert "1.0.0" in monitor_text
        assert "2.0.0" in ein_tzofia_text

    def test_widget_structure(self, info_banner):
        """Test that widget has correct structure"""
        # Should have separate labels for location and versions
        assert hasattr(info_banner, '_location_label')
        assert hasattr(info_banner, '_monitor_version_label')
        assert hasattr(info_banner, '_ein_tzofia_version_label')
        assert info_banner._location_label is not None
        assert info_banner._monitor_version_label is not None
        assert info_banner._ein_tzofia_version_label is not None
        assert info_banner.layout() is not None
