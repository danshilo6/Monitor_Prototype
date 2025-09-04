"""
RestartManager

Handles all computer restart logic and decision making.
"""

import psutil
from datetime import datetime, timedelta
from pathlib import Path
from monitor.log_setup import get_logger
from monitor.core.evaluators.restart_evaluator import RestartEvaluator
from monitor.core.device_status_manager import DeviceStatusManager
from monitor.services.config_service import ConfigService
from monitor.core.os_manager import OSManager
from monitor.services.email_service import EmailService


class RestartManager:
    """
    Manages computer restart decisions and execution.
    
    This class handles:
    - Evaluating if restart conditions are met
    - Checking if Ein Tzofia is running (if enabled)
    - Recording restart attempts
    - Executing computer restarts
    """
    
    def __init__(self, device_status_manager: DeviceStatusManager,
                 config_service: ConfigService, os_manager: OSManager, email_service: EmailService = None):
        """
        Initialize the restart manager.
        
        Args:
            device_status_manager: Manager for device status persistence
            config_service: Configuration service for checking restart settings
            os_manager: OS manager for executing system operations like restart
            email_service: Email service for sending restart notifications (optional)
        """
        self.logger = get_logger("monitor.core.restart_manager")
        
        # Configuration
        self.config_service = config_service
        self.os_manager = os_manager
        self.email_service = email_service
        
        # Store device status manager for restart info updates
        self.device_status_manager = device_status_manager
        
        # Constants for defaults
        self.DEFAULT_RESTART = 5
        self.DEFAULT_RESTART_COOLDOWN = 30
        self.DEFAULT_CHECK_EINTZOFIA_RUNNING = True
        
        self.logger.debug("RestartManager initialized")

    def _get_restart_evaluator(self):
        """Get restart evaluator with current config values."""
        minutes_to_restart = int(self.config_service.get("system", "minutes_to_restart", self.DEFAULT_RESTART))
        restart_cooldown_minutes = int(self.config_service.get("system", "restart_cooldown_minutes", self.DEFAULT_RESTART_COOLDOWN))
        return RestartEvaluator(self.logger, minutes_to_restart, restart_cooldown_minutes)
    
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
            
            # Get restart evaluator with current config values
            restart_evaluator = self._get_restart_evaluator()
            
            # Check basic restart conditions first
            if not restart_evaluator.should_restart(
                device_statuses, restart_info, engine_start_time
            ):
                # Check if there are failed thread devices for logging
                failed_device = restart_evaluator._find_failed_thread_device(device_statuses)
                if failed_device:
                    engine_runtime = datetime.now() - engine_start_time if engine_start_time else timedelta(0)
                    reason = f"Thread device failure detected but not restarting - engine runtime: {engine_runtime}"
                    return False, reason
                return False, "No restart conditions met"
            
            # If basic conditions are met, check Ein Tzofia running condition if enabled
            check_eintzofia_running_enabled = self.config_service.get("system", "check_eintzofia_running", self.DEFAULT_CHECK_EINTZOFIA_RUNNING)
            if check_eintzofia_running_enabled:
                if not self._is_eintzofia_running():
                    reason = "Thread device failure detected but Ein Tzofia is NOT running - restart blocked"
                    return False, reason
                else:
                    reason = "Ein Tzofia is running - restart approved"
                    return True, reason
            else:
                reason = "Ein Tzofia running check disabled - restart approved"
                return True, reason
                
        except Exception as e:
            self.logger.error(f"Error checking restart conditions: {e}")
            return False, f"Error checking restart conditions: {e}"
    
    def execute_restart(self) -> None:
        """
        Execute computer restart and update restart info.
        """
        try:
            # Check if restart is enabled in config before proceeding
            restart_enabled = self.config_service.get("system", "enable_restart", True)
            if not restart_enabled:
                self.logger.info("Restart requested but disabled in config - skipping restart")
                self.send_restart_notification()
                print("restart email notification sent for debugging purposes")
                return
            
            self.logger.info("RESTARTING COMPUTER due to thread device failure")
            print("RESTARTING COMPUTER due to thread device failure")  # TODO: Remove this print later
            
            # Get current restart info
            restart_info = self.device_status_manager.get_restart_info()
            
            # Record the restart
            restart_count = restart_info.get('restart_count', 0) + 1
            restart_record = self.create_restart_record()
            restart_record['restart_count'] = restart_count
            
            updated_restart_info = {
                'last_restart_time': restart_record['last_restart_time'],
                'restart_count': restart_count
            }
            
            # Update restart info directly through device status manager
            self.device_status_manager.update_restart_info(updated_restart_info)
            
            self.logger.info(f"Recorded restart #{restart_count} at {restart_record['timestamp']}")
            
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
                self.email_service.send_restart_notification(threads=threads, send_threads_info=True)
            except Exception as email_error:
                self.logger.error(f"Failed to send restart notification email: {email_error}")
                # Continue with restart even if email fails
        else:
            self.logger.debug("No email service configured - skipping restart notification email")
