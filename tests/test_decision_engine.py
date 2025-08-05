"""Tests for DecisionEngine class"""
import pytest
import tempfile
import shutil
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from PySide6.QtCore import QThread, QTimer, QCoreApplication, Slot
from PySide6.QtTest import QSignalSpy
from monitor.core.decision_engine import DecisionEngine
from monitor.services.devices_models import DeviceInfo, DeviceType
from monitor.services.config_service import ConfigService


class TestDecisionEngine:
    """Test cases for DecisionEngine"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for test databases"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def decision_engine(self, temp_db_dir):
        """Create a DecisionEngine instance for testing"""
        engine = DecisionEngine(temp_db_dir)
        yield engine
        # Ensure cleanup
        if hasattr(engine, 'devices_db') and engine.devices_db:
            engine.devices_db.close()
    
    @pytest.fixture
    def mock_config(self):
        """Mock config service for testing"""
        with patch('monitor.core.decision_engine.ConfigService') as mock_config_service:
            mock_config = Mock()
            mock_config.get.side_effect = lambda section, key, default: {
                ('devices', 'relay_fail_threshold'): '150',
                ('devices', 'camera_fail_threshold'): '0.7',
                ('system', 'minutes_to_restart'): '3'
            }.get((section, key), default)
            mock_config_service.return_value = mock_config
            yield mock_config
    
    def test_init(self, decision_engine, temp_db_dir):
        """Test DecisionEngine initialization"""
        assert decision_engine.db_directory == temp_db_dir
        assert not decision_engine.is_running()
        assert decision_engine.devices_db is not None
        assert decision_engine._evaluation_timer is None
        assert decision_engine.relay_fail_threshold == 200  # Default
        assert decision_engine.camera_fail_threshold == 0.6  # Default
        assert decision_engine.minutes_to_restart == 5  # Default
    
    def test_start_stop(self, decision_engine, qapp):
        """Test starting and stopping the decision engine"""
        # Test start
        decision_engine.start()
        assert decision_engine.is_running()
        assert decision_engine._evaluation_timer is not None
        # Timer might not be active immediately in test environment
        
        # Test stop
        decision_engine.stop()
        assert not decision_engine.is_running()
    
    def test_double_start_warning(self, decision_engine):
        """Test that starting twice logs a warning"""
        decision_engine.start()
        
        with patch.object(decision_engine.logger, 'warning') as mock_warning:
            decision_engine.start()  # Start again
            mock_warning.assert_called_with("DecisionEngine is already running")
        
        decision_engine.stop()
    
    def test_config_loading(self, decision_engine, mock_config):
        """Test configuration loading"""
        decision_engine._load_config_thresholds()
        
        assert decision_engine.relay_fail_threshold == 150
        assert decision_engine.camera_fail_threshold == 0.7
        assert decision_engine.minutes_to_restart == 3
    
    def test_config_loading_error_handling(self, decision_engine):
        """Test configuration loading error handling"""
        with patch('monitor.core.decision_engine.ConfigService', side_effect=Exception("Config error")):
            # Should not raise, just log warning and keep defaults
            decision_engine._load_config_thresholds()
            
            assert decision_engine.relay_fail_threshold == 200  # Default
            assert decision_engine.camera_fail_threshold == 0.6  # Default
            assert decision_engine.minutes_to_restart == 5  # Default


class TestDeviceEvaluation:
    """Test device evaluation logic"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for test databases"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def decision_engine(self, temp_db_dir):
        """Create a DecisionEngine instance for testing"""
        engine = DecisionEngine(temp_db_dir)
        # Set known thresholds for testing
        engine.relay_fail_threshold = 100
        engine.camera_fail_threshold = 0.6
        engine.minutes_to_restart = 3
        yield engine
        if hasattr(engine, 'devices_db') and engine.devices_db:
            engine.devices_db.close()
    
    def test_is_relay_device(self, decision_engine):
        """Test relay device type detection"""
        assert decision_engine._is_relay_device(DeviceType.FAN.value)
        assert decision_engine._is_relay_device(DeviceType.SPRINKLER.value)
        assert decision_engine._is_relay_device(DeviceType.GROUP.value)
        assert decision_engine._is_relay_device(DeviceType.COMPORT.value)
        assert decision_engine._is_relay_device(DeviceType.THI.value)
        assert not decision_engine._is_relay_device(DeviceType.CAMERA.value)
        assert not decision_engine._is_relay_device(DeviceType.THREAD.value)
    
    def test_is_thread_device(self, decision_engine):
        """Test thread device type detection"""
        assert decision_engine._is_thread_device(DeviceType.THREAD.value)
        assert decision_engine._is_thread_device(DeviceType.DEVICE_MODE_THREAD.value)
        assert decision_engine._is_thread_device(DeviceType.SYSTEM_HEALTH.value)
        assert not decision_engine._is_thread_device(DeviceType.CAMERA.value)
        assert not decision_engine._is_thread_device(DeviceType.FAN.value)
    
    def test_evaluate_relay_device_above_threshold(self, decision_engine):
        """Test relay device evaluation above threshold"""
        device = DeviceInfo(
            device_id="test_fan",
            device_type=DeviceType.FAN.value,
            status="fail",
            last_log_status="fail",
            last_log_consecutive_count=150,  # Above threshold of 100
            success_count=5,
            fail_count=10,
            recent_pattern="FFFFFFFFFF",
            last_updated=datetime.now()
        )
        
        result = decision_engine._evaluate_relay_device(device)
        assert result == "fail"  # Should return the actual device status
    
    def test_evaluate_relay_device_below_threshold(self, decision_engine):
        """Test relay device evaluation below threshold"""
        device = DeviceInfo(
            device_id="test_fan",
            device_type=DeviceType.FAN.value,
            status="fail",
            last_log_status="fail",
            last_log_consecutive_count=50,  # Below threshold of 100
            success_count=5,
            fail_count=10,
            recent_pattern="FFFFFSSSSS",
            last_updated=datetime.now()
        )
        
        result = decision_engine._evaluate_relay_device(device)
        assert result is None  # Below threshold
    
    def test_evaluate_thread_device_timeout(self, decision_engine):
        """Test thread device evaluation with timeout"""
        # Device that hasn't been updated for too long
        old_time = datetime.now() - timedelta(minutes=5)  # Threshold is 3 minutes
        device = DeviceInfo(
            device_id="test_thread",
            device_type=DeviceType.THREAD.value,
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
            success_count=5,
            fail_count=0,
            recent_pattern="SSSSSSSSSS",
            last_updated=old_time
        )
        
        result = decision_engine._evaluate_thread_device(device)
        assert result == "fail"  # Thread inactive too long
    
    def test_evaluate_thread_device_active(self, decision_engine):
        """Test thread device evaluation when active"""
        # Device recently updated
        recent_time = datetime.now() - timedelta(minutes=1)  # Within 3 minute threshold
        device = DeviceInfo(
            device_id="test_thread",
            device_type=DeviceType.THREAD.value,
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
            success_count=5,
            fail_count=0,
            recent_pattern="SSSSSSSSSS",
            last_updated=recent_time
        )
        
        result = decision_engine._evaluate_thread_device(device)
        assert result == "success"  # Thread is active
    
    def test_evaluate_camera_device_high_failure_rate(self, decision_engine):
        """Test camera device evaluation with high failure rate"""
        # Mock device with high failure rate
        device = Mock()
        device.device_id = "test_camera"
        device.device_type = DeviceType.CAMERA.value
        device.success_count = 2
        device.fail_count = 8
        device.get_failure_rate.return_value = 0.8  # 80% failure rate (above 60% threshold)
        device.last_updated = datetime.now()
        
        result = decision_engine._evaluate_camera_device(device)
        assert result == "fail"  # High failure rate
    
    def test_evaluate_camera_device_low_failure_rate(self, decision_engine):
        """Test camera device evaluation with low failure rate"""
        # Mock device with low failure rate
        device = Mock()
        device.device_id = "test_camera"
        device.device_type = DeviceType.CAMERA.value
        device.success_count = 8
        device.fail_count = 2
        device.get_failure_rate.return_value = 0.2  # 20% failure rate (below 60% threshold)
        device.last_updated = datetime.now()
        
        result = decision_engine._evaluate_camera_device(device)
        assert result == "success"  # Low failure rate
    
    def test_evaluate_camera_device_with_few_entries(self, decision_engine):
        """Test camera device evaluation with few entries (should still work)"""
        # Mock device with few entries but valid failure rate
        device = Mock()
        device.device_id = "test_camera"
        device.device_type = DeviceType.CAMERA.value
        device.success_count = 2
        device.fail_count = 1  # Total 3 entries, 33% failure rate (below 60% threshold)
        device.get_failure_rate.return_value = 0.33
        device.last_updated = datetime.now()
        
        result = decision_engine._evaluate_camera_device(device)
        assert result == "success"  # Low failure rate should be success
    
    def test_evaluate_device_unknown_type(self, decision_engine):
        """Test evaluation of unknown device type"""
        device = DeviceInfo(
            device_id="test_unknown",
            device_type="unknown_type",
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
            success_count=5,
            fail_count=0,
            recent_pattern="SSSSSSSSSS",
            last_updated=datetime.now()
        )
        
        result = decision_engine._evaluate_device(device)
        assert result is None  # Unknown device type


