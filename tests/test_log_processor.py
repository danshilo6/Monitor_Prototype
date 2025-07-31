"""Tests for LogProcessor functionality"""

import unittest
import tempfile
import sqlite3
import subprocess
import time
import os
from pathlib import Path
from unittest.mock import Mock, patch
from monitor.core.log_processor import LogProcessor


class TestLogProcessor(unittest.TestCase):
    """Test cases for LogProcessor"""

    def setUp(self):
        """Set up test environment with temporary directory"""
        # Create temporary directory for test databases
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_initialization_with_default_values(self):
        """
        Test that LogProcessor initializes correctly with default values.
        
        This test verifies:
        - The processor accepts a database directory
        - Default polling interval and batch size are used when not specified
        - All required components are initialized (log_reader, device_status_db)
        - The processor starts in a stopped state (running=False)
        """
        # Mock the dependencies so we don't need real databases
        with patch('monitor.core.log_processor.LogReader') as mock_log_reader, \
             patch('monitor.core.log_processor.DeviceStatusDatabase') as mock_device_db, \
             patch('monitor.core.log_processor.get_logger') as mock_logger:
            
            # Create the processor
            processor = LogProcessor(self.test_path)
            
            # Verify initialization
            self.assertEqual(processor.db_directory, self.test_path)
            self.assertEqual(processor.polling_interval, LogProcessor.DEFAULT_POLLING_INTERVAL)
            self.assertEqual(processor.batch_size, LogProcessor.DEFAULT_LOG_BATCH_SIZE)
            self.assertFalse(processor.running)
            
            # Verify components were created
            mock_log_reader.assert_called_once_with(self.test_path)
            mock_device_db.assert_called_once()
            
            # Verify known_devices set is initialized empty
            self.assertEqual(len(processor.known_devices), 0)
            self.assertIsInstance(processor.known_devices, set)

    def test_initialization_with_custom_values(self):
        """
        Test that LogProcessor accepts and uses custom polling interval and batch size.
        
        This test verifies:
        - Custom polling_interval is properly stored
        - Custom batch_size is properly stored  
        - The processor can be configured differently from defaults
        """
        custom_interval = 5.0
        custom_batch_size = 50
        
        # Mock the dependencies
        with patch('monitor.core.log_processor.LogReader') as mock_log_reader, \
             patch('monitor.core.log_processor.DeviceStatusDatabase') as mock_device_db, \
             patch('monitor.core.log_processor.get_logger') as mock_logger:
            
            # Create processor with custom values
            processor = LogProcessor(
                self.test_path, 
                polling_interval=custom_interval,
                batch_size=custom_batch_size
            )
            
            # Verify custom values are used
            self.assertEqual(processor.polling_interval, custom_interval)
            self.assertEqual(processor.batch_size, custom_batch_size)
            self.assertEqual(processor.db_directory, self.test_path)

    def test_calculate_status_updates_new_device(self):
        """
        Test status calculation for a device we've never seen before.
        
        This test verifies:
        - New devices are detected and added to known_devices
        - First-time device status gets consecutive count of 1
        - The update dictionary is populated correctly
        """
        # Mock the dependencies
        with patch('monitor.core.log_processor.LogReader'), \
             patch('monitor.core.log_processor.DeviceStatusDatabase'), \
             patch('monitor.core.log_processor.get_logger'):
            
            processor = LogProcessor(self.test_path)
            
            # Create fake log data - pandas DataFrame format
            import pandas as pd
            new_logs = pd.DataFrame([
                {'device': 'device1', 'status': 'success', 'timestamp': '2025-07-30 10:00:00'}
            ])
            
            # Empty current statuses (no devices in database yet)
            current_statuses = {}
            
            # Call the method we're testing
            updates = processor._calculate_status_updates(new_logs, current_statuses)
            
            # Verify the results
            self.assertEqual(len(updates), 1)
            self.assertIn('device1', updates)
            
            # Check the status and count for new device
            device_row = updates['device1']
            self.assertEqual(device_row.current_status, 'success')
            self.assertEqual(device_row.last_log_status, 'success')
            self.assertEqual(device_row.count, 1)  # First occurrence
            
            # Verify device was added to known devices
            self.assertIn('device1', processor.known_devices)

    def test_calculate_status_updates_same_status_increment(self):
        """
        Test status calculation when existing device reports the same status.
        
        This test verifies:
        - Existing device with same status gets incremented consecutive count
        - Device stays in known_devices (no duplicate addition)
        - Current status and count from database are used correctly
        """
        # Mock the dependencies
        with patch('monitor.core.log_processor.LogReader'), \
             patch('monitor.core.log_processor.DeviceStatusDatabase'), \
             patch('monitor.core.log_processor.get_logger'):
            
            processor = LogProcessor(self.test_path)
            
            # Pre-populate known_devices (device already exists)
            processor.known_devices.add('device1')
            
            # Create fake log data - same device reporting same status
            import pandas as pd
            new_logs = pd.DataFrame([
                {'device': 'device1', 'status': 'success', 'timestamp': '2025-07-30 10:00:00'}
            ])
            
            # Simulate existing device status in database using DeviceStatusInfo
            from monitor.services.device_status_models import DeviceStatusInfo
            from datetime import datetime
            current_statuses = {
                'device1': DeviceStatusInfo(
                    device_id='device1',
                    current_status='success',
                    last_log_status='success',
                    count=5,
                    last_updated=datetime.fromisoformat('2025-07-30 09:59:00')
                )
            }
            
            # Call the method we're testing
            updates = processor._calculate_status_updates(new_logs, current_statuses)
            
            # Verify the results
            self.assertEqual(len(updates), 1)
            self.assertIn('device1', updates)
            
            # Check that consecutive count was incremented (5 + 1 = 6)
            device_row = updates['device1']
            self.assertEqual(device_row.current_status, 'success')
            self.assertEqual(device_row.last_log_status, 'success')
            self.assertEqual(device_row.count, 6)  # Previous count (5) + 1
            
            # Verify device is still in known devices (no change)
            self.assertIn('device1', processor.known_devices)

    def test_calculate_status_updates_status_change_reset(self):
        """
        Test status calculation when existing device reports a different status.
        
        This test verifies:
        - Device status change resets consecutive count to 1
        - New status is properly recorded
        - Device remains in known_devices
        - The reset logic works correctly regardless of previous count
        """
        # Mock the dependencies
        with patch('monitor.core.log_processor.LogReader'), \
             patch('monitor.core.log_processor.DeviceStatusDatabase'), \
             patch('monitor.core.log_processor.get_logger'):
            
            processor = LogProcessor(self.test_path)
            
            # Pre-populate known_devices (device already exists)
            processor.known_devices.add('device1')
            
            # Create fake log data - same device reporting DIFFERENT status
            import pandas as pd
            new_logs = pd.DataFrame([
                {'device': 'device1', 'status': 'fail', 'timestamp': '2025-07-30 10:00:00'}
            ])
            
            # Simulate existing device status in database using DeviceStatusInfo (was 'success' with high count)
            from monitor.services.device_status_models import DeviceStatusInfo
            from datetime import datetime
            current_statuses = {
                'device1': DeviceStatusInfo(
                    device_id='device1',
                    current_status='success',
                    last_log_status='success',
                    count=15,  # High count to test reset
                    last_updated=datetime.fromisoformat('2025-07-30 09:59:00')
                )
            }
            
            # Call the method we're testing
            updates = processor._calculate_status_updates(new_logs, current_statuses)
            
            # Verify the results
            self.assertEqual(len(updates), 1)
            self.assertIn('device1', updates)
            
            # Check that status changed and count was reset to 1
            device_row = updates['device1']
            # Since threshold is not reached, it should keep the existing status 'success'
            self.assertEqual(device_row.current_status, 'success')  # Keeps existing status below threshold
            self.assertEqual(device_row.last_log_status, 'fail')  # But tracks the new log status
            self.assertEqual(device_row.count, 1)  # Reset to 1 because log status changed
            
            # Verify device is still in known devices (no change)
            self.assertIn('device1', processor.known_devices)

    def test_calculate_status_updates_multiple_devices_mixed_scenarios(self):
        """
        Test status calculation with multiple devices in a single batch (realistic scenario).
        
        This test verifies:
        - Multiple devices can be processed in one batch
        - Each device is handled according to its individual situation
        - Mix of new devices, status increments, and status changes work together
        - All devices are properly tracked in known_devices
        """
        # Mock the dependencies
        with patch('monitor.core.log_processor.LogReader'), \
             patch('monitor.core.log_processor.DeviceStatusDatabase'), \
             patch('monitor.core.log_processor.get_logger'):
            
            processor = LogProcessor(self.test_path)
            
            # Pre-populate some known devices
            processor.known_devices.add('device2')  # device2 already known
            processor.known_devices.add('device3')  # device3 already known
            
            # Create fake log data - multiple devices with different scenarios
            import pandas as pd
            new_logs = pd.DataFrame([
                {'device': 'device1', 'status': 'success', 'timestamp': '2025-07-30 10:00:00'},    # New device
                {'device': 'device2', 'status': 'success', 'timestamp': '2025-07-30 10:00:01'},    # Same status (increment)
                {'device': 'device3', 'status': 'fail', 'timestamp': '2025-07-30 10:00:02'},     # Status change (reset)
                {'device': 'device4', 'status': 'fail', 'timestamp': '2025-07-30 10:00:03'}   # Another new device
            ])
            
            # Simulate existing device statuses in database using DeviceStatusInfo
            from monitor.services.device_status_models import DeviceStatusInfo
            from datetime import datetime
            current_statuses = {
                'device2': DeviceStatusInfo(
                    device_id='device2',
                    current_status='success',
                    last_log_status='success',
                    count=3,
                    last_updated=datetime.fromisoformat('2025-07-30 09:59:00')
                ),
                'device3': DeviceStatusInfo(
                    device_id='device3',
                    current_status='success',
                    last_log_status='success',
                    count=8,
                    last_updated=datetime.fromisoformat('2025-07-30 09:58:00')
                )
                # device1 and device4 are new (not in database)
            }
            
            # Call the method we're testing
            updates = processor._calculate_status_updates(new_logs, current_statuses)
            
            # Verify all 4 devices were processed
            self.assertEqual(len(updates), 4)
            
            # Check device1 (new device)
            device_row = updates['device1']
            self.assertEqual(device_row.current_status, 'success')
            self.assertEqual(device_row.last_log_status, 'success')
            self.assertEqual(device_row.count, 1)
            
            # Check device2 (same status increment)
            device_row = updates['device2']
            self.assertEqual(device_row.current_status, 'success')
            self.assertEqual(device_row.last_log_status, 'success')
            self.assertEqual(device_row.count, 4)  # 3 + 1
            
            # Check device3 (status change reset)
            device_row = updates['device3']
            self.assertEqual(device_row.current_status, 'success')  # Keeps existing status below threshold
            self.assertEqual(device_row.last_log_status, 'fail')  # But tracks the new log status
            self.assertEqual(device_row.count, 1)  # Reset to 1 because log status changed
            
            # Check device4 (another new device)
            device_row = updates['device4']
            self.assertEqual(device_row.current_status, 'fail')
            self.assertEqual(device_row.last_log_status, 'fail')
            self.assertEqual(device_row.count, 1)
            
            # Verify all devices are now in known_devices
            self.assertIn('device1', processor.known_devices)
            self.assertIn('device2', processor.known_devices)
            self.assertIn('device3', processor.known_devices)
            self.assertIn('device4', processor.known_devices)
            self.assertEqual(len(processor.known_devices), 4)

    def test_integration_with_log_simulator(self):
        """
        Integration test: LogProcessor reading from log simulator and writing to device database.
        
        This test verifies the complete pipeline:
        - Log simulator generates real log entries in a database
        - LogProcessor reads those logs using LogReader
        - LogProcessor processes the logs and updates device status database
        - Device statuses are correctly stored and can be retrieved
        
        This is a realistic end-to-end test of the entire system.
        """
        # Skip this test if we can't find the log simulator
        simulator_path = Path("scripts/log_simulator.py")
        if not simulator_path.exists():
            self.skipTest("Log simulator not found at scripts/log_simulator.py")
        
        # Create a separate temporary directory for this integration test
        import tempfile
        import shutil
        test_dir = tempfile.mkdtemp(prefix="log_processor_integration_")
        test_path = Path(test_dir)
        
        try:
            # Step 1: Run log simulator synchronously to generate test data
            print(f"Running log simulator in {test_path}")
            result = subprocess.run([
                "python", str(simulator_path),
                "--db-dir", str(test_path),
                "--duration", "2",  # Run for 2 seconds
                "--interval", "0.5",  # Generate logs every 0.5 seconds
                "--logs-per-cycle", "10",  # Process 10 logs per cycle
                "--test-mode",  # Use test mode
                "--reset-db"  # Start fresh
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                self.fail(f"Log simulator failed: {result.stderr}")
            
            print("Log simulator completed successfully")
            print(f"Simulator output: {result.stdout[:200]}...")  # Show first 200 chars
            
            # Step 2: Check that a database file was created
            db_files = list(test_path.glob("logs_*.db"))
            self.assertGreater(len(db_files), 0, "No database files created by simulator")
            print(f"Found database files: {[f.name for f in db_files]}")
            
            # Step 3: Create LogProcessor (no mocking - use real components)
            # Use temporary database path to avoid polluting production data
            temp_device_db_path = str(test_path / "test_device_status.db")
            processor = LogProcessor(
                db_directory=test_path,
                polling_interval=0.1,  # Check frequently
                batch_size=50,
                device_status_db_path=temp_device_db_path
            )
            
            # Step 4: Process a few batches to read the generated logs
            processor.running = True
            for i in range(5):  # Process 5 batches
                print(f"Processing batch {i+1}")
                processor._process_log_batch()
                time.sleep(0.1)
                
                # Check intermediate results
                if i == 2:  # After 3rd batch
                    intermediate_summary = processor.get_status_summary()
                    print(f"Intermediate status summary: {intermediate_summary}")
            
            # Get final status before stopping (while database is still open)
            final_status_summary = processor.get_status_summary()
            final_all_statuses = processor.device_status_db.get_all_device_statuses()
            
            processor.stop()
            
            # Step 5: Verify that devices were detected and processed
            print(f"Known devices after processing: {processor.known_devices}")
            self.assertGreater(len(processor.known_devices), 0, 
                             "Should have detected at least one device from simulator")
            
            # Step 6: Verify device status database was updated (using data from before stop)
            print(f"Final status summary: {final_status_summary}")
            self.assertGreater(final_status_summary['total_devices'], 0,
                             "Should have at least one device in status database")
            
            # Step 7: Verify we can read device statuses (using data from before stop)
            self.assertGreater(len(final_all_statuses), 0,
                             "Should have device statuses in database")
            
            # Step 8: Verify status data format and content
            for device_id, device_row in final_all_statuses.items():
                self.assertIsInstance(device_id, str, "Device ID should be string")
                self.assertIsInstance(device_row.current_status, str, "Status should be string")
                self.assertIsInstance(device_row.count, int, "Count should be integer")
                self.assertGreater(device_row.count, 0, "Count should be positive")
                self.assertIsNotNone(device_row.last_updated, "Last updated should not be None")
            
            print(f"Integration test successful:")
            print(f"  - Detected {len(processor.known_devices)} devices")
            print(f"  - Status summary: {final_status_summary}")
            print(f"  - Sample devices: {list(final_all_statuses.keys())[:3]}")
            
        except subprocess.TimeoutExpired:
            self.fail("Log simulator process timed out")
        except Exception as e:
            self.fail(f"Integration test failed: {e}")
        finally:
            # Clean up temporary directory
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
