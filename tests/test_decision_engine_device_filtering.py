"""
Test for DecisionEngine device filtering functionality.
Tests that devices with no device type are properly ignored.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from datetime import datetime
from monitor.core.decision_engine import DecisionEngine
from monitor.services.devices_models import DeviceInfo, DeviceType
from monitor.services.config_service import ConfigService


@pytest.fixture
def mock_config_service():
    """Mock config service with default settings"""
    config = Mock(spec=ConfigService)
    config.get.return_value = None
    return config


@pytest.fixture
def mock_devices_db():
    """Mock devices database with test devices"""
    db = Mock()
    
    # Create test devices with various device types
    test_devices = {
        "device_valid_camera": DeviceInfo(
            device_id="device_valid_camera",
            device_type="camera",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        ),
        "device_valid_relay": DeviceInfo(
            device_id="device_valid_relay", 
            device_type="relay",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        ),
        "device_none_type": DeviceInfo(
            device_id="device_none_type",
            device_type=None,
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        ),
        "device_empty_type": DeviceInfo(
            device_id="device_empty_type",
            device_type="",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        ),
        "device_whitespace_type": DeviceInfo(
            device_id="device_whitespace_type",
            device_type="   ",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        ),
        "device_unknown_type": DeviceInfo(
            device_id="device_unknown_type",
            device_type="unknown",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        ),
        "device_unknown_case": DeviceInfo(
            device_id="device_unknown_case",
            device_type="UNKNOWN",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
        )
    }
    
    db.get_all.return_value = test_devices
    return db


@pytest.fixture
def decision_engine(qapp, mock_config_service, mock_devices_db, tmp_path):
    """Create DecisionEngine with mocked dependencies"""
    logs_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"
    logs_dir.mkdir()
    data_dir.mkdir()
    
    with patch('monitor.core.decision_engine.LogProcessor'), \
         patch('monitor.core.decision_engine.DevicesDatabase', return_value=mock_devices_db), \
         patch('monitor.core.decision_engine.ContactDatabase'), \
         patch('monitor.core.decision_engine.NotificationService'), \
         patch('monitor.core.decision_engine.DeviceStatusManager'), \
         patch('monitor.core.decision_engine.RestartManager'), \
         patch('monitor.core.decision_engine.OSManager'), \
         patch('monitor.core.decision_engine.ServerManager'):
        
        engine = DecisionEngine(
            logs_directory=logs_dir,
            data_directory=data_dir,
            config_service=mock_config_service
        )
        
        # Mock the methods we don't want to actually execute
        engine._ensure_device_tracked = Mock()
        engine._evaluate_and_process_device = Mock()
        
        return engine


def test_device_filtering_ignores_invalid_types(decision_engine, mock_devices_db):
    """Test that devices with invalid device types are filtered out"""
    
    # Call the method under test
    decision_engine._evaluate_devices()
    
    # Get the call arguments to see which devices were processed
    processed_devices = []
    for call in decision_engine._evaluate_and_process_device.call_args_list:
        device_info = call[0][0]  # First argument is the DeviceInfo
        processed_devices.append(device_info.device_id)
    
    # Verify only valid devices were processed
    expected_processed = ["device_valid_camera", "device_valid_relay"]
    assert set(processed_devices) == set(expected_processed)
    
    # Verify invalid devices were not processed
    invalid_devices = [
        "device_none_type", 
        "device_empty_type", 
        "device_whitespace_type", 
        "device_unknown_type",
        "device_unknown_case"
    ]
    for invalid_device in invalid_devices:
        assert invalid_device not in processed_devices


def test_device_filtering_logs_ignored_devices(decision_engine, mock_devices_db, caplog):
    """Test that ignored devices are logged for debugging"""
    
    with caplog.at_level("DEBUG", logger="monitor.core.decision_engine"):
        decision_engine._evaluate_devices()
    
    # Check that debug messages were logged for ignored devices
    log_messages = [record.message for record in caplog.records]
    
    # Should log total devices found
    assert any("Found 7 total devices" in msg for msg in log_messages)
    
    # Should log filtered count
    assert any("Evaluating 2 devices with valid device types" in msg for msg in log_messages)
    
    # Should log specific ignored devices
    assert any("Ignoring device device_none_type" in msg for msg in log_messages)
    assert any("Ignoring device device_empty_type" in msg for msg in log_messages)
    assert any("Ignoring device device_unknown_type" in msg for msg in log_messages)


def test_device_filtering_handles_empty_database(decision_engine):
    """Test that filtering works correctly when database is empty"""
    
    # Mock empty database
    decision_engine.devices_db.get_all.return_value = {}
    
    # Should not raise any exceptions
    decision_engine._evaluate_devices()
    
    # No devices should be processed
    decision_engine._evaluate_and_process_device.assert_not_called()


def test_device_filtering_handles_all_invalid_devices(decision_engine):
    """Test that filtering works when all devices are invalid"""
    
    # Mock database with only invalid devices
    invalid_devices = {
        "device1": DeviceInfo("device1", None, datetime.now(), "success"),
        "device2": DeviceInfo("device2", "", datetime.now(), "success"),
        "device3": DeviceInfo("device3", "unknown", datetime.now(), "success")
    }
    decision_engine.devices_db.get_all.return_value = invalid_devices
    
    # Should not raise any exceptions
    decision_engine._evaluate_devices()
    
    # No devices should be processed
    decision_engine._evaluate_and_process_device.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])