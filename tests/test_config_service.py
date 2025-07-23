"""Tests for ConfigService"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from monitor.services.config_service import ConfigService


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "general": {
                "location_name": "Test Location",
                "monitor_program_path": "/test/path"
            },
            "versions": {
                "monitor_version": "1.0.0",
                "ein_tzofia_version": "1.0.0"
            },
            "system": {
                "enable_restart": True,
                "minutes_to_restart": "5",
                "startup_snooze_time": "5"
            },
            "devices": {
                "relay_fail_threshold": "100",
                "camera_fail_threshold": "200",
                "camera_log_minutes": "3"
            }
        }
        json.dump(test_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def config_service(temp_config_file):
    """Create ConfigService instance for testing"""
    return ConfigService(temp_config_file)


class TestConfigService:
    """Test cases for ConfigService"""

    def test_get_existing_values(self, config_service):
        """Test getting existing configuration values"""
        assert config_service.get("general", "location_name") == "Test Location"
        assert config_service.get("system", "enable_restart") is True
        assert config_service.get("devices", "relay_fail_threshold") == "100"

    def test_get_default_values(self, config_service):
        """Test getting non-existent values with defaults"""
        assert config_service.get("general", "nonexistent", "default") == "default"
        assert config_service.get("nonexistent_section", "key", "default") == "default"

    def test_set_and_get_values(self, config_service):
        """Test setting and getting configuration values"""
        config_service.set("general", "location_name", "New Location")
        assert config_service.get("general", "location_name") == "New Location"
        
        # Test creating new section
        config_service.set("new_section", "new_key", "new_value")
        assert config_service.get("new_section", "new_key") == "new_value"

    def test_save_and_load_persistence(self, temp_config_file):
        """Test that changes persist after saving"""
        # Create service and modify config
        service1 = ConfigService(temp_config_file)
        service1.set("general", "location_name", "Persistent Location")
        
        # Create new service instance and verify persistence
        service2 = ConfigService(temp_config_file)
        assert service2.get("general", "location_name") == "Persistent Location"

    def test_default_config_creation(self):
        """Test that default config is created when file doesn't exist"""
        with tempfile.NamedTemporaryFile(delete=True) as f:
            non_existent_path = f.name + "_nonexistent"
        
        service = ConfigService(non_existent_path)
        
        # Check default values are present
        assert service.get("general", "location_name") == ""
        assert service.get("system", "enable_restart") is False
        assert service.get("devices", "relay_fail_threshold") == ""
        
        # Cleanup
        if os.path.exists(non_existent_path):
            os.unlink(non_existent_path)

    def test_all_method(self, config_service):
        """Test getting all configuration data"""
        all_config = config_service.all()
        
        assert isinstance(all_config, dict)
        assert "general" in all_config
        assert "system" in all_config
        assert "devices" in all_config
        assert all_config["general"]["location_name"] == "Test Location"

    def test_thread_safety_timeout(self, config_service):
        """Test that lock timeout works correctly"""
        # This is a basic test - full thread safety testing would require more complex setup
        config_service._lock.acquire()
        try:
            # This should work since we're in the same thread (re-entrant lock)
            result = config_service.get("general", "location_name")
            assert result == "Test Location"
        finally:
            config_service._lock.release()

    def test_multiple_instances_independence(self, temp_config_file):
        """Test multiple ConfigService instances work independently"""
        instance1 = ConfigService(temp_config_file)
        instance2 = ConfigService(temp_config_file)
        
        # They should be different objects
        assert instance1 is not instance2
        
        # Changes in one instance are saved and visible to other instances
        # since they share the same file
        original_value = instance2.get("general", "location_name")
        instance1.set("general", "location_name", "Instance1 Location")
        
        # Create a new instance to verify the change was persisted
        instance3 = ConfigService(temp_config_file)
        assert instance3.get("general", "location_name") == "Instance1 Location"
