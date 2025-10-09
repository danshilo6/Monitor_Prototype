"""
RestartManager

Handles all computer restart logic and decision making.
"""

import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from monitor.log_setup import get_logger
from monitor.core.device_status_manager import DeviceStatusManager
from monitor.services.config_service import ConfigService
from monitor.core.os_manager import OSManager
from monitor.services.notification_service import NotificationService
from monitor.services.devices_models import DeviceType
from monitor.core.restart_db import RestartDB


class RestartManager:
    """
    Manages computer restart decisions and execution.
    
    This class handles:
    - Evaluating if restart conditions are met (previously in RestartEvaluator)
    - Checking if Ein Tzofia is running (if enabled)
    - Recording restart attempts
    - Executing computer restarts
    """
    
    def __init__(self, device_status_manager: DeviceStatusManager,
                 config_service: ConfigService, os_manager: OSManager, email_service: NotificationService = None):
        """
        Initialize the restart manager.
        
        Args:
            device_status_manager: Manager for device status persistence
            config_service: Configuration service for checking restart settings
            os_manager: OS manager for executing system operations like restart
            email_service: Notification service for sending restart notifications (optional)
        """
        self.logger = get_logger("monitor.core.restart_manager")
        
        # Configuration
        self.config_service = config_service
        self.os_manager = os_manager
        self.email_service = email_service
        
        # Store device status manager for restart info updates
        self.device_status_manager = device_status_manager
        
        # Initialize restart database
        self.restart_db = RestartDB()
        
        # Constants for defaults
        self.DEFAULT_RESTART = 5
        self.DEFAULT_RESTART_COOLDOWN = 30
        self.DEFAULT_CHECK_EINTZOFIA_RUNNING = True
        
        self.logger.debug("RestartManager initialized")

 
    
    def _find_failed_thread_device(self, device_statuses: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Find the first failed thread device.
        
        Args:
            device_statuses: Dictionary of device statuses
            
        Returns:
            Device ID of first failed thread device, or None if none found
        """
        for device_id, device_info in device_statuses.items():
            if (
                device_info.get('status') == 'fail' and
                device_info.get('type', '').lower() == DeviceType.THREAD.value.lower()
            ):
                return device_id
        return None
    
    def _find_thread_devices(self, devices_statuses: Dict[str, Dict[str, Any]]) -> list[str]:
        """Find all thread devices."""
        thread_type = DeviceType.THREAD.value.lower()
        return [
            device_id for device_id, device_info in devices_statuses.items() if device_info.get('type', '').lower() == thread_type
        ]

    def _comport_failed(self, device_statuses: Dict[str, Dict[str, Any]]) -> bool:
        """Check if any COM port device has a 'fail' status"""
        for device_id, device_info in device_statuses.items():
            if (device_info.get('type') == DeviceType.COMPORT.value and 
                device_info.get('status') == 'fail'):
                print("\n\n\n****** COMPORT FAILED *******\n\n\n")
                return True
        return False

    def _check_engine_runtime(self, engine_start_time: Optional[datetime], minutes_to_restart: int) -> bool:
        """
        Check if the engine has been running long enough to allow restart.
        
        Args:
            engine_start_time: When the decision engine started
            minutes_to_restart: Minimum minutes the engine must run before restart
            
        Returns:
            True if engine has run long enough, False otherwise
        """
        if engine_start_time is None:
            self.logger.debug("Engine start time is None, cannot restart")
            return False
        
        engine_runtime = datetime.now() - engine_start_time
        restart_threshold = timedelta(minutes=minutes_to_restart)
        
        if engine_runtime < restart_threshold:
            self.logger.debug(f"Engine runtime ({engine_runtime}) < restart threshold ({restart_threshold})")
            return False
        
        self.logger.debug(f"Engine runtime check passed: {engine_runtime} >= {restart_threshold}")
        return True
    
    def _in_new_day_grace_period(self) -> bool:
        """Check if current time is within the new day grace period, which is 12:00 AM plus the decision engine cycle time."""
        now = datetime.now()
        decision_cycle_seconds = int(self.config_service.get("system", "decision_engine_cycle_seconds", 60))
        decision_cycle_minutes = decision_cycle_seconds // 60
        grace_minutes = max(decision_cycle_minutes, 1)
        return now.hour == 0 and now.minute < grace_minutes

    def _check_restart_cooldown(self, restart_info: Dict[str, Any], restart_cooldown_minutes: int) -> bool:
        """
        Check if enough time has passed since the last restart.
        
        Args:
            restart_info: Dictionary containing restart history
            restart_cooldown_minutes: Minimum minutes between restarts
            
        Returns:
            True if cooldown period has passed, False otherwise
        """
        last_restart_str = restart_info.get('last_restart_time')
        if not last_restart_str:
            self.logger.debug("No previous restart recorded, cooldown check passed")
            return True
        
        try:
            last_restart_time = datetime.fromisoformat(last_restart_str)
            time_since_last_restart = datetime.now() - last_restart_time
            cooldown_threshold = timedelta(minutes=restart_cooldown_minutes)
            
            if time_since_last_restart < cooldown_threshold:
                self.logger.debug(f"Restart cooldown active: {time_since_last_restart} < {cooldown_threshold}")
                print(f"Still in cooldown: {time_since_last_restart} < {cooldown_threshold}")  # TODO: Remove this print later
                return False
            
            self.logger.debug(f"Cooldown check passed: {time_since_last_restart} >= {cooldown_threshold}")
            return True
            
        except ValueError as e:
            self.logger.warning(f"Could not parse last restart time '{last_restart_str}': {e}")
            return True  # If we can't parse the time, allow restart
    
    def should_restart_computer(self, engine_start_time: datetime) -> tuple[bool, str]:
        """
        Determine if the computer should be restarted.
        
        Args:
            engine_start_time: When the decision engine started
            
        Returns:
            Tuple of (should_restart: bool, reason: str)
        """
        try:
            # Get current device statuses and restart info from device status manager
            device_statuses = self.device_status_manager.get_device_statuses()
            restart_info = self.device_status_manager.get_restart_info()
            
            # Check restart conditions (including update flag)
            # First check if restart is requested due to updates
            if self.config_service.get("system", "pending_restart_after_update", False):
                self.logger.info("Restart requested due to pending updates")
                return True, "Updates applied - restart required"

            # Get current config values
            minutes_to_restart = int(self.config_service.get("system", "minutes_to_restart", self.DEFAULT_RESTART))
            restart_cooldown_minutes = int(self.config_service.get("system", "restart_cooldown_minutes", self.DEFAULT_RESTART_COOLDOWN))

            # Check timing constraints
            if not self._check_engine_runtime(engine_start_time, minutes_to_restart):
                engine_runtime = datetime.now() - engine_start_time if engine_start_time else timedelta(0)
                return False, f"Engine runtime ({engine_runtime}) less than required threshold ({minutes_to_restart} minutes)"
            
            if not self._check_restart_cooldown(restart_info, restart_cooldown_minutes):
                last_restart_str = restart_info.get('last_restart_time', 'unknown')
                return False, f"Still in restart cooldown period (last restart: {last_restart_str})"

            # Check if Comport failed (even within grace period)
            if self._comport_failed(device_statuses):
                self.logger.info("Restart approved due comport failure")
                return True, "COM port device failure detected - restart approved"

            # Check if new day grace period is active: 12:00 AM to 12:0 AM + decision engine cycle
            # This is for threads that may report fail briefly during daily reset 
            if self._in_new_day_grace_period():
                self.logger.info("Restart skipped due to new day grace period")
                return False, "New day grace period active - skipping restart"

            # Check if any thread devices are in fail status
            failed_thread_device = self._find_failed_thread_device(device_statuses)
            thread_devices = self._find_thread_devices(device_statuses)
            if not failed_thread_device and len(thread_devices) >= 3:
                self.logger.debug("No failed thread devices found")
                return False, "No failed thread devices found"
            
            if failed_thread_device:
                self.logger.debug(f"Found failed thread device: {failed_thread_device}")        
                self.logger.info("All restart conditions met - restart approved")
                return True, f"Thread device failure detected ({failed_thread_device}) - restart approved"
            else:
                # Less than 3 thread devices and at least one failed
                return True, "Thread device failure detected (insufficient thread devices) - restart approved"

        except Exception as e:
            self.logger.error(f"Error checking restart conditions: {e}")
            return False, f"Error checking restart conditions: {e}"
    
    def execute_restart(self, reason: str = "Manual restart") -> None:
        """
        Execute computer restart and record it in the database.
        
        Args:
            reason: The reason for the restart (will be stored in database)
        """
        try:
            # Clear the update restart flag before restarting
            update_restart_pending = self.config_service.get("system", "pending_restart_after_update", False)
            if update_restart_pending:
                self.config_service.set("system", "pending_restart_after_update", False)
                self.logger.info("Cleared pending restart flag after updates")

            # Check if restart is enabled in config before proceeding
            restart_enabled = self.config_service.get("system", "enable_restart", True)
            if not restart_enabled:
                self.logger.info("Restart requested but disabled in config - skipping restart")
                print("Restart disabled in config - skipping restart")
                return
            
            # Record the restart in database with reason
            if not self.restart_db.add_restart_record(reason):
                self.logger.warning("Failed to record restart in database, but continuing with restart")
            
            # Update legacy restart info for backward compatibility
            restart_info = self.device_status_manager.get_restart_info()
            restart_count = restart_info.get('restart_count', 0) + 1
            current_time = datetime.now()
            
            updated_restart_info = {
                'last_restart_time': current_time.isoformat(),
                'restart_count': restart_count
            }
            
            # Update restart info through device status manager
            self.device_status_manager.update_restart_info(updated_restart_info)
            
            self.logger.info(f"Recorded restart #{restart_count} at {current_time} - Reason: {reason}")
            
            # Send restart notification email before restarting
            self.send_restart_notification()

            # Execute the actual computer restart using OSManager
            self.logger.info("Executing computer restart...")
            self.os_manager.restart_pc()
            
        except Exception as e:
            self.logger.error(f"Failed to execute restart: {e}")
    
    def _is_eintzofia_running(self) -> bool:
        """
        Check if Ein Tzofia process is currently running.
        
        Returns:
            True if Ein Tzofia is running, False otherwise
        """
        try:
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    # Check both process name and executable path
                    proc_name = proc.info.get('name', '') or ''
                    proc_exe = proc.info.get('exe', '') or ''
                    proc_name_lower = proc_name.lower()
                    proc_exe_lower = proc_exe.lower()
                    
                    # Look for processes that contain "eintzofia" in name or executable path
                    if 'eintzofia' in proc_name_lower or 'eintzofia' in proc_exe_lower:
                        self.logger.debug(f"Found Ein Tzofia process: {proc.info}")
                        return True
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Process might have ended between iterations or we don't have access
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking if Ein Tzofia is running: {e}")
            return False
    
    def create_restart_record(self) -> dict:
        """
        Create a restart record with current timestamp and incremented count.
        
        Returns:
            Dictionary containing restart record information
        """
        current_time = datetime.now()
        return {
            'last_restart_time': current_time.isoformat(),
            'restart_count': 1,  # Will be updated by caller if needed
            'timestamp': current_time
        }

    def send_restart_notification(self) -> None:
        # Send restart notification email before restarting
        if self.email_service:
            try:
                self.logger.info("Sending restart notification email")
                threads = self.device_status_manager.get_threads_status()
                comport_status = self.device_status_manager.get_comport_status()
                self.email_service.send_restart_notification(
                    threads=threads, 
                    send_threads_info=True, 
                    comport_status=comport_status
                )
            except Exception as email_error:
                self.logger.error(f"Failed to send restart notification email: {email_error}")
                # Continue with restart even if email fails
        else:
            self.logger.debug("No email service configured - skipping restart notification email")

    def get_restart_history(self, limit: int = 100) -> list[dict]:
        """
        Get restart history from the database.
        
        Args:
            limit: Maximum number of restart records to return (default: 100)
            
        Returns:
            List of restart records, most recent first
        """
        return self.restart_db.get_restart_history(limit)

    def get_restart_statistics(self) -> dict:
        """
        Get restart statistics from the database.
        
        Returns:
            Dictionary containing restart statistics
        """
        return self.restart_db.get_restart_statistics()

    def get_restart_count(self) -> int:
        """
        Get the total number of restart records in the database.
        
        Returns:
            Total count of restart records
        """
        return self.restart_db.get_restart_count()
