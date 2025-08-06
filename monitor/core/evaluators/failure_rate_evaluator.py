"""
Evaluator based on failure rate percentage.
"""

from monitor.core.evaluators.base_evaluator import BaseEvaluator
from monitor.services.devices_models import DeviceInfo


class FailureRateEvaluator(BaseEvaluator):
    """
    Evaluates devices based on failure rate percentage.
    
    Used for devices that should fail if failure rate exceeds threshold.
    """
    
    def __init__(self, logger, failure_rate_threshold: float):
        """
        Initialize evaluator.
        
        Args:
            logger: Logger instance
            failure_rate_threshold: Failure rate (0.0-1.0) before marking as failed
        """
        super().__init__(logger)
        self.failure_rate_threshold = failure_rate_threshold
    
    def evaluate(self, device: DeviceInfo) -> str:
        """
        Evaluate based on failure rate.
        
        Returns 'fail' if above threshold, 'success' otherwise.
        """
        failure_rate = device.get_failure_rate()
        
        self.logger.debug(f"FailureRate evaluation for {device.device_id}: "
                         f"rate={failure_rate}, threshold={self.failure_rate_threshold}")
        
        if failure_rate >= self.failure_rate_threshold:
            return 'fail'
        else:
            return 'success'
