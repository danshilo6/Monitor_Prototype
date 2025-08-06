"""
Evaluator based on time since last activity.
"""

from datetime import datetime, timedelta
from monitor.core.evaluators.base_evaluator import BaseEvaluator
from monitor.services.devices_models import DeviceInfo


class TimeoutEvaluator(BaseEvaluator):
    """
    Evaluates devices based on timeout since last activity.
    
    Used for devices that should fail if inactive for too long.
    """
    
    def __init__(self, logger, timeout_minutes: int):
        """
        Initialize evaluator.
        
        Args:
            logger: Logger instance
            timeout_minutes: Minutes before device times out
        """
        super().__init__(logger)
        self.timeout_minutes = timeout_minutes
    
    def evaluate(self, device: DeviceInfo) -> str:
        """
        Evaluate based on time since last activity.
        
        Returns 'fail' if timed out, 'success' if active.
        """
        time_since_update = datetime.now() - device.last_updated
        timeout_threshold = timedelta(minutes=self.timeout_minutes)
        
        self.logger.debug(f"Timeout evaluation for {device.device_id}: "
                         f"inactive_time={time_since_update}, threshold={timeout_threshold}")
        
        return 'fail' if time_since_update >= timeout_threshold else 'success'
