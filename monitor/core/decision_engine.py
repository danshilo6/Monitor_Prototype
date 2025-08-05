"""
Decision Engine

Core decision engine that processes device status changes and makes automated decisions.

Main functionality:
- Connects to the devices database
- Receives signals from LogProcessor about new log entries
- Designed to run on a separate thread
- Will be extended to handle automated decision making
"""

from pathlib import Path
import json
import os
import platform
import psutil
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Slot, Signal, QTimer
from monitor.log_setup import get_logger
from monitor.core.log_processor import LogProcessor
from monitor.services.devices_db import DevicesDatabase
from monitor.services.config_service import ConfigService
from monitor.services.devices_models import DeviceInfo, DeviceType
from monitor.services.alert_models import Alert, AlertType

DEFAULT_RELAY_FAIL = 200  # Used for fan devices and similar relay-controlled equipment
DEFAULT_CAMERA_FAIL = 0.6
DEFAULT_RESTART = 5
DEFAULT_RESTART_COOLDOWN = 30  # Minimum minutes between restarts
DEFAULT_CHECK_EINTZOFIA_RUNNING_ENABLED = True  # Check if EinTzofia is running before restart

class DecisionEngine(QObject):
    """
    Decision engine that orchestrates the monitoring cycle.
    
    This engine:
    - Controls when log processing occurs (via LogProcessor)
    - Makes decisions based on device status changes
    - Designed to run on a separate thread for optimal performance
    """
    
    # Signal to indicate the engine has finished (for thread cleanup)
    finished = Signal()
    
    # Signals for cycle completion and monitoring
    cycle_completed = Signal(int)        # Emits count of processed logs per cycle
    
    # Signals for alert management (to be connected to alert database)
    alert_creation_requested = Signal(Alert)  # Emits Alert object when device fails
    alert_resolution_requested = Signal(str)  # Emits device_id when device recovers
    
    # Signals for email notifications (to be connected to email service)
    device_failure_notification_requested = Signal(object)  # Emits DeviceInfo
    device_recovery_notification_requested = Signal(object)  # Emits DeviceInfo
    
    def __init__(self, logs_directory: Path, data_directory: Path, cycle_interval: float = 3.0):
        """
        Initialize the decision engine.
        
        Args:
            logs_directory: Directory containing the log database files
            data_directory: Directory containing the devices database
            cycle_interval: Time in seconds between monitoring cycles
        """
        super().__init__()
        self.logger = get_logger("monitor.core.decision_engine")
        
        # Configuration
        self.logs_directory = logs_directory
        self.data_directory = data_directory
        self.cycle_interval = cycle_interval
        
        # State
        self._running = False
        self._start_time = None  # Track when the decision engine started
        
        # Timer for monitoring cycles (will be created when started)
        self._cycle_timer = None
        
        # Initialize log processor (no timer - controlled by this engine)
        self.log_processor = LogProcessor(logs_directory, data_directory)
        
        # Device failure thresholds and system settings (loaded from config)
        self.relay_fail_threshold = DEFAULT_RELAY_FAIL  # For fan and relay-controlled devices
        self.camera_fail_threshold = DEFAULT_CAMERA_FAIL
        self.minutes_to_restart = DEFAULT_RESTART
        self.restart_cooldown_minutes = DEFAULT_RESTART_COOLDOWN
        self.check_eintzofia_running_enabled = DEFAULT_CHECK_EINTZOFIA_RUNNING_ENABLED
        
        # Device status tracking (persistent)
        self._device_statuses = {}  # {device_id: {'status': str, 'timestamp': str, 'type': str}}
        self._restart_info = {}  # {'last_restart_time': str, 'restart_count': int}
        self._status_file = self._get_status_file_path()
        self._load_device_statuses()
        
        # Database connection
        self.devices_db = DevicesDatabase(data_directory / "devices.db")
        
        # Note: Alert database connection will be handled via signals
        
        self.logger.info("DecisionEngine initialized")
    
    @staticmethod
    def _get_status_file_path() -> Path:
        """Get path to the decision engine status file."""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "data" / "decision_engine_statuses.json"

    def _load_device_statuses(self) -> None:
        """Load device statuses from JSON file."""
        try:
            if self._status_file.exists():
                with open(self._status_file, 'r') as f:
                    data = json.load(f)
                
                # Handle both old format (just device statuses) and new format (with restart info)
                if isinstance(data, dict) and 'devices' in data:
                    # New format: {"devices": {...}, "restart_info": {...}}
                    self._device_statuses = data.get('devices', {})
                    self._restart_info = data.get('restart_info', {})
                else:
                    # Old format: just device statuses
                    self._device_statuses = data
                    self._restart_info = {}
                
                self.logger.debug(f"Loaded {len(self._device_statuses)} device statuses from file")
            else:
                self.logger.debug("No existing status file found, starting with empty statuses")
                self._device_statuses = {}
                self._restart_info = {}
        except Exception as e:
            self.logger.warning(f"Could not load device statuses: {e}")
            self._device_statuses = {}
            self._restart_info = {}

    def _save_device_statuses(self) -> None:
        """Save device statuses and restart info to JSON file."""
        try:
            # Ensure data directory exists
            self._status_file.parent.mkdir(exist_ok=True)
            
            # Save in new format with both device statuses and restart info
            data = {
                'devices': self._device_statuses,
                'restart_info': self._restart_info
            }
            
            with open(self._status_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Saved {len(self._device_statuses)} device statuses and restart info to file")
        except Exception as e:
            self.logger.warning(f"Could not save device statuses: {e}")
    
    def _get_device_status(self, device_id: str) -> str:
        """Get the current status for a device, returns 'success' if not found (new device)."""
        device_info = self._device_statuses.get(device_id, {})
        return device_info.get('status', 'success')
    
    def _update_device_status(self, device_id: str, status: str, device_type: str, timestamp: datetime) -> None:
        """Update device status with timestamp and type information."""
        self._device_statuses[device_id] = {
            'status': status,
            'timestamp': timestamp.isoformat(),
            'type': device_type
        }
        self._save_device_statuses()
    
    def _load_config_thresholds(self) -> None:
        """
        Load device failure thresholds and system settings from config file.
        
        This method reads the config.json file and extracts the device
        thresholds and restart settings used for automated decisions.
        """
        try:
            config = ConfigService()
            
            # Load device thresholds
            self.relay_fail_threshold = int(config.get("devices", "relay_fail_threshold", DEFAULT_RELAY_FAIL))
            self.camera_fail_threshold = float(config.get("devices", "camera_fail_threshold", DEFAULT_CAMERA_FAIL))
            
            # Load system restart setting
            self.minutes_to_restart = int(config.get("system", "minutes_to_restart", DEFAULT_RESTART))
            self.restart_cooldown_minutes = int(config.get("system", "restart_cooldown_minutes", DEFAULT_RESTART_COOLDOWN))
            self.check_eintzofia_running_enabled = config.get("system", "check_eintzofia_running", DEFAULT_CHECK_EINTZOFIA_RUNNING_ENABLED) in [True, "true", "True", "1", 1]
            
            self.logger.info(f"Loaded config: relay_fail={self.relay_fail_threshold}, "
                           f"camera_fail={self.camera_fail_threshold}, "
                           f"restart_time={self.minutes_to_restart} minutes, "
                           f"restart_cooldown={self.restart_cooldown_minutes} minutes, "
                           f"check_eintzofia_running_enabled={self.check_eintzofia_running_enabled}")
            
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            # Keep the default values set in __init__
    
    @Slot()
    def start(self) -> None:
        """Start the decision engine with its own timer."""
        if self._running:
            self.logger.warning("DecisionEngine is already running")
            return
        
        # Record start time
        self._start_time = datetime.now()
        
        # Load config thresholds once at startup
        self._load_config_thresholds()
        
        # Start the log processor (no timer needed)
        self.log_processor.start()
        
        # Create timer on current thread (worker thread)
        self._cycle_timer = QTimer()
        self._cycle_timer.timeout.connect(self.run_cycle)
        self._cycle_timer.setInterval(int(self.cycle_interval * 1000))  # Convert to milliseconds
        
        self._running = True
        self._cycle_timer.start()
        
        self.logger.info(f"DecisionEngine started with {self.cycle_interval}s cycle at {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    @Slot()
    def stop(self) -> None:
        """Stop the decision engine."""
        if not self._running:
            return
        
        self.logger.info("Stopping DecisionEngine...")
        self._running = False
        self._start_time = None  # Reset start time
        
        # Stop and cleanup timer
        if self._cycle_timer is not None:
            self._cycle_timer.stop()
            self._cycle_timer.deleteLater()
            self._cycle_timer = None
        
        # Close log processor
        self.log_processor.stop()
        
        self.devices_db.close()
        self.logger.info("DecisionEngine stopped")
        self.finished.emit()  # Emit finished signal for thread cleanup
    
    @Slot()
    def close_resources(self) -> None:
        """Close all database connections and resources without stopping the engine."""
        try:
            self.logger.debug("Closing DecisionEngine resources...")
            
            # Close log processor connections
            if hasattr(self.log_processor, 'stop'):
                self.log_processor.stop()
                self.logger.debug("LogProcessor resources closed")
            
            # Close devices database connections
            if hasattr(self.devices_db, 'close'):
                self.devices_db.close()
                self.logger.debug("DevicesDatabase connections closed")
                
        except Exception as e:
            self.logger.error("Error closing DecisionEngine resources", exc_info=True)
    
    def is_running(self) -> bool:
        """Check if the engine is currently running."""
        return self._running
    
    @Slot()
    def run_cycle(self) -> None:
        """
        Run one monitoring cycle.
        
        This method processes logs first, then evaluates devices sequentially.
        Called by the ThreadManager's timer.
        """
        if not self._running:
            self.logger.warning("DecisionEngine is not running, cannot run cycle")
            return
        
        self.logger.debug("Running monitoring cycle")
        
        # Step 1: Process new logs
        try:
            processed_count = self.log_processor.process_batch()
            self.logger.debug(f"Processed {processed_count} logs")
        except Exception as e:
            self.logger.error(f"Log processor error: {e}")
            processed_count = 0
        
        # Step 2: Evaluate devices and make decisions
        try:
            self._evaluate_devices()
            self.logger.debug("Device evaluation completed")
        except Exception as e:
            self.logger.error(f"Device evaluation error: {e}")
        
        # Emit completion signal
        self.cycle_completed.emit(processed_count)
    
    def _evaluate_devices(self) -> None:
        """Evaluate all devices and make decisions (called by timer)."""
        if not self._running:
            return
        
        try:
            # Check if EinTzofia is running (if check is enabled) - independent of restart logic
            if self.check_eintzofia_running_enabled:
                if not self._is_eintzofia_running():
                    self.logger.warning("EinTzofia is not running!")
                    print("\nEin Tzofia:  Closed\n")
                else:
                    self.logger.debug("EinTzofia is running normally")
                    print("\nEin Tzofia:  RUNNING\n")
            # Get all current device statuses from the database
            devices = self.devices_db.get_all()
            self.logger.debug(f"Evaluating {len(devices)} devices")
            
            # Evaluate each device for decision logic
            for device_id, device_info in devices.items():
                self._ensure_device_tracked(device_info) # Adds the device to the json file
                new_status = self._evaluate_device(device_info)
                if new_status is not None:
                    self._handle_status_change(device_info, new_status)
            
        except Exception as e:
            self.logger.error(f"Error evaluating devices: {e}")
    
    def _is_relay_device(self, device_type: str) -> bool:
        relay_types = [
            DeviceType.FAN.value,
            DeviceType.SPRINKLER.value, 
            DeviceType.GROUP.value,
            DeviceType.COMPORT.value,
            DeviceType.THI.value,
        ]
        return device_type in relay_types

    def _is_thread_device(self, device_type: str) -> bool:
        thread_types = [
            DeviceType.THREAD.value,
            DeviceType.DEVICE_MODE_THREAD.value,
            DeviceType.SYSTEM_HEALTH.value
        ]
        return device_type in thread_types

    def _evaluate_device(self, device: DeviceInfo) -> str:
        """
        Evaluate a single device and return the new status.
        
        Args:
            device: DeviceInfo instance to evaluate
            
        Returns:
            New status string, or None if no evaluation logic exists for this device type
        """
        device_type = device.device_type.lower()
        
        # Handle relay-controlled devices
        if self._is_relay_device(device_type):
            return self._evaluate_relay_device(device)
        # Handle thread-based devices
        elif self._is_thread_device(device_type):
            return self._evaluate_thread_device(device)
        elif device_type == DeviceType.CAMERA.value:
            return self._evaluate_camera_device(device)
        else:
            # For other device types (unknown)
            self.logger.debug(f"No decision logic for device type: {device_type} (device: {device.device_id})")
            return None

    def _evaluate_relay_device(self, device: DeviceInfo) -> str:
        consecutive_count = device.last_log_consecutive_count
        last_status = device.last_log_status
        
        # Determine current decision status
        if consecutive_count >= self.relay_fail_threshold:
            return last_status  # Use the actual device status ('fail' or 'success')
        else:
            return None  # Below threshold - no status change needed

    def _evaluate_thread_device(self, device: DeviceInfo) -> str:
        """Evaluate thread devices based on time since last activity"""
        time_since_update = datetime.now() - device.last_updated
        timeout_threshold = timedelta(minutes=self.minutes_to_restart)
        
        if time_since_update >= timeout_threshold:
            # Check if DecisionEngine has been running long enough to restart
            if self._should_restart_eintzofia():
                self.logger.info("RESTARTING EIN TZOFIA")
                self._record_restart()  # Record the restart time and count
                # TODO: Add actual restart logic here
            else:
                # Log when restart would happen but timing prevents it
                engine_runtime = datetime.now() - self._start_time if self._start_time else timedelta(0)
                restart_threshold = timedelta(minutes=self.minutes_to_restart)
                self.logger.info(f"Thread device failure detected but not restarting Ein Tzofia yet - engine runtime: {engine_runtime}, required: {restart_threshold}")
            return 'fail'  # Thread inactive too long
        else:
            return 'success'  # Thread is active

    def _evaluate_camera_device(self, device: DeviceInfo) -> str:
        """Evaluate camera devices based on failure rate"""
        failure_rate = device.get_failure_rate()

        if failure_rate >= self.camera_fail_threshold:
            return 'fail'  
        else:
            return 'success'
    
    def _should_restart_eintzofia(self) -> bool:
        """
        Check if Ein Tzofia should be restarted.
        
        Only restart if:
        1. The DecisionEngine has been running for longer than the restart timeout
        2. Enough time has passed since the last restart (cooldown period)
        
        Returns:
            True if Ein Tzofia should be restarted, False otherwise
        """
        if self._start_time is None:
            return False
        
        # Calculate how long the DecisionEngine has been running
        engine_runtime = datetime.now() - self._start_time
        restart_threshold = timedelta(minutes=self.minutes_to_restart)
        
        # Check if engine has been running long enough
        if engine_runtime < restart_threshold:
            self.logger.debug(f"DecisionEngine runtime ({engine_runtime}) < restart threshold ({restart_threshold}), skipping Ein Tzofia restart")
            return False
        
        # Check cooldown period since last restart
        last_restart_str = self._restart_info.get('last_restart_time')
        if last_restart_str:
            try:
                last_restart_time = datetime.fromisoformat(last_restart_str)
                time_since_last_restart = datetime.now() - last_restart_time
                cooldown_threshold = timedelta(minutes=self.restart_cooldown_minutes)
                
                if time_since_last_restart < cooldown_threshold:
                    self.logger.debug(f"Time since last restart ({time_since_last_restart}) < cooldown threshold ({cooldown_threshold}), skipping Ein Tzofia restart")
                    return False
                    
            except ValueError as e:
                self.logger.warning(f"Could not parse last restart time '{last_restart_str}': {e}")
        
        self.logger.debug(f"DecisionEngine runtime ({engine_runtime}) >= restart threshold ({restart_threshold}), allowing Ein Tzofia restart")
        
        # Check if EinTzofia is actually running (if check is enabled)
        if self.check_eintzofia_running_enabled:
            if not self._is_eintzofia_running():
                self.logger.debug("EinTzofia is not running, no need to restart")
                return False
            else:
                self.logger.debug("EinTzofia is running, restart is appropriate")
        else:
            self.logger.debug("EinTzofia running check is disabled, proceeding with restart")
        
        return True
    
    def _record_restart(self) -> None:
        """Record that a restart has occurred by updating the restart info."""
        try:
            current_time = datetime.now()
            restart_count = self._restart_info.get('restart_count', 0) + 1
            
            self._restart_info = {
                'last_restart_time': current_time.isoformat(),
                'restart_count': restart_count
            }
            
            self._save_device_statuses()  # Save the updated restart info
            self.logger.info(f"Recorded restart #{restart_count} at {current_time}")
            
        except Exception as e:
            self.logger.error(f"Failed to record restart: {e}")
    
    def _is_eintzofia_running(self) -> bool:
        """
        Check if EinTzofia process is currently running.
        
        Returns:
            True if EinTzofia is running, False otherwise
        """
        try:
            # Get EinTzofia path from config
            config = ConfigService()
            eintzofia_path = config.get("general", "eintzofia_path", "")
            
            if not eintzofia_path:
                self.logger.warning("EinTzofia path not configured, assuming it's not running")
                return False
            
            # Extract the executable name from the path
            eintzofia_exe_name = os.path.basename(eintzofia_path)
            
            # For Windows, ensure we have the .exe extension for comparison
            current_os = platform.system()
            if current_os == "Windows":
                if not eintzofia_exe_name.lower().endswith('.exe'):
                    eintzofia_exe_name += '.exe'
            
            # Check all running processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name']
                    if proc_name:
                        # Case-insensitive comparison
                        if proc_name.lower() == eintzofia_exe_name.lower():
                            self.logger.debug(f"Found EinTzofia process: {proc_name} (PID: {proc.info['pid']})")
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process disappeared or access denied, continue checking others
                    continue
            
            self.logger.debug(f"EinTzofia process '{eintzofia_exe_name}' not found in running processes")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if EinTzofia is running: {e}")
            # If we can't check, assume it's running to avoid unnecessary restarts
            return True
    
    def _ensure_device_tracked(self, device: DeviceInfo) -> None:
        """Ensure device is tracked in the json file"""
        device_id = device.device_id
        
        # If this is the first time seeing this device, set baseline to 'success'
        if device_id not in self._device_statuses:
            self.logger.info(f"NEW DEVICE DETECTED: {device_id}")
            self._update_device_status(device_id, 'success', device.device_type, device.last_updated)
    
    def _get_device_alert_type(self, device_type: str) -> AlertType:
        """Map device type to alert type directly."""
        # First try exact match
        try:
            return AlertType(device_type)
        except ValueError:
            pass
        
        # Then try lowercase match (for most device types)
        try:
            return AlertType(device_type.lower())
        except ValueError:
            # If device type doesn't exist in AlertType, use UNKNOWN
            self.logger.warning(f"Unknown device type for alert: {device_type}, using UNKNOWN")
            return AlertType.UNKNOWN
    
    def _create_device_failure_alert(self, device: DeviceInfo) -> None:
        """Create an alert for a failed device by emitting a signal."""
        try:
            device_id = device.device_id
            alert_type = self._get_device_alert_type(device.device_type)
            
            # Use device_id as both alert ID and description (now consistent for all device types)
            alert_id = device_id
            description = device_id
            
            alert = Alert(
                id=alert_id,
                alert_type=alert_type,
                description=description,
                timestamp=datetime.now()
            )
            
            # Emit signal instead of directly calling database
            self.alert_creation_requested.emit(alert)
            self.logger.info(f"Requested failure alert creation for device {device_id}: {alert_id}")
                
        except Exception as e:
            self.logger.error(f"Error creating failure alert for device {device.device_id}: {e}")
    
    def _resolve_device_recovery_alert(self, device: DeviceInfo) -> None:
        """Resolve any existing alerts for a recovered device by emitting a signal."""
        try:
            # Use device_id as alert ID (now consistent for all device types)
            alert_id = device.device_id
            
            # Emit signal with alert_id - the alert database will find and resolve matching alerts
            self.alert_resolution_requested.emit(alert_id)
            self.logger.info(f"Requested alert resolution for recovered device {device.device_id} (alert_id: {alert_id})")
                
        except Exception as e:
            self.logger.error(f"Error requesting alert resolution for device {device.device_id}: {e}")
    
    def _handle_status_change(self, device: DeviceInfo, new_status: str) -> None:
        """
        Handle status changes for any device type.
        
        This method contains the common logic for:
        - Always alerting for failed devices (regardless of status change)
        - Only alerting recovery when status changes from fail to success
        - Sending email notifications for status changes
        - Logging appropriate messages
        - Updating persistent storage
        """
        device_id = device.device_id
        previous_status = self._get_device_status(device_id)
        
        # Always create alerts for failed devices (let alert DB handle deduplication)
        if new_status == 'fail':
            if previous_status != 'fail':
                self.logger.warning(f"DEVICE FAILED - {device_id}")
                # Send email notification for new device failure
                self.device_failure_notification_requested.emit(device)
            else:
                self.logger.debug(f"Device {device_id} still in fail status - ensuring alert exists")
            # Always signal alert for failed devices
            self._create_device_failure_alert(device)
            
        # Only resolve alerts when transitioning from fail to success
        elif new_status == 'success' and previous_status == 'fail':
            self.logger.info(f"DEVICE RECOVERED - {device_id}")
            # Resolve any existing alerts for recovered device
            self._resolve_device_recovery_alert(device)
            # Send email notification for device recovery
            self.device_recovery_notification_requested.emit(device)
        elif new_status == 'success':
            self.logger.debug(f"Device {device_id} status unchanged: {new_status}")
        
        # Update status tracking if status actually changed
        if new_status != previous_status:
            self._update_device_status(device_id, new_status, device.device_type, device.last_updated)
    
    @staticmethod
    def reset_statuses() -> None:
        """Reset decision engine statuses (for testing)."""
        try:
            status_file = DecisionEngine._get_status_file_path()
            if status_file.exists():
                status_file.unlink()
                print(f"Decision engine statuses reset: {status_file}")
            else:
                print("No status file found to reset")
        except Exception as e:
            print(f"Error resetting statuses: {e}")


def main():
    """Example of running DecisionEngine and LogProcessor on separate threads."""
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThread
    from monitor.core.log_processor import LogProcessor
    
    app = QApplication(sys.argv)
    
    try:
        # Use current working directory for testing
        db_directory = Path.cwd()
        
        # Create worker objects
        decision_engine = DecisionEngine(db_directory)
        log_processor = LogProcessor(
            db_directory=db_directory,
            batch_interval=2.0
        )
        
        # Create threads
        decision_thread = QThread()
        log_processor_thread = QThread()
        
        # Move workers to their threads
        decision_engine.moveToThread(decision_thread)
        log_processor.moveToThread(log_processor_thread)
        
        # No connection needed - each component runs independently on its own timer
        
        # Connect thread lifecycle signals
        # When thread starts, start the worker
        decision_thread.started.connect(decision_engine.start)
        log_processor_thread.started.connect(log_processor.start)
        
        # When worker finishes, quit the thread
        decision_engine.finished.connect(decision_thread.quit)
        log_processor.finished.connect(log_processor_thread.quit)
        
        # When thread quits, delete it (cleanup)
        decision_thread.finished.connect(decision_thread.deleteLater)
        log_processor_thread.finished.connect(log_processor_thread.deleteLater)
        
        print("Starting DecisionEngine and LogProcessor on separate threads...")
        print("Press Ctrl+C to stop")
        
        # Start the threads (this will call worker.start() on each thread)
        decision_thread.start()
        log_processor_thread.start()
        
        # Run the Qt event loop on main thread
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        # Stop workers (which will emit finished signals)
        if 'decision_engine' in locals():
            decision_engine.stop()
        if 'log_processor' in locals():
            log_processor.close()
        
        # Wait for threads to finish
        if 'decision_thread' in locals() and decision_thread.isRunning():
            decision_thread.quit()
            decision_thread.wait()
        if 'log_processor_thread' in locals() and log_processor_thread.isRunning():
            log_processor_thread.quit()
            log_processor_thread.wait()
        
        print("All threads stopped")


if __name__ == "__main__":
    main()