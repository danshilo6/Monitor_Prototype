"""
RestartManager

Handles all computer restart logic and decision making.
"""

import psutil
from datetime import datetime, timedelta
from pathlib import Path
from monitor.log_setup import get_logger
from monitor.core.evaluators.restart_evaluator import RestartEvaluator


class RestartManager:
    """
    Manages computer restart decisions and execution.
    
    This class handles:
    - Evaluating if restart conditions are met
    - Checking if Ein Tzofia is running (if enabled)
    - Recording restart attempts
    - Executing computer restarts
    """
    
    def __init__(self, minutes_to_restart: int, restart_cooldown_minutes: int, 
                 check_eintzofia_running_enabled: bool):
        """
        Initialize the restart manager.
        
        Args:
            minutes_to_restart: Minutes a thread device can be offline before restart
            restart_cooldown_minutes: Minimum minutes between restarts
            check_eintzofia_running_enabled: Whether to check if Ein Tzofia is running
        """
        self.logger = get_logger("monitor.core.restart_manager")
        
        # Configuration
        self.check_eintzofia_running_enabled = check_eintzofia_running_enabled
        
        # Initialize restart evaluator
        self.restart_evaluator = RestartEvaluator(
            self.logger, minutes_to_restart, restart_cooldown_minutes
        )
        
        self.logger.debug("RestartManager initialized")
    
    def should_restart_computer(self, device_statuses: dict, restart_info: dict, 
                               engine_start_time: datetime) -> tuple[bool, str]:
        """
        Determine if the computer should be restarted.
        
        Args:
            device_statuses: Current device status tracking
            restart_info: Restart history information
            engine_start_time: When the decision engine started
            
        Returns:
            Tuple of (should_restart: bool, reason: str)
        """
        try:
            # Check basic restart conditions first
            if not self.restart_evaluator.should_restart(
                device_statuses, restart_info, engine_start_time
            ):
                # Check if there are failed thread devices for logging
                failed_device = self.restart_evaluator._find_failed_thread_device(device_statuses)
                if failed_device:
                    engine_runtime = datetime.now() - engine_start_time if engine_start_time else timedelta(0)
                    reason = f"Thread device failure detected but not restarting - engine runtime: {engine_runtime}"
                    return False, reason
                return False, "No restart conditions met"
            
            # If basic conditions are met, check Ein Tzofia running condition if enabled
            if self.check_eintzofia_running_enabled:
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
    
    def execute_restart(self, restart_info: dict) -> dict:
        """
        Execute computer restart and return updated restart info.
        
        Args:
            restart_info: Current restart information
            
        Returns:
            Updated restart info with new restart record
        """
        try:
            self.logger.info("RESTARTING COMPUTER due to thread device failure")
            print("RESTARTING COMPUTER due to thread device failure")  # TODO: Remove this print later
            
            # Record the restart
            restart_count = restart_info.get('restart_count', 0) + 1
            restart_record = self.restart_evaluator.create_restart_record()
            restart_record['restart_count'] = restart_count
            
            updated_restart_info = {
                'last_restart_time': restart_record['last_restart_time'],
                'restart_count': restart_count
            }
            
            self.logger.info(f"Recorded restart #{restart_count} at {restart_record['timestamp']}")
            
            # TODO: Add actual computer restart logic here
            # import subprocess
            # subprocess.run(['shutdown', '/r', '/t', '0'], check=True)
            
            return updated_restart_info
            
        except Exception as e:
            self.logger.error(f"Failed to execute restart: {e}")
            return restart_info  # Return unchanged restart info on error
    
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
