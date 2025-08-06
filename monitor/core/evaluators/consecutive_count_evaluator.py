"""
Evaluator based on consecutive failure count threshold.
"""

from monitor.core.evaluators.base_evaluator import BaseEvaluator
from monitor.services.devices_models import DeviceInfo


class ConsecutiveCountEvaluator(BaseEvaluator):
    """
    Evaluates devices based on consecutive failure count.
    
    Used for devices that should fail after X consecutive failed attempts.
    """
    
    def __init__(self, logger, fail_threshold: int):
        """
        Initialize evaluator.
        
        Args:
            logger: Logger instance
            fail_threshold: Number of consecutive failures before marking as failed
        """
        super().__init__(logger)
        self.fail_threshold = fail_threshold
    
    def evaluate(self, device: DeviceInfo) -> str:
        """
        Evaluate based on consecutive failure count.
        
        Returns device status if above threshold, None otherwise.
        """
        consecutive_count = device.last_log_consecutive_count
        last_status = device.last_log_status
        
        self.logger.debug(f"ConsecutiveCount evaluation for {device.device_id}: "
                         f"count={consecutive_count}, threshold={self.fail_threshold}")
        
        if consecutive_count >= self.fail_threshold:
            return last_status  # Return actual device status
        else:
            return None  # Below threshold