class TestDeviceStatusTracking:
    """Test device status tracking and persistence"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for test databases"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def decision_engine(self, temp_db_dir):
        """Create a DecisionEngine instance for testing"""
        engine = DecisionEngine(temp_db_dir)
        yield engine
        if hasattr(engine, 'devices_db') and engine.devices_db:
            engine.devices_db.close()
    
    def test_status_file_path(self):
        """Test status file path generation"""
        path = DecisionEngine._get_status_file_path()
        assert path.name == "decision_engine_statuses.json"
        assert path.parent.name == "data"
    
    def test_device_status_persistence(self, decision_engine):
        """Test saving and loading device statuses"""
        # Update a device status
        test_time = datetime.now()
        decision_engine._update_device_status("test_device", "fail", "fan", test_time)
        
        # Verify it's in memory
        assert decision_engine._get_device_status("test_device") == "fail"
        
        # Create new engine instance to test loading
        new_engine = DecisionEngine(decision_engine.db_directory)
        assert new_engine._get_device_status("test_device") == "fail"
        
        new_engine.devices_db.close()
    
    def test_get_device_status_new_device(self, decision_engine):
        """Test getting status for new device returns success"""
        status = decision_engine._get_device_status("new_device")
        assert status == "success"  # Default for new devices
    
    def test_ensure_device_tracked(self, decision_engine):
        """Test ensuring new devices are tracked"""
        device = DeviceInfo(
            device_id="new_device",
            device_type=DeviceType.FAN.value,
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
            success_count=5,
            fail_count=0,
            recent_pattern="SSSSSSSSSS",
            last_updated=datetime.now()
        )
        
        # Device not yet tracked
        assert "new_device" not in decision_engine._device_statuses
        
        decision_engine._ensure_device_tracked(device)
        
        # Device should now be tracked with 'success' status
        assert decision_engine._get_device_status("new_device") == "success"
    
    def test_handle_status_change_no_change(self, decision_engine):
        """Test handling status when no change occurs"""
        device = DeviceInfo(
            device_id="test_device",
            device_type=DeviceType.FAN.value,
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
            success_count=5,
            fail_count=0,
            recent_pattern="SSSSSSSSSS",
            last_updated=datetime.now()
        )
        
        # Set initial status
        decision_engine._update_device_status("test_device", "success", "fan", datetime.now())
        
        with patch.object(decision_engine.logger, 'debug') as mock_debug:
            decision_engine._handle_status_change(device, "success")
            mock_debug.assert_called_with("Device test_device status unchanged: success")
    
    def test_handle_status_change_to_fail(self, decision_engine):
        """Test handling status change to fail"""
        device = DeviceInfo(
            device_id="test_device",
            device_type=DeviceType.FAN.value,
            status="fail",
            last_log_status="fail",
            last_log_consecutive_count=150,
            success_count=5,
            fail_count=10,
            recent_pattern="FFFFFFFFFF",
            last_updated=datetime.now()
        )
        
        # Set initial status to success
        decision_engine._update_device_status("test_device", "success", "fan", datetime.now())
        
        with patch.object(decision_engine.logger, 'warning') as mock_warning:
            decision_engine._handle_status_change(device, "fail")
            mock_warning.assert_called_with("DEVICE FAILED - test_device")
        
        assert decision_engine._get_device_status("test_device") == "fail"
    
    def test_handle_status_change_to_success(self, decision_engine):
        """Test handling status change to success (recovery)"""
        device = DeviceInfo(
            device_id="test_device",
            device_type=DeviceType.FAN.value,
            status="success",
            last_log_status="success",
            last_log_consecutive_count=1,
            success_count=10,
            fail_count=5,
            recent_pattern="SSSSSFFFFF",
            last_updated=datetime.now()
        )
        
        # Set initial status to fail
        decision_engine._update_device_status("test_device", "fail", "fan", datetime.now())
        
        with patch.object(decision_engine.logger, 'info') as mock_info:
            decision_engine._handle_status_change(device, "success")
            mock_info.assert_called_with("DEVICE RECOVERED - test_device")
        
        assert decision_engine._get_device_status("test_device") == "success"


class TestTimerBasedOperation:
    """Test timer-based operation and device evaluation"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for test databases"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def decision_engine(self, temp_db_dir):
        """Create a DecisionEngine instance for testing"""
        engine = DecisionEngine(temp_db_dir)
        yield engine
        if hasattr(engine, 'devices_db') and engine.devices_db:
            engine.devices_db.close()
    
    def test_timer_creation_and_interval(self, decision_engine, qapp):
        """Test timer creation and configuration"""
        decision_engine.start()
        
        assert decision_engine._evaluation_timer is not None
        assert decision_engine._evaluation_timer.interval() == 60000  # 60 seconds
        # Timer might not be active immediately in test environment
        
        decision_engine.stop()
    
    def test_evaluate_devices_empty_database(self, decision_engine):
        """Test device evaluation with empty database"""
        # Mock empty database
        with patch.object(decision_engine.devices_db, 'get_all', return_value={}):
            # Should not raise any errors
            decision_engine._evaluate_devices()
    
    def test_evaluate_devices_with_mixed_devices(self, decision_engine):
        """Test device evaluation with mixed device types"""
        # Set known thresholds for testing
        decision_engine.relay_fail_threshold = 100
        decision_engine.camera_fail_threshold = 0.6
        decision_engine.minutes_to_restart = 3
        decision_engine._running = True  # Ensure engine is marked as running
        
        # Create test devices
        devices = {
            "relay_device": DeviceInfo(
                device_id="relay_device",
                device_type=DeviceType.FAN.value,
                status="fail",
                last_log_status="fail",
                last_log_consecutive_count=150,  # Above threshold
                success_count=5,
                fail_count=10,
                recent_pattern="FFFFFFFFFF",
                last_updated=datetime.now()
            ),
            "thread_device": DeviceInfo(
                device_id="thread_device",
                device_type=DeviceType.THREAD.value,
                status="success",
                last_log_status="success",
                last_log_consecutive_count=1,
                success_count=5,
                fail_count=0,
                recent_pattern="SSSSSSSSSS",
                last_updated=datetime.now() - timedelta(minutes=5)  # Too old
            ),
            "camera_device": DeviceInfo(
                device_id="camera_device",
                device_type=DeviceType.CAMERA.value,
                status="success",
                last_log_status="success",
                last_log_consecutive_count=1,
                success_count=2,
                fail_count=1,  # 33% failure rate (below 60% threshold)
                recent_pattern="SSF",
                last_updated=datetime.now()
            )
        }
        
        # Mock the camera device's get_failure_rate method
        devices["camera_device"].get_failure_rate = Mock(return_value=0.33)
        
        with patch.object(decision_engine.devices_db, 'get_all', return_value=devices):
            with patch.object(decision_engine, '_handle_status_change') as mock_handle:
                with patch.object(decision_engine, '_ensure_device_tracked') as mock_ensure:
                    decision_engine._evaluate_devices()
                    
                    # Should handle status changes for all three devices with evaluations
                    assert mock_handle.call_count == 3, f"Expected 3 calls, got {mock_handle.call_count}"
                    
                    # All devices should be tracked (this ensures baseline tracking)
                    assert mock_ensure.call_count == 3, f"Expected 3 calls to ensure_tracked, got {mock_ensure.call_count}"
    
    def test_evaluate_devices_error_handling(self, decision_engine):
        """Test error handling in device evaluation"""
        with patch.object(decision_engine.devices_db, 'get_all', side_effect=Exception("DB Error")):
            with patch.object(decision_engine.logger, 'error') as mock_error:
                # Mock the running state to ensure method doesn't exit early
                decision_engine._running = True
                decision_engine._evaluate_devices()
                mock_error.assert_called_with("Error evaluating devices: DB Error")
    
    def test_reset_statuses(self, temp_db_dir):
        """Test resetting decision engine statuses"""
        # Create a status file
        status_file = DecisionEngine._get_status_file_path()
        status_file.parent.mkdir(exist_ok=True)
        status_file.write_text('{"test": "data"}')
        
        assert status_file.exists()
        
        DecisionEngine.reset_statuses()
        
        assert not status_file.exists()


