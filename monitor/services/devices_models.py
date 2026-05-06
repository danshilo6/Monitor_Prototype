"""
Device Data Models

Data class representing device database records.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Optional, Tuple
from enum import Enum
import json


class DeviceType(Enum):
    """Enumeration of supported device types from log entries."""
    GROUP = "group"
    FAN = "fan" 
    SPRINKLER = "sprinkler"
    CAMERA = "camera"
    COMPORT = "comport"
    THREAD = "thread"
    THI = "THI_sensor"
    CONVERTER = "converter"
    UNKNOWN = "unknown"  # Fallback for unrecognized types
    
    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


@dataclass
class DeviceInfo:
    """
    Represents a device status record from the database.
    
    This data class makes it easier to work with device status data
    instead of using tuples with manual index handling.
    
    Database schema:
    - device_id: The device identifier
    - device_type: The type of device (camera, sprinkler, fan, etc.)
    - status: The current reported status ('success' or 'fail') 
    - last_log_status: The status from the most recent log entry
    - last_log_consecutive_count: Number of consecutive occurrences of last_log_status
    - success_count: Number of 'S' entries in recent_pattern
    - fail_count: Number of 'F' entries in recent_pattern
    - recent_pattern: String pattern of recent statuses (e.g., "SFSFSF" where S=success, F=fail)
    - last_updated: When this record was last updated
    """
    device_id: str
    device_type: str  # DeviceType as string
    status: str  # 'success' or 'fail' - what we report as device status
    last_log_status: str  # 'success' or 'fail' - what the last log entry said
    last_log_consecutive_count: int  # consecutive count of last_log_status
    success_count: int = 0  # Count of 'S' in recent_pattern
    fail_count: int = 0  # Count of 'F' in recent_pattern
    recent_pattern: str = ""  # Pattern like "SFSFSF" for recent statuses
    last_updated: datetime = field(default_factory=datetime.now)

    def add_status_to_history(self, new_status: str, max_history: int = 20) -> 'DeviceInfo':
        """
        Add a new status to the recent history pattern.
        
        Args:
            new_status: 'success' or 'fail'
            max_history: Maximum number of recent statuses to track
            
        Returns:
            New DeviceInfo instance with updated history
        """
        # Convert status to single character
        status_char = 'S' if new_status == 'success' else 'F'
        
        # Add to pattern
        new_pattern = self.recent_pattern + status_char
        
        # Trim to max_history if needed
        if len(new_pattern) > max_history:
            # Remove the oldest (leftmost) character
            removed_char = new_pattern[0]
            new_pattern = new_pattern[1:]
            
            # Update counts - subtract the removed character
            new_success_count = self.success_count
            new_fail_count = self.fail_count
            
            if removed_char == 'S':
                new_success_count -= 1
            else:
                new_fail_count -= 1
        else:
            new_success_count = self.success_count
            new_fail_count = self.fail_count
        
        # Add the new character to counts
        if status_char == 'S':
            new_success_count += 1
        else:
            new_fail_count += 1
        
        # Create new instance with updated values
        return replace(
            self,
            last_log_status=new_status,
            last_updated=datetime.now(),
            recent_pattern=new_pattern,
            success_count=new_success_count,
            fail_count=new_fail_count
        )
    
    def get_success_rate(self) -> float:
        """
        Calculate the success rate from recent history.
        
        Returns:
            Success rate as a float between 0.0 and 1.0
        """
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def get_failure_rate(self) -> float:
        """
        Calculate the failure rate from recent history.
        
        Returns:
            Failure rate as a float between 0.0 and 1.0
        """
        return 1.0 - self.get_success_rate()
    
    def get_recent_status_counts(self) -> Tuple[int, int]:
        """
        Get the counts of success and fail statuses in recent history.
        
        Returns:
            Tuple of (success_count, fail_count)
        """
        return (self.success_count, self.fail_count)
    
    


    

