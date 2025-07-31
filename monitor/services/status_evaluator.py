"""
Status Evaluator

Responsible for determining device status based on log data and business rules.
Separated from data models to keep business logic centralized.
"""

from monitor.services.device_status_models import DeviceStatusInfo
from monitor.log_setup import get_logger


class StatusEvaluator:
    """
    Evaluates and determines device status based on business rules.
    
    This class contains all the logic for deciding when a device status
    should change from success to fail or vice versa.
    """
    
    def __init__(self, fail_threshold: int = 200):
        """
        Initialize the status evaluator.
        
        Args:
            fail_threshold: Number of consecutive failures before marking device as failed
        """
        self.logger = get_logger("monitor.services.status_evaluator")
        self.fail_threshold = fail_threshold
        self.logger.info(f"Status evaluator initialized with fail_threshold={fail_threshold}")
    
    def evaluate_status_after_log(self, device_info: DeviceStatusInfo, new_log_status: str) -> DeviceStatusInfo:
        """
        Evaluate what the device status should be after processing a new log entry.
        
        Business Rules:
        1. For new devices: initial status matches first log
        2. Status changes to 'fail' after fail_threshold consecutive 'fail' logs
        3. Status changes to 'success' after any 'success' log (immediate recovery)
        
        Args:
            device_info: Current device status information
            new_log_status: Status from the new log entry ('success' or 'fail')
            
        Returns:
            Updated DeviceStatusInfo with new status determination
        """
        # First update the log tracking information
        updated_info = device_info.update_log_info(new_log_status)
        
        # Determine if status should change based on business rules
        new_status = self._determine_device_status(updated_info)
        
        # Apply status change if needed
        if new_status != updated_info.current_status:
            self.logger.info(f"Device {device_info.device_id} status changing from '{updated_info.current_status}' to '{new_status}' after {updated_info.count} consecutive '{new_log_status}' logs")
            updated_info = updated_info.update_status(new_status)
        else:
            self.logger.debug(f"Device {device_info.device_id}: {new_log_status} count = {updated_info.count} (status: {updated_info.current_status}, threshold: {self.fail_threshold})")
        
        return updated_info
    
    def _determine_device_status(self, device_info: DeviceStatusInfo) -> str:
        """
        Determine what the device status should be based on current log data.
        
        Args:
            device_info: Current device information
            
        Returns:
            The status the device should have ('success' or 'fail')
        """
        # Handle new devices (no current status set)
        if device_info.current_status is None or device_info.current_status == '':
            return device_info.last_log_status
        
        # Business Rule: Immediate recovery on any success
        if device_info.last_log_status == 'success':
            return 'success'
        
        # Business Rule: Fail after threshold consecutive failures
        if device_info.last_log_status == 'fail' and device_info.count >= self.fail_threshold:
            return 'fail'
        
        # Default: keep current status
        return device_info.current_status
    
    def should_status_change(self, device_info: DeviceStatusInfo) -> bool:
        """
        Check if the device status should change based on current data.
        
        Args:
            device_info: Current device information
            
        Returns:
            True if status should change
        """
        determined_status = self._determine_device_status(device_info)
        return determined_status != device_info.current_status
