"""
DeviceStatusManager

Handles device status persistence and tracking.
"""

import json
from datetime import datetime
from pathlib import Path
from monitor.log_setup import get_logger
from monitor.utils.path_utils import get_data_path
from monitor.services.devices_models import DeviceType


class DeviceStatusManager:
    """
    Manages device status persistence and tracking.
    
    This class handles:
    - Loading/saving device statuses to JSON file
    - Tracking device status changes
    - Managing restart information
    """
    
    def __init__(self):
        """Initialize the device status manager."""
        self.logger = get_logger("monitor.core.device_status_manager")
        
        # Device status tracking (persistent)
        self._device_statuses = {}  # {device_id: {'status': str, 'timestamp': str, 'type': str}}
        self._restart_info = {}  # {'last_restart_time': str, 'restart_count': int}
        self._status_file = Path(get_data_path("decision_engine_statuses.json"))
        
        # Load existing statuses
        self._load_device_statuses()
        
        self.logger.debug("DeviceStatusManager initialized")
    
    @staticmethod
    def _get_status_file_path() -> Path:
        """Get path to the decision engine status file."""
        return Path(get_data_path("decision_engine_statuses.json"))
    
    def _load_device_statuses(self) -> None:
        """Load device statuses from JSON file."""
        try:
            if self._status_file.exists():
                with open(self._status_file, 'r') as f:
                    data = json.load(f)
                
                # Handle both old format (just device statuses) and new format (with restart info)
                if isinstance(data, dict) and 'devices' in data:
                    # New format: {"devices": {...}, "restart_info": {...}}
                    self._device_statuses = data.get('devices', {})
                    self._restart_info = data.get('restart_info', {})
                else:
                    # Old format: just device statuses
                    self._device_statuses = data
                    self._restart_info = {}
                
                self.logger.debug(f"Loaded {len(self._device_statuses)} device statuses from file")
            else:
                self.logger.debug("No existing status file found, starting with empty statuses")
                self._device_statuses = {}
                self._restart_info = {}
        except Exception as e:
            self.logger.warning(f"Could not load device statuses: {e}")
            self._device_statuses = {}
            self._restart_info = {}
    
    def _save_device_statuses(self) -> None:
        """Save device statuses and restart info to JSON file."""
        try:
            # Ensure data directory exists
            self._status_file.parent.mkdir(exist_ok=True)
            
            # Save in new format with both device statuses and restart info
            data = {
                'devices': self._device_statuses,
                'restart_info': self._restart_info
            }
            
            with open(self._status_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"Saved {len(self._device_statuses)} device statuses and restart info to file")
        except Exception as e:
            self.logger.warning(f"Could not save device statuses: {e}")
    
    def get_device_status(self, device_id: str) -> str:
        """Get the current status for a device, returns 'success' if not found (new device)."""
        device_info = self._device_statuses.get(device_id, {})
        return device_info.get('status', 'success')
    
    def update_device_status(self, device_id: str, status: str, device_type: str, timestamp: datetime) -> None:
        """Update device status with timestamp and type information."""
        self._device_statuses[device_id] = {
            'status': status,
            'timestamp': timestamp.isoformat(),
            'type': device_type
        }
        self._save_device_statuses()
    
    def ensure_device_tracked(self, device_id: str, device_type: str, timestamp: datetime) -> bool:
        """
        Ensure device is tracked in the json file.
        
        Returns:
            True if this is a new device, False if already tracked
        """
        if device_id not in self._device_statuses:
            self.update_device_status(device_id, 'success', device_type, timestamp)
            return True  # New device
        return False  # Already tracked
    
    def get_device_statuses(self) -> dict:
        """Get a copy of all device statuses."""
        return self._device_statuses.copy()
    
    def get_threads_status(self) -> dict:
        """Get all threads id's and status that are currently in the device status json file"""
        threads = {}
        for device_id, device_info in self._device_statuses.items():
            if device_info.get('type') == DeviceType.THREAD.value:
                threads[device_id] = device_info.get('status', 'unknown')
        return threads

    def comport_failed(self) -> bool:
        """Check if any COM port device has a 'fail' status"""
        for device_id, device_info in self._device_statuses.items():
            if (device_info.get('type') == DeviceType.COMPORT.value and 
                device_info.get('status') == 'fail'):
                return True
        return False

    def get_comport_status(self) -> str:
        """Get the status of the first COM port device found, or 'none' if no comport exists"""
        for device_id, device_info in self._device_statuses.items():
            if device_info.get('type') == DeviceType.COMPORT.value:
                return device_info.get('status', 'unknown')
        return 'none'

    def get_restart_info(self) -> dict:
        """Get a copy of restart information."""
        return self._restart_info.copy()
    
    def update_restart_info(self, restart_info: dict) -> None:
        """Update restart information and save to file."""
        self._restart_info = restart_info
        self._save_device_statuses()
    
    @staticmethod
    def reset_statuses() -> None:
        """Reset device statuses (for testing)."""
        try:
            status_file = DeviceStatusManager._get_status_file_path()
            if status_file.exists():
                status_file.unlink()
                print(f"Device statuses reset: {status_file}")
            else:
                print("No status file found to reset")
        except Exception as e:
            print(f"Error resetting statuses: {e}")
