"""
Device Status Data Models

Data class representing device status database records.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DeviceStatusInfo:
    """
    Represents a device status record from the database.
    
    This data class makes it easier to work with device status data
    instead of using tuples with manual index handling.
    
    Database schema:
    - device_id: The device identifier
    - current_status: The current reported status ('success' or 'fail') 
    - last_log_status: The status from the most recent log entry
    - count: Number of consecutive occurrences of last_log_status
    - last_updated: When this record was last updated
    """
    device_id: str
    current_status: str  # 'success' or 'fail' - what we report as device status
    last_log_status: str  # 'success' or 'fail' - what the last log entry said
    count: int  # consecutive count of last_log_status
    last_updated: datetime
    
    @classmethod
    def from_db_tuple(cls, device_id: str, row_data: tuple) -> 'DeviceStatusInfo':
        """
        Create a DeviceStatusInfo instance from database row data.
        
        Args:
            device_id: The device identifier
            row_data: Tuple containing (current_status, last_log_status, count, last_updated)
            
        Returns:
            DeviceStatusInfo instance
        """
        current_status, last_log_status, count, last_updated = row_data
        return cls(
            device_id=device_id,
            current_status=current_status,
            last_log_status=last_log_status,
            count=count,
            last_updated=last_updated
        )
    
    def to_db_tuple(self) -> tuple:
        """
        Convert to tuple format for database operations (excluding device_id).
        
        Returns:
            Tuple of (current_status, last_log_status, count, last_updated)
        """
        return (self.current_status, self.last_log_status, self.count, self.last_updated)
    
    def update_log_info(self, new_log_status: str) -> 'DeviceStatusInfo':
        """
        Update log-related information after processing a new log entry.
        Does NOT determine device status - only tracks log counts.
        
        Args:
            new_log_status: Status from the new log entry ('success' or 'fail')
            
        Returns:
            New DeviceStatusInfo instance with updated log tracking
        """
        if new_log_status == self.last_log_status:
            # Same status as before: increment count
            new_count = self.count + 1
        else:
            # Different status: reset count to 1
            new_count = 1
        
        return DeviceStatusInfo(
            device_id=self.device_id,
            current_status=self.current_status,  # Keep existing status unchanged
            last_log_status=new_log_status,
            count=new_count,
            last_updated=datetime.now()
        )
    
    def update_status(self, new_status: str) -> 'DeviceStatusInfo':
        """
        Update the current device status.
        This should only be called by the status evaluation logic.
        
        Args:
            new_status: The new device status to set
            
        Returns:
            New DeviceStatusInfo instance with updated status
        """
        return DeviceStatusInfo(
            device_id=self.device_id,
            current_status=new_status,
            last_log_status=self.last_log_status,
            count=self.count,
            last_updated=datetime.now()
        )
