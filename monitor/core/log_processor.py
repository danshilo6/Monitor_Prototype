"""
Log Processor

Continuously reads new log entries from the logs database and updates the device status database.

Main functionality:
- Reads logs in batches from the log database
- Extracts device status information from each log entry
- Tracks consecutive status counts for each device
- Updates the device status database with current states
- Runs continuously with configurable polling intervals
"""

import sys
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Tuple
from monitor.core.log_reader import LogReader
from monitor.services.device_status_db import DeviceStatusDatabase
from monitor.services.device_status_models import DeviceStatusInfo
from monitor.services.status_evaluator import StatusEvaluator
from monitor.services.config_service import ConfigService
from monitor.log_setup import get_logger


class LogProcessor:
    """
    Processes logs and updates device status database using batch processing.
    
    Core operations:
    - Reads new log entries in configurable batch sizes
    - Processes device status changes in memory
    - Maintains consecutive status counts for each device
    - Updates device status database with batch writes
    - Detects new devices and tracks known device list
    """
    
    # Processing constants
    DEFAULT_POLLING_INTERVAL = 2.0  # seconds between polling for new logs
    DEFAULT_LOG_BATCH_SIZE = 100  # max logs to process per batch
    INITIAL_CONSECUTIVE_COUNT = 1  # count when status first appears or changes
    
    # System devices to ignore (not real hardware)
    SYSTEM_DEVICES = {'thread', 'system_health', 'system', 'scheduler'}
    
    # Log entry column names
    LOG_COLUMN_DEVICE = 'device'
    LOG_COLUMN_STATUS = 'status' 
    LOG_COLUMN_TIMESTAMP = 'timestamp'
    
    def __init__(self, db_directory: Path, polling_interval: float = None, batch_size: int = None, device_status_db_path: str = None, config_path: str = None):
        """
        Initialize the log processor.
        
        Args:
            db_directory: Directory containing the log database files
            polling_interval: Time in seconds between polling for new logs (default: 2.0)
            batch_size: Max logs to process per batch (default: 100)
            device_status_db_path: Optional path for device status database (for testing)
            config_path: Optional path to config file (default: "config.json")
        """
        self.logger = get_logger("monitor.core.log_processor")
        
        # Load configuration
        self.config_service = ConfigService(config_path) if config_path else ConfigService()
        self.relay_fail_threshold = int(self.config_service.get("devices", "relay_fail_threshold", 200))
        self.logger.info(f"Using relay fail threshold: {self.relay_fail_threshold}")
        
        # Initialize status evaluator
        self.status_evaluator = StatusEvaluator(fail_threshold=self.relay_fail_threshold)
        
        # Configuration
        self.db_directory = db_directory
        self.polling_interval = polling_interval or self.DEFAULT_POLLING_INTERVAL
        self.batch_size = batch_size or self.DEFAULT_LOG_BATCH_SIZE
        self.running = False
        
        # Initialize components
        self.log_reader = LogReader(db_directory)
        self.device_status_db = DeviceStatusDatabase(device_status_db_path) if device_status_db_path else DeviceStatusDatabase()
        
        # Track devices we've seen to detect new ones
        self.known_devices: Set[str] = set()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Log processor initialized: interval={self.polling_interval}s, batch_size={self.batch_size}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start processing logs continuously."""
        self.running = True
        self.logger.info("Starting log processor...")
        
        # Load existing device statuses to avoid redundant database calls
        existing_statuses = self.device_status_db.get_all_device_statuses()
        self.known_devices = set(existing_statuses.keys())
        self.logger.info(f"Loaded {len(self.known_devices)} existing devices from status database")
        
        try:
            while self.running:
                self._process_log_batch()
                time.sleep(self.polling_interval)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self):
        """Stop processing and cleanup resources."""
        if self.running:
            self.logger.info("Stopping log processor...")
            self.running = False
            self.log_reader.close()
            self.device_status_db.close()
            self.logger.info("Log processor stopped")
    
    def _process_log_batch(self):
        """Process a batch of new log entries efficiently."""
        try:
            # Step 1: Get new logs
            new_logs = self.log_reader.read_next(limit=self.batch_size)
            
            if new_logs.empty:
                return
            
            self.logger.debug(f"Processing batch of {len(new_logs)} log entries")
            
            # Step 2: Get current device statuses (one database call)
            database_device_statuses = self.device_status_db.get_all_device_statuses()
            
            # Step 3: Process logs in memory and calculate updates
            updated_device_statuses = self._calculate_status_updates(new_logs, database_device_statuses)
            
            # Step 4: Write all updates to database
            self._apply_status_updates(updated_device_statuses)
            
        except Exception as e:
            self.logger.error(f"Error processing log batch: {e}")
    
    def _calculate_status_updates(self, new_logs, database_device_statuses: Dict[str, DeviceStatusInfo]) -> Dict[str, DeviceStatusInfo]:
        """
        Calculate all status updates from logs using status evaluator.
        
        For each device:
        - Updates log tracking information (last status, consecutive count)
        - Uses StatusEvaluator to determine if device status should change
        
        Args:
            new_logs: DataFrame of new log entries
            database_device_statuses: Dict of current device statuses from database
            
        Returns:
            Dict mapping device_id to updated DeviceStatusInfo
        """
        updated_device_statuses = {}  # device_id -> DeviceStatusInfo
        
        for _, log_entry in new_logs.iterrows():
            device_id = log_entry.get(self.LOG_COLUMN_DEVICE, '').strip()
            log_status = log_entry.get(self.LOG_COLUMN_STATUS, '').strip()
            
            # Skip invalid or system entries
            if not self._is_valid_device_entry(device_id, log_status):
                continue
            
            # Track new devices
            if device_id not in self.known_devices:
                self.logger.info(f"New device detected: {device_id}")
                self.known_devices.add(device_id)
            
            # Get current status (from previous update in this batch or from database)
            if device_id in updated_device_statuses:
                current_info = updated_device_statuses[device_id]
            elif device_id in database_device_statuses:
                current_info = database_device_statuses[device_id]
            else:
                # New device: create initial status info
                current_info = DeviceStatusInfo(
                    device_id=device_id,
                    current_status='',  # Will be determined by status evaluator
                    last_log_status='',  # Will be set by status evaluator
                    count=0,  # Will be incremented by status evaluator
                    last_updated=datetime.now()
                )
                self.logger.info(f"New device {device_id} detected")
            
            # Use status evaluator to determine updated status
            updated_info = self.status_evaluator.evaluate_status_after_log(current_info, log_status)
            
            # Log status changes
            if updated_info.current_status != current_info.current_status:
                self.logger.info(f"Device {device_id} status changed from '{current_info.current_status}' to '{updated_info.current_status}' after {updated_info.count} consecutive '{log_status}' logs")
            else:
                self.logger.debug(f"Device {device_id}: {log_status} count = {updated_info.count} (status: {updated_info.current_status}, threshold: {self.relay_fail_threshold})")
            
            # Store the updated status info
            updated_device_statuses[device_id] = updated_info
        
        return updated_device_statuses
    
    def _is_valid_device_entry(self, device_id: str, status: str) -> bool:
        """
        Check if a log entry represents a valid device status update.
        
        Args:
            device_id: The device identifier
            status: The status value
            
        Returns:
            True if this entry should be processed
        """
        # Must have both device and status
        if not device_id or not status:
            return False
        
        # Skip system devices
        if device_id.lower() in self.SYSTEM_DEVICES:
            return False
        
        return True
    
    def _apply_status_updates(self, updated_device_statuses: Dict[str, DeviceStatusInfo]):
        """
        Apply the calculated status updates to the database.
        
        Args:
            updated_device_statuses: Dict mapping device_id to DeviceStatusInfo
        """
        if not updated_device_statuses:
            return
        
        successful_updates = 0
        failed_updates = 0
        
        for device_id, status_info in updated_device_statuses.items():
            # Write the updated status info to database
            success = self.device_status_db.update_device_status(status_info)
            
            if success:
                successful_updates += 1
            else:
                failed_updates += 1
                self.logger.warning(f"Failed to update status for device {device_id}")
        
        # Log the results
        total_processed = len(updated_device_statuses)
        self.logger.debug(f"Database updates: {successful_updates}/{total_processed} successful")
        
        if failed_updates > 0:
            self.logger.error(f"{failed_updates} device status updates failed")
    
    def get_status_summary(self) -> Dict:
        """
        Get a summary of current device statuses.
        
        Returns:
            Dict with total_devices, status_counts, and last_updated
        """
        try:
            all_statuses = self.device_status_db.get_all_device_statuses()
            
            summary = {
                'total_devices': len(all_statuses),
                'status_counts': {},
                'last_updated': None
            }
            
            latest_update = None
            for device_id, status_info in all_statuses.items():
                # Count devices by status
                summary['status_counts'][status_info.current_status] = summary['status_counts'].get(status_info.current_status, 0) + 1
                
                # Track latest update time
                if latest_update is None or status_info.last_updated > latest_update:
                    latest_update = status_info.last_updated
            
            summary['last_updated'] = latest_update
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting status summary: {e}")
            return {
                'total_devices': 0, 
                'status_counts': {}, 
                'last_updated': None
            }


def main():
    """Main entry point for the log processor."""
    try:
        # Create processor with default settings
        processor = LogProcessor(
            db_directory=Path('.'), 
            polling_interval=LogProcessor.DEFAULT_POLLING_INTERVAL,
            batch_size=LogProcessor.DEFAULT_LOG_BATCH_SIZE
        )
        
        print("Starting log processor...")
        print(f"Batch size: {processor.batch_size} logs")
        print(f"Polling interval: {processor.polling_interval}s")
        print("Processing logs and updating device statuses...")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        
        processor.start()
        
    except Exception as e:
        print(f"❌ Failed to start log processor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
