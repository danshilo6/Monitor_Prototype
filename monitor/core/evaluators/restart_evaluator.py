"""
Restart Evaluator

Handles the logic for determining when the computer should be restarted
based on thread device failures and timing constraints.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

class RestartEvaluator:
    """
    Evaluates whether the computer should be restarted based on:
    - Thread device failures
    - Engine runtime requirements
    - Restart cooldown periods
    """
    
    def __init__(self, logger: logging.Logger, minutes_to_restart: int, restart_cooldown_minutes: int):
        """
        Initialize the restart evaluator.
        
        Args:
            logger: Logger instance for this evaluator
            minutes_to_restart: Minimum minutes the engine must run before restart is allowed
            restart_cooldown_minutes: Minimum minutes between restarts
        """
        self.logger = logger
        self.minutes_to_restart = minutes_to_restart
        self.restart_cooldown_minutes = restart_cooldown_minutes
        self.thread_device_types = ['thread', 'device_mode_thread', 'system_health']
    
    def should_restart(self, device_statuses: Dict[str, Dict[str, Any]], 
                      restart_info: Dict[str, Any], 
                      engine_start_time: Optional[datetime]) -> bool:
        """
        Determine if the computer should be restarted.
        
        Args:
            device_statuses: Dictionary of device statuses from persistent storage
            restart_info: Dictionary containing restart history information
            engine_start_time: When the decision engine started
            
        Returns:
            True if restart should occur, False otherwise
        """
        # Check if any thread devices are in fail status
        failed_thread_device = self._find_failed_thread_device(device_statuses)
        if not failed_thread_device:
            self.logger.debug("No failed thread devices found")
            return False
        
        self.logger.debug(f"Found failed thread device: {failed_thread_device}")
        
        # Check timing constraints
        if not self._check_engine_runtime(engine_start_time):
            return False
        
        if not self._check_restart_cooldown(restart_info):
            return False
        
        self.logger.info("All restart conditions met - restart approved")
        return True
    
    def _find_failed_thread_device(self, device_statuses: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Find the first failed thread device.
        
        Args:
            device_statuses: Dictionary of device statuses
            
        Returns:
            Device ID of first failed thread device, or None if none found
        """
        for device_id, device_info in device_statuses.items():
            if (device_info.get('status') == 'fail' and 
                device_info.get('type', '').lower() in self.thread_device_types):
                return device_id
        return None
    
    def _check_engine_runtime(self, engine_start_time: Optional[datetime]) -> bool:
        """
        Check if the engine has been running long enough to allow restart.
        
        Args:
            engine_start_time: When the decision engine started
            
        Returns:
            True if engine has run long enough, False otherwise
        """
        if engine_start_time is None:
            self.logger.debug("Engine start time is None, cannot restart")
            return False
        
        engine_runtime = datetime.now() - engine_start_time
        restart_threshold = timedelta(minutes=self.minutes_to_restart)
        
        if engine_runtime < restart_threshold:
            self.logger.debug(f"Engine runtime ({engine_runtime}) < restart threshold ({restart_threshold})")
            return False
        
        self.logger.debug(f"Engine runtime check passed: {engine_runtime} >= {restart_threshold}")
        return True
    
    def _check_restart_cooldown(self, restart_info: Dict[str, Any]) -> bool:
        """
        Check if enough time has passed since the last restart.
        
        Args:
            restart_info: Dictionary containing restart history
            
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
            cooldown_threshold = timedelta(minutes=self.restart_cooldown_minutes)
            
            if time_since_last_restart < cooldown_threshold:
                self.logger.debug(f"Restart cooldown active: {time_since_last_restart} < {cooldown_threshold}")
                print(f"Still in cooldown: {time_since_last_restart} < {cooldown_threshold}")  # TODO: Remove this print later
                return False
            
            self.logger.debug(f"Cooldown check passed: {time_since_last_restart} >= {cooldown_threshold}")
            return True
            
        except ValueError as e:
            self.logger.warning(f"Could not parse last restart time '{last_restart_str}': {e}")
            return True  # If we can't parse the time, allow restart
    
    def create_restart_record(self) -> Dict[str, Any]:
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
