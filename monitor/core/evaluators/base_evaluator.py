"""
Base evaluator class that defines the interface for all device evaluators.
"""

from abc import ABC, abstractmethod
from monitor.services.devices_models import DeviceInfo


class BaseEvaluator(ABC):
    """
    Abstract base class for device evaluators.
    
    Each evaluator implements a specific decision logic pattern.
    """
    
    def __init__(self, logger):
        """Initialize with a logger."""
        self.logger = logger
    
    @abstractmethod
    def evaluate(self, device: DeviceInfo) -> str:
        """
        Evaluate a device and return its status.
        
        Returns:
            Status string ('fail', 'success') or None if no change needed
        """
        pass
