"""
Decision Engine

Core decision engine that processes device status changes and makes automated decisions.

Main functionality:
- Connects to the devices database
- Receives signals from LogProcessor about new log entries
- Designed to run on a separat        # Step 3: Evaluate devices and make decisions
        try:
            self._evaluate_devices()
            self.logger.debug("Device evaluation completed")
        except Exception as e:
            self.logger.error(f"Device evaluation error: {e}")
        
        # Step 4: Evaluate restart conditions
        try:
            self._evaluate_restart_conditions()
            self.logger.debug("Restart evaluation completed")
        except Exception as e:
            self.logger.error(f"Restart evaluation error: {e}")ill be extended to handle automated decision making
"""

from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Slot, Signal, QTimer
from monitor.log_setup import get_logger
from monitor.core.log_processor import LogProcessor
from monitor.services.devices_db import DevicesDatabase
from monitor.services.contact_db import ContactDatabase
from monitor.services.email_service import EmailService
from monitor.services.config_service import ConfigService
from monitor.services.devices_models import DeviceInfo, DeviceType
from monitor.services.alert_models import Alert, AlertType
from monitor.core.evaluators.consecutive_count_evaluator import ConsecutiveCountEvaluator
from monitor.core.evaluators.timeout_evaluator import TimeoutEvaluator
from monitor.core.evaluators.failure_rate_evaluator import FailureRateEvaluator
from monitor.core.device_status_manager import DeviceStatusManager
from monitor.core.restart_manager import RestartManager
from monitor.core.os_manager import OSManager
from monitor.core.server_manager import ServerManager

