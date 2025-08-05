"""
Log Processor

Simple log processor that reads new log entries and emits Qt signals to a DecisionEngine.

Main functionality:
- Reads new log entries from the logs database
- Emits Qt signals when new data is available
- Designed to be moved to a thread by the main application
- Minimal processing - focuses on data reading and signaling
"""

import time
import re
from pathlib import Path
import pandas as pd
from dataclasses import replace
from PySide6.QtCore import QObject, Signal, QTimer, Slot
from monitor.core.log_reader import LogReader
from monitor.log_setup import get_logger
from monitor.services.devices_models import DeviceType, DeviceInfo
from monitor.services.devices_db import DevicesDatabase


class LogProcessor(QObject):
    """
    Device status processor that reads logs and maintains device state tracking.
    
    This processor focuses on:
    - Reading new log entries efficiently
    - Updating device status tracking in the database
    - Designed to be moved to a thread by the application
    - Minimal processing overhead
    """
    
    # Qt Signals
    new_logs_processed = Signal(int)     # Emits when new logs are found and processed (with count)
    no_logs_found = Signal()             # Emits when no new logs are found in this batch
    error_occurred = Signal(str)         # Emits error message
    finished = Signal()                  # Emits when processor has finished cleanup (for thread cleanup)
    
    def __init__(self, 
                 logs_directory: Path,
                 data_directory: Path,
                 batch_interval: float = 2.0):
        """
        Initialize the log processor.
        
        Args:
            logs_directory: Directory containing the log database files
            data_directory: Directory containing the devices database
            batch_interval: Time in seconds between batch processing cycles
        """
        super().__init__()
        self.logger = get_logger("monitor.core.log_processor")
        
        # Configuration
        self.logs_directory = logs_directory
        self.data_directory = data_directory
        self.batch_interval = batch_interval
        
        # State
        self._running = False
        
        # Log reader - handles its own state persistence
        self.log_reader = LogReader(logs_directory)
        
        # Devices database
        self.devices_db = DevicesDatabase(data_directory / "devices.db")
        
        # Expected system threads that should always be monitored
        self._expected_threads = [
            {'id': 'thread', 'type': DeviceType.THREAD},
            {'id': 'device_mode_thread', 'type': DeviceType.DEVICE_MODE_THREAD}, 
            {'id': 'system_health', 'type': DeviceType.SYSTEM_HEALTH}
        ]
        
        # Timer for batch processing (will be created when started)
        self._batch_timer = None
        
        self.logger.info(f"LogProcessor initialized: interval={batch_interval}s")
    
    @Slot()
    def start(self) -> None:
        """Start the log processor batch processing."""
        if self._running:
            self.logger.warning("LogProcessor is already running")
            return
        
        # Create timer on the current thread (worker thread)
        if self._batch_timer is None:
            self._batch_timer = QTimer()
            self._batch_timer.timeout.connect(self._process_batch)
            self._batch_timer.setInterval(int(self.batch_interval * 1000))  # Convert to milliseconds
        
        self._running = True
        
        # Ensure expected threads exist in database (one-time setup)
        self._ensure_expected_threads_exist()
        
        self._batch_timer.start()
        self.logger.info("LogProcessor started")
    
    @Slot()
    def stop(self) -> None:
        """Stop the log processor."""
        if not self._running:
            return
        
        self.logger.info("Stopping LogProcessor...")
        self._running = False
        
        # Stop timer if it exists (must be done from the same thread that created it)
        if self._batch_timer is not None:
            self._batch_timer.stop()
            self._batch_timer.deleteLater()
            self._batch_timer = None
        
        self.log_reader.close()
        self.devices_db.close()
        self.logger.info("LogProcessor stopped")
        self.finished.emit()  # Emit finished signal for thread cleanup
    
    def is_running(self) -> bool:
        """Check if the processor is currently running."""
        return self._running
    
    def _ensure_expected_threads_exist(self) -> None:
        """Add expected system threads to database if missing (one-time setup)."""
        from datetime import datetime
        
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
        Determine device type based on device name patterns.
        
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
        thread_names = ["thread", "device_mode_thread", "system_health"]
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
    
    def _create_new_device(self, device_id: str, log_status: str) -> DeviceInfo:
        """
        Create a new device with initial status.
        
        Args:
            device_id: The device identifier
            log_status: The initial status from the first log entry
            
        Returns:
            New DeviceInfo instance
        """
        device_type = self._determine_device_type(device_id)
        device_info = DeviceInfo(
            device_id=device_id,
            device_type=str(device_type),
            status=log_status,  # Initial status from first log
            last_log_status=log_status,
            last_log_consecutive_count=1,
            success_count=1 if log_status == 'success' else 0,
            fail_count=1 if log_status == 'fail' else 0,
            recent_pattern='S' if log_status == 'success' else 'F'
        )
        
        self.logger.debug(f"Created new device: {device_id} (type: {device_type}, initial status: {log_status})")
        return device_info
    
    def _update_existing_device(self, device: DeviceInfo, log_status: str, max_history: int = 50) -> DeviceInfo:
        """
        Update an existing device with a new log status.
        
        Args:
            device: The existing DeviceInfo to update
            log_status: The new status from the log entry
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
            status=log_status
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
    
    def _process_batch(self) -> None:
        """Read all new logs and update device statuses accordingly."""
        # Check if processor is still running before processing
        if not self._running:
            return
            
        try:
            # Step 1: Read all new logs (no limit)
            new_logs = self.log_reader.read_next()
            
            if new_logs.empty:
                # No new logs found - debug log this
                self.logger.debug("No new log entries found in this batch")
                self.no_logs_found.emit()
                return
            
            self.logger.debug(f"Found {len(new_logs)} new log entries to process")
            
            # Step 2: Load current devices from database into memory
            devices_in_memory = self.devices_db.get_all()
            self.logger.debug(f"Loaded {len(devices_in_memory)} devices from database")
            
            # Step 3: Process logs line by line and update in-memory devices
            processed_count = 0
            for _, log_entry in new_logs.iterrows():
                device_id = log_entry.get('device', '')
                log_status = log_entry.get('status', '')
                
                if not device_id or not log_status:
                    self.logger.warning(f"Skipping log entry with missing device_id or status: {log_entry}")
                    continue
                
                # Get or create device info
                if device_id in devices_in_memory:
                    device_info = devices_in_memory[device_id]
                    # Update existing device
                    max_history = 50  # TODO: Get from config based on device_type
                    updated_device = self._update_existing_device(device_info, log_status, max_history)
                else:
                    # Create new device
                    updated_device = self._create_new_device(device_id, log_status)
                
                # Store updated device back in memory
                devices_in_memory[device_id] = updated_device
                processed_count += 1
            
            # Debug log which devices had new logs in this batch
            logged_devices = self._get_logged_devices(new_logs)
            if logged_devices:
                device_list = '\n'.join(logged_devices)
                self.logger.debug(f"Devices with new logs in this batch: {device_list}")
            
            # Step 4: Write all updated devices back to database
            success_count = 0
            for device_id, device_info in devices_in_memory.items():
                if self.devices_db.update_device(device_info):
                    success_count += 1
                else:
                    self.logger.error(f"Failed to update device {device_id} in database")
            
            self.logger.debug(f"Processed {processed_count} log entries, updated {success_count} devices in database")
            
            # Emit new logs processed signal with count
            self.new_logs_processed.emit(len(new_logs))
                
        except Exception as e:
            error_msg = f"Error processing log batch: {e}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)


def main():
    """Simple main function for testing the log processor."""
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    
    def on_new_logs_processed(count: int):
        print(f"Processed {count} new log entries")
    
    def on_no_logs_found():
        print("No new logs found in this batch")
    
    def on_error(error_msg: str):
        print(f"Error: {error_msg}")
    
    app = QApplication(sys.argv)
    
    try:
        # Use current working directory for testing
        db_directory = Path.cwd()
        processor = LogProcessor(
            db_directory=db_directory,
            batch_interval=2.0
        )
        
        # Connect signals
        processor.new_logs_processed.connect(on_new_logs_processed)
        processor.no_logs_found.connect(on_no_logs_found)
        processor.error_occurred.connect(on_error)
        
        print("Starting LogProcessor...")
        print("Press Ctrl+C to stop")
        
        processor.start()
        
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
