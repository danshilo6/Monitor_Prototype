"""
Log Processor

Simple log processor that reads new log entries and processes them synchronously.

Main functionality:
- Reads new log entries from the logs database
- Updates device status tracking in the database  
- Designed to be controlled by DecisionEngine (no internal timer)
- Pure Python class with no Qt dependencies
- Minimal processing - focuses on data reading and device updates
"""

import time
import re
from pathlib import Path
from typing import Optional
import pandas as pd
from datetime import datetime
from dataclasses import replace
from monitor.core.log_reader import LogReader
from monitor.log_setup import get_logger
from monitor.services.devices_models import DeviceType, DeviceInfo
from monitor.services.devices_db import DevicesDatabase


class LogProcessor:
    """
    Device status processor that reads logs and maintains device state tracking.
    
    Pure Python class - no Qt dependencies.
    Designed to be called synchronously by DecisionEngine.
    """
    
    def __init__(self, 
                 logs_directory: Path,
                 data_directory: Path,
                 devices_db: Optional['DevicesDatabase'] = None):
        """
        Initialize the log processor.
        
        Args:
            logs_directory: Directory containing the log database files
            data_directory: Directory containing the devices database
            devices_db: Optional shared DevicesDatabase instance. If None, creates own instance.
        """
        self.logger = get_logger("monitor.core.log_processor")
        
        # Configuration
        self.logs_directory = logs_directory
        self.data_directory = data_directory
        
        # State
        self._running = False
        
        # Log reader - handles its own state persistence
        self.log_reader = LogReader(logs_directory)
        
        # Devices database - use shared instance if provided, otherwise create own
        if devices_db is not None:
            self.devices_db = devices_db
            self.logger.debug("Using shared DevicesDatabase instance")
        else:
            self.devices_db = DevicesDatabase(data_directory / "devices.db")
            self.logger.debug("Created new DevicesDatabase instance")
        
        # Expected system threads that should always be monitored
        self._expected_threads = [
            {'id': 'thread', 'type': DeviceType.THREAD}
        ]
        
        self.logger.info("LogProcessor initialized")
    
    def start(self) -> None:
        """Start the log processor (no timer - controlled by DecisionEngine)."""
        if self._running:
            self.logger.warning("LogProcessor is already running")
            return
        
        self._running = True
        
        self.logger.info("LogProcessor started")
    
    def stop(self) -> None:
        """Stop the log processor."""
        if not self._running:
            return
        
        self.logger.info("Stopping LogProcessor...")
        self._running = False
        
        self.log_reader.close()
        self.devices_db.close()
        self.logger.info("LogProcessor stopped")
    
    def is_running(self) -> bool:
        """Check if the processor is currently running."""
        return self._running
    
    def _ensure_expected_threads_exist(self) -> None:
        """Add expected system threads to database if missing (one-time setup)."""

        
        current_time = datetime.now()
        devices_in_memory = self.devices_db.get_all()
        
        for thread_config in self._expected_threads:
            thread_id = thread_config['id']
            thread_type = thread_config['type']
            
            if thread_id not in devices_in_memory:
                # Create missing thread device with baseline status
                thread_device = DeviceInfo(
                    device_id=thread_id,
                    device_type=thread_type.value,
                    status='success',  # Initial status
                    last_updated=current_time,
                    last_log_status='success',
                    last_log_consecutive_count=1,
                    success_count=1,
                    fail_count=0
                )
                
                self.logger.info(f"Adding expected thread to database: {thread_id} ({thread_type.value})")
                self.devices_db.update_device(thread_device)
    
    def _determine_device_type(self, device_name: str) -> DeviceType:
        """
        DEPRECATED: Determine device type based on device name patterns.
        
        This method is no longer used as device types are now provided
        directly in the log entries via the 'device_type' column.
        
        Args:
            device_name: The device identifier/name
            
        Returns:
            DeviceType enum value
        """
        if not device_name:
            return DeviceType.UNKNOWN
        
        device_name = device_name.strip()
        
        # Camera: IP address pattern (num.num.num.num)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, device_name):
            return DeviceType.CAMERA
        
        # Thread: specific thread names
        thread_names = ["thread"]
        if device_name.lower() in thread_names:
            return DeviceType.THREAD
        
        # Comport: exact match
        if device_name.lower() == "comport":
            return DeviceType.COMPORT
        
        # THI: exact match
        if device_name.upper() == "THI":
            return DeviceType.THI
        
        # Group: string + number + " - " + multiple numbers separated by spaces ending with "G"
        # Example: AZ4 - 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68G
        group_pattern = r'^[A-Za-z]+\d+\s*-\s*(\d+\s+)*\d+G$'
        if re.match(group_pattern, device_name):
            return DeviceType.GROUP
        
        # Fan: string + number + " - " + multiple numbers separated by spaces (no trailing G)
        # Example: AR1 - 65 66 67 68
        fan_pattern = r'^[A-Za-z]+\d+\s*-\s*(\d+\s+){2,}\d+$'
        if re.match(fan_pattern, device_name):
            return DeviceType.FAN
        
        # Sprinkler: string + number + " - " + single number
        # Example: B4 - 8
        sprinkler_pattern = r'^[A-Za-z]+\d+\s*-\s*\d+$'
        if re.match(sprinkler_pattern, device_name):
            return DeviceType.SPRINKLER
        
        # Default to unknown if no pattern matches
        return DeviceType.UNKNOWN
    
    def _create_new_device(self, device_id: str, device_type: str, log_status: str, last_updated: datetime) -> DeviceInfo:
        """
        Create a new device with initial status.
        
        Args:
            device_id: The device identifier
            device_type: The device type from the log entry
            log_status: The initial status from the first log entry
            last_updated: Timestamp from the log entry
            
        Returns:
            New DeviceInfo instance
        """
        device_info = DeviceInfo(
            device_id=device_id,
            device_type=device_type,
            status=log_status,  # Initial status from first log
            last_log_status=log_status,
            last_log_consecutive_count=1,
            success_count=1 if log_status == 'success' else 0,
            fail_count=1 if log_status == 'fail' else 0,
            recent_pattern='S' if log_status == 'success' else 'F',
            last_updated=last_updated
        )
        
        self.logger.debug(f"Created new device: {device_id} (type: {device_type}, initial status: {log_status})")
        return device_info
    
    def _update_existing_device(self, device: DeviceInfo, log_status: str, last_updated: datetime, max_history: int = 50) -> DeviceInfo:
        """
        Update an existing device with a new log status.
        
        Args:
            device: The existing DeviceInfo to update
            log_status: The new status from the log entry
            last_updated: Timestamp from the log entry
            max_history: Maximum history length to maintain
            
        Returns:
            Updated DeviceInfo instance
        """
        # Update the device with the new log status (adds to history and updates counts)
        updated_device = device.add_status_to_history(log_status, max_history)
        
        # Update consecutive count logic
        if log_status == device.last_log_status:
            # Same status as before: increment count
            updated_device = replace(
                updated_device,
                last_log_consecutive_count=device.last_log_consecutive_count + 1
            )
        else:
            # Different status: reset count to 1
            updated_device = replace(
                updated_device,
                last_log_consecutive_count=1
            )
        
        # Update the main status field to match the latest log status
        updated_device = replace(
            updated_device,
            status=log_status,
            last_updated=last_updated
        )
        return updated_device
    
    def _get_logged_devices(self, new_logs: pd.DataFrame) -> list[str]:
        """
        Get the unique device IDs that have new log entries.
        
        Args:
            new_logs: DataFrame containing the new log entries
            
        Returns:
            Sorted list of unique device IDs that have new logs
        """
        unique_devices = new_logs['device'].dropna().unique()
        return sorted(unique_devices)
    
    def process_batch(self) -> int:
        """Process one batch of logs and return count (called by DecisionEngine)."""
        # Check if processor is still running before processing
        if not self._running:
            return 0
            
        try:
            # Step 1: Read all new logs (no limit)
            new_logs = self.log_reader.read_next()
            
            if new_logs.empty:
                # No new logs found - debug log this
                self.logger.debug("No new log entries found in this batch")
                print("No new logs")
                return 0
            
            print(f"Found {len(new_logs)} new logs")
            self.logger.debug(f"Found {len(new_logs)} new log entries to process")
            
            # Step 2: Load current devices from database into memory
            devices_in_memory = self.devices_db.get_all()
            self.logger.debug(f"Loaded {len(devices_in_memory)} devices from database")
            
            # Step 3: Process logs line by line and update in-memory devices
            processed_count = 0
            for _, log_entry in new_logs.iterrows():
                device_id = log_entry.get('device', '')
                device_type = log_entry.get('device_type', 'unknown')  # Get device_type from log entry
                log_status = log_entry.get('status', '')
                # Parse timestamp from log entry, fallback to now if missing
                log_timestamp = log_entry.get('timestamp')
                if log_timestamp is not None:
                    try:
                        # Try parsing as string or datetime
                        if isinstance(log_timestamp, str):
                            last_updated = datetime.fromisoformat(log_timestamp)
                        else:
                            last_updated = pd.to_datetime(log_timestamp).to_pydatetime()
                    except Exception:
                        last_updated = datetime.now()
                else:
                    last_updated = datetime.now()
                
                if not device_id or not log_status:
                    self.logger.warning(f"Skipping log entry with missing device_id or status: {log_entry}")
                    continue
                
                # Get or create device info
                if device_id in devices_in_memory:
                    device_info = devices_in_memory[device_id]
                    # Update existing device
                    max_history = 50  # TODO: Get from config based on device_type
                    updated_device = self._update_existing_device(device_info, log_status, last_updated, max_history)
                else:
                    # Create new device using device_type from log entry
                    updated_device = self._create_new_device(device_id, device_type, log_status, last_updated)
                
                # Store updated device back in memory
                devices_in_memory[device_id] = updated_device
                processed_count += 1
            
            # Debug log which devices had new logs in this batch
            logged_devices = self._get_logged_devices(new_logs)
            if logged_devices:
                device_list = '\n'.join(logged_devices)
                self.logger.debug(f"Devices with new logs in this batch: {device_list}")
            
            # Step 4: Write all updated devices back to database using batch update
            device_list = list(devices_in_memory.values())
            success_count = self.devices_db.update_devices_batch(device_list)
            
            if success_count == len(device_list):
                self.logger.debug(f"Processed {processed_count} log entries, batch updated {success_count} devices in database")
            else:
                self.logger.warning(f"Processed {processed_count} log entries, but only {success_count}/{len(device_list)} devices were successfully updated")
            
            return len(new_logs)  # Return count of processed logs
                
        except Exception as e:
            error_msg = f"Error processing log batch: {e}"
            self.logger.error(error_msg)
            return 0


def main():
    """Simple main function for testing the log processor."""
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    
    def test_log_processing():
        """Test function that processes logs and prints results."""
        logs_count = processor.process_batch()
        if logs_count > 0:
            print(f"Processed {logs_count} new log entries")
        else:
            print("No new logs found in this batch")
    
    app = QApplication(sys.argv)
    
    try:
        # Use current working directory for testing
        logs_directory = Path.cwd()
        data_directory = Path.cwd()
        processor = LogProcessor(logs_directory, data_directory)
        
        print("Starting LogProcessor...")
        print("Press Ctrl+C to stop")
        
        processor.start()
        
        # Create a timer to manually call process_batch for testing
        test_timer = QTimer()
        test_timer.timeout.connect(test_log_processing)
        test_timer.setInterval(2000)  # 2 seconds
        test_timer.start()
        
        # Run the Qt event loop
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        if 'processor' in locals():
            processor.stop()
        print("LogProcessor stopped")


if __name__ == "__main__":
    main()