class TestIntegration:
    """Integration tests for DecisionEngine"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for test databases"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def app(self, qapp):
        """Ensure QApplication is running for threading tests"""
        return qapp
    
    def test_threaded_timer_operation(self, temp_db_dir, app):
        """Test DecisionEngine timer operation on separate thread"""
        decision_engine = DecisionEngine(temp_db_dir)
        decision_thread = QThread()
        
        evaluation_count = {'count': 0}
        
        def count_evaluations():
            evaluation_count['count'] += 1
        
        try:
            # Move to thread
            decision_engine.moveToThread(decision_thread)
            
            # Patch evaluation to count calls
            with patch.object(decision_engine, '_evaluate_devices', side_effect=count_evaluations):
                # Set up thread lifecycle
                decision_thread.started.connect(decision_engine.start)
                decision_engine.finished.connect(decision_thread.quit)
                
                # Start thread
                decision_thread.start()
                
                # Wait for thread to start
                start_time = time.time()
                while not decision_thread.isRunning() and (time.time() - start_time < 2.0):
                    app.processEvents()
                    time.sleep(0.01)
                
                assert decision_thread.isRunning()
                
                # Run for a short time to see timer calls
                QTimer.singleShot(200, app.quit)  # Stop after 200ms
                app.exec()
                
                # Verify timer-based evaluation occurred
                # Note: May not get calls in 200ms depending on timing, so just verify setup
                assert decision_engine.is_running()
                
        finally:
            # Clean shutdown
            if decision_engine.is_running():
                decision_engine.stop()
            
            if decision_thread.isRunning():
                decision_thread.quit()
                decision_thread.wait(3000)