DEFAULT_RELAY_FAIL = 200  # Used for fan devices and similar relay-controlled equipment
DEFAULT_CAMERA_FAIL = 0.6
DEFAULT_RESTART = 5
DEFAULT_RESTART_COOLDOWN = 30  # Minimum minutes between computer restarts
DEFAULT_CHECK_EINTZOFIA_RUNNING = True  # Whether to check if Ein Tzofia is running before restart
DEFAULT_ENABLE_EINTZOFIA_AUTO_REOPEN = True  # Whether to enable automatic Ein Tzofia auto-reopen

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
    
    def __init__(self, logs_directory: Path, data_directory: Path, 
                 config_service: ConfigService = None, cycle_interval: float = 3.0):
        """
        Initialize the decision engine.
        
        Args:
            logs_directory: Directory containing the log database files
            data_directory: Directory containing the devices database
            config_service: Optional config service instance (creates new if None)
            cycle_interval: Time in seconds between monitoring cycles
        """
        super().__init__()
        self.logger = get_logger("monitor.core.decision_engine")
        
        # Use provided config service or create new one
        self.config_service = config_service or ConfigService()
        
        # Configuration
        self.logs_directory = logs_directory
        self.data_directory = data_directory
        self.cycle_interval = cycle_interval
        
        # State
        self._running = False
        self._start_time = None  # Track when the decision engine started
        
        # Timer for monitoring cycles (will be created when started)
        self._cycle_timer = None
        
        # Initialize device status manager
        self.device_status_manager = DeviceStatusManager()
        
        # Initialize OS manager
        self.os_manager = OSManager(self.config_service)
        
        # Initialize server manager
        self.server_manager = ServerManager(self.config_service, self.os_manager)
        
        # Database connections
        self.devices_db = DevicesDatabase(data_directory / "devices.db")
        self.contact_db = ContactDatabase(data_directory / "contacts.db")
        
        # Initialize email service
        self.email_service = EmailService(self.contact_db, self.server_manager, self.config_service)
        
        print("\n\n\n TEST")
        self.server_manager.send_email("SUBJECT","MESSAGE",["dan@bulltech.co.il"])
        print("\n\n\n")
        # Initialize log processor with shared database (no timer - controlled by this engine)
        self.log_processor = LogProcessor(logs_directory, data_directory, self.devices_db)
        
        # Initialize evaluators (will be set up in start() method)
        self.consecutive_count_evaluator = None
        self.timeout_evaluator = None
        self.failure_rate_evaluator = None
        self.restart_evaluator = None
        self.restart_manager = None  # Will be initialized in start() with config

        # Note: Alert database connection will be handled via signals    
        self.logger.info("DecisionEngine initialized")
    
    def _load_config_thresholds(self) -> None:
        """
        Load decision engine cycle interval from config file.
        
        Other settings are now read directly from config service for real-time updates.
        """
        try:
            # Use the injected config service
            config = self.config_service
            
            # Load decision engine cycle interval (seconds) if provided - keep cached for performance
            raw_cycle = config.get("system", "decision_cycle_seconds", self.cycle_interval)
            try:
                # Accept string or numeric; ignore empty string
                if raw_cycle not in (None, ""):
                    new_cycle = float(raw_cycle)
                    if new_cycle > 0:
                        self.cycle_interval = new_cycle
                    else:
                        self.logger.warning(f"decision_cycle_seconds must be > 0, got {new_cycle}; keeping {self.cycle_interval}")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid decision_cycle_seconds '{raw_cycle}', keeping {self.cycle_interval}")
            
            self.logger.info("Loaded Config")
            
        except Exception as e:
            self.logger.warning(f"Failed to load config, using defaults: {e}")
            # Keep the default values set in __init__

    def _get_evaluator_with_current_config(self, evaluator_type: str):
        """Get evaluator instance with current config values."""
        if evaluator_type == "consecutive_count":
            threshold = int(self.config_service.get("devices", "relay_fail_threshold", DEFAULT_RELAY_FAIL))
            return ConsecutiveCountEvaluator(self.logger, threshold)
        elif evaluator_type == "timeout":
            timeout = int(self.config_service.get("system", "minutes_to_restart", DEFAULT_RESTART))
            return TimeoutEvaluator(self.logger, timeout)
        elif evaluator_type == "failure_rate":
            threshold = float(self.config_service.get("devices", "camera_fail_threshold", DEFAULT_CAMERA_FAIL))
            return FailureRateEvaluator(self.logger, threshold)
        else:
            raise ValueError(f"Unknown evaluator type: {evaluator_type}")
    
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
        
        # Initialize evaluators (will be updated with current config values when used)
        self.consecutive_count_evaluator = None
        self.timeout_evaluator = None
        self.failure_rate_evaluator = None
        self.restart_manager = RestartManager(
            self.device_status_manager,
            self.config_service,
            self.os_manager,
            self.email_service
        )
        
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
        """
        print("\n\n============================================ DECISION ENGINE CYCLE ============================================")
        
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
        
        # Step 2: Check Ein Tzofia status if enabled
        try:
            self._check_and_start_eintzofia()
            self.logger.debug("Ein Tzofia check completed")
        except Exception as e:
            self.logger.error(f"Ein Tzofia check error: {e}")
        
        # Step 3: Evaluate devices and make decisions
        try:
            self._evaluate_devices()
            self.logger.debug("Device evaluation completed")
        except Exception as e:
            self.logger.error(f"Device evaluation error: {e}")
        
        self.devices_db.print_devices_summary("Device DB")

        # Step 3: Send pulse to server
        try:
            self._pulse_to_server()
            self.logger.debug("Server pulse completed")
        except Exception as e:
            self.logger.error(f"Server pulse error: {e}")

        # Step 4: Evaluate restart conditions
        try:
            self._evaluate_restart_conditions()
            self.logger.debug("Restart evaluation completed")
        except Exception as e:
            self.logger.error(f"Restart evaluation error: {e}")

        # Emit completion signal
        self.cycle_completed.emit(processed_count)
        
        # Log timestamp at the end of the cycle
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.debug(f"Cycle completed at: {current_time}")
        print(f"Cycle completed at: {current_time}\n")
    
    def _check_and_start_eintzofia(self) -> None:
        """Check if Ein Tzofia is running and start it if needed (when enabled)."""
        # Check config service directly for real-time setting
        if not self.config_service.get("system", "enable_eintzofia_auto_reopen", DEFAULT_ENABLE_EINTZOFIA_AUTO_REOPEN):
            return
            
        if not self.config_service.get("system", "check_eintzofia_running", DEFAULT_CHECK_EINTZOFIA_RUNNING):
            return
            
        try:
            # Use existing RestartManager method to check if Ein Tzofia is running
            if not self.restart_manager._is_eintzofia_running():
                self.logger.warning("Ein Tzofia is not running - attempting to start")
                
                # Get Ein Tzofia path and start it using initialized OSManager
                try:
                    eintzofia_path = self.os_manager.get_EinTzofia_path()
                    if eintzofia_path and Path(eintzofia_path).exists():
                        success = self.os_manager.open_file(eintzofia_path)
                        if success:
                            self.logger.info("Ein Tzofia started successfully")
                        else:
                            self.logger.error("Failed to start Ein Tzofia")
                    else:
                        self.logger.warning("Ein Tzofia path not found or doesn't exist - skipping auto-start")
                except Exception as path_error:
                    self.logger.warning(f"Could not get Ein Tzofia path: {path_error} - skipping auto-start")
            else:
                self.logger.debug("Ein Tzofia is running normally")
                
        except Exception as e:
            self.logger.error(f"Error checking/starting Ein Tzofia: {e}")
    
    def _evaluate_devices(self) -> None:
        """Evaluate all devices and make decisions (called by timer)."""
        if not self._running:
            return
        
        try:
            # Get all current device statuses from the database
            devices = self.devices_db.get_all()
            self.logger.debug(f"Evaluating {len(devices)} devices")
            
            # Evaluate each device and process the result
            for device_id, device_info in devices.items():
                self._ensure_device_tracked(device_info) # Adds the device to the json file
                self._evaluate_and_process_device(device_info)
            
        except Exception as e:
            self.logger.error(f"Error evaluating devices: {e}")
    
    def _evaluate_and_process_device(self, device: DeviceInfo) -> None:
        """
        Evaluate a device and take appropriate actions based on the result.
        
        This method:
        1. Determines device status using appropriate evaluator
        2. Takes actions (alerts, notifications) based on that status
        3. Updates persistent storage
        """
        # Step 1: Determine device status
        new_status = self._determine_device_status(device)
        if new_status is None:
            return  # No evaluation logic for this device type
        
        # Step 2: Process the evaluation result and take actions
        self._process_device_evaluation(device, new_status)
    
    def _determine_device_status(self, device: DeviceInfo) -> str:
        """
        Determine device status using the appropriate evaluator.
        
        Args:
            device: DeviceInfo instance to evaluate
            
        Returns:
            New status string, or None if no evaluation logic exists for this device type
        """
        device_type = device.device_type.lower()
        
        # Map device types to evaluation logic - use current config values
        if device_type in [DeviceType.FAN.value, DeviceType.SPRINKLER.value, 
                          DeviceType.GROUP.value, DeviceType.COMPORT.value, 
                          DeviceType.THI.value]:
            evaluator = self._get_evaluator_with_current_config("consecutive_count")
            return evaluator.evaluate(device)
            
        elif device_type == DeviceType.THREAD.value:
            evaluator = self._get_evaluator_with_current_config("timeout")
            return evaluator.evaluate(device)
            
        elif device_type == DeviceType.CAMERA.value:
            evaluator = self._get_evaluator_with_current_config("failure_rate")
            return evaluator.evaluate(device)
            
        else:
            self.logger.debug(f"No evaluation logic for device type: {device_type}")
            return None
    
    def _evaluate_restart_conditions(self) -> None:
        """Evaluate if restart conditions are met and restart computer if needed."""
        try:
            # Use RestartManager to handle all restart logic
            should_restart, reason = self.restart_manager.should_restart_computer(
                self._start_time
            )
            
            # Log the decision
            if should_restart:
                self.logger.info(f"Restart approved: {reason}")
                print(f"Restart approved: {reason}")  # TODO: Remove this print later
                
                # Execute restart (restart manager will update restart info directly)
                self.restart_manager.execute_restart()
            else:
                self.logger.info(f"Restart blocked: {reason}")
                if "Thread device failure detected" in reason:
                    print(f"{reason}")  # TODO: Remove this print later
                
        except Exception as e:
            self.logger.error(f"Error checking restart conditions: {e}")
    
    def _pulse_to_server(self) -> None:
        """Send pulse to server at the end of monitoring cycle."""
        try:
            self.logger.debug("Sending pulse to server")
            result = self.server_manager.pulse_to_server()
            self.logger.debug(f"Server pulse result: {result}")
        except Exception as e:
            self.logger.error(f"Failed to send pulse to server: {e}")
    
    def _ensure_device_tracked(self, device: DeviceInfo) -> None:
        """Ensure device is tracked in the json file"""
        device_id = device.device_id
        
        # If this is the first time seeing this device, set baseline to 'success'
        if self.device_status_manager.ensure_device_tracked(device_id, device.device_type, device.last_updated):
            self.logger.info(f"NEW DEVICE DETECTED: {device_id}")
    
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
    
    def _process_device_evaluation(self, device: DeviceInfo, new_status: str) -> None:
        """
        Process device evaluation result and take appropriate actions.
        
        This method handles:
        - Creating alerts for failed devices
        - Resolving alerts when devices recover  
        - Sending email notifications for status changes
        - Logging status changes
        - Updating persistent status storage
        """
        device_id = device.device_id
        previous_status = self.device_status_manager.get_device_status(device_id)
        
        # Always create alerts for failed devices (let alert DB handle deduplication)
        if new_status == 'fail':
            if previous_status != 'fail':
                print(f"DEVICE FAILED - {device_id}")
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
            self.device_status_manager.update_device_status(device_id, new_status, device.device_type, device.last_updated)
    
    @staticmethod
    def reset_statuses() -> None:
        """Reset decision engine statuses (for testing)."""
        DeviceStatusManager.reset_statuses()


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
        
        # Create shared config service
        config_service = ConfigService()
        
        # Create worker objects
        decision_engine = DecisionEngine(db_directory, db_directory, config_service)
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