"""Device status database for persistent storage of device statuses"""

import sqlite3
import os
from typing import Dict, Optional, Tuple
from datetime import datetime
from monitor.log_setup import get_logger
from monitor.services.device_status_models import DeviceStatusInfo


class DeviceStatusDatabase:
    """Database for persistent device status storage"""
    
    def __init__(self, db_file: str = "data/device_status.db"):
        self.logger = get_logger("monitor.services.device_status_db")
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self._conn: sqlite3.Connection | None = None
        self.logger.info(f"Initializing device status database: {db_file}")
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection and create tables"""
        try:
            self._conn = sqlite3.connect(
                self.db_file,
                check_same_thread=False  # Allow multi-threaded access
            )
            self._conn.row_factory = sqlite3.Row
            
            # Check if table exists and what schema it has
            cursor = self._conn.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='device_status'
            ''')
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Check current schema
                cursor = self._conn.execute("PRAGMA table_info(device_status)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Check if we need to migrate to the new simplified schema
                if 'last_log_status' not in columns or 'count' not in columns:
                    self.logger.info("Migrating database schema to simplified format...")
                    self._migrate_to_simplified_schema()
                else:
                    self.logger.info("Database schema is up to date")
            else:
                # Create new table with simplified schema
                self.logger.info("Creating new device status table with simplified schema")
                self._conn.execute('''
                    CREATE TABLE device_status (
                        device_id TEXT PRIMARY KEY,
                        current_status TEXT NOT NULL,
                        last_log_status TEXT NOT NULL,
                        count INTEGER NOT NULL DEFAULT 1,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                self._conn.commit()
                self.logger.info("Device status table created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _migrate_to_simplified_schema(self):
        """Migrate from old complex schema to new simplified schema"""
        try:
            # Create new table with simplified schema
            self._conn.execute('''
                CREATE TABLE device_status_new (
                    device_id TEXT PRIMARY KEY,
                    current_status TEXT NOT NULL,
                    last_log_status TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check what columns exist in the old table
            cursor = self._conn.execute("PRAGMA table_info(device_status)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'success_count' in columns and 'fail_count' in columns:
                # Migrate from success/fail counters schema
                self.logger.info("Migrating from success/fail counters schema...")
                self._conn.execute('''
                    INSERT INTO device_status_new (device_id, current_status, last_log_status, count, last_updated)
                    SELECT device_id, current_status, current_status,
                           CASE WHEN current_status = 'success' THEN success_count ELSE fail_count END,
                           last_updated_at
                    FROM device_status
                ''')
            elif 'consecutive_count' in columns:
                # Migrate from old consecutive_count schema  
                self.logger.info("Migrating from consecutive_count schema...")
                self._conn.execute('''
                    INSERT INTO device_status_new (device_id, current_status, last_log_status, count, last_updated)
                    SELECT device_id, current_status, current_status, consecutive_count, last_updated
                    FROM device_status
                ''')
            else:
                # Unknown schema, start fresh
                self.logger.warning("Unknown schema, starting with empty table")
            
            # Replace old table
            self._conn.execute('DROP TABLE device_status')
            self._conn.execute('ALTER TABLE device_status_new RENAME TO device_status')
            self._conn.commit()
            self.logger.info("Schema migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Schema migration failed: {e}")
            # Rollback if possible
            try:
                self._conn.execute('DROP TABLE IF EXISTS device_status_new')
                self._conn.commit()
            except:
                pass
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None
            self.logger.info("Database connection closed")
    
    def get_device_status(self, device_id: str) -> Optional[DeviceStatusInfo]:
        """
        Get current status for a device
        
        Args:
            device_id: The device identifier
            
        Returns:
            DeviceStatusInfo instance or None if device not found
        """
        try:
            row = self._conn.execute('''
                SELECT current_status, last_log_status, count, last_updated
                FROM device_status 
                WHERE device_id = ?
            ''', (device_id,)).fetchone()
            
            if row:
                last_updated = datetime.fromisoformat(row[3]) if row[3] else datetime.now()
                return DeviceStatusInfo.from_db_tuple(device_id, (row[0], row[1], row[2], last_updated))
            return None
        except Exception as e:
            self.logger.error(f"Failed to get status for device {device_id}: {e}")
            return None
    
    def update_device_status(self, device_status_info: DeviceStatusInfo) -> bool:
        """
        Update device status using a DeviceStatusInfo object
        
        Args:
            device_status_info: DeviceStatusInfo containing all the data to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._conn.execute('''
                INSERT OR REPLACE INTO device_status 
                (device_id, current_status, last_log_status, count, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (device_status_info.device_id, *device_status_info.to_db_tuple()))
            self._conn.commit()
            
            self.logger.debug(f"Updated device {device_status_info.device_id}: status={device_status_info.current_status}, last_log={device_status_info.last_log_status}, count={device_status_info.count}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update status for device {device_status_info.device_id}: {e}")
            return False
    
    def get_all_device_statuses(self) -> Dict[str, DeviceStatusInfo]:
        """
        Get all device statuses
        
        Returns:
            Dictionary mapping device_id to DeviceStatusInfo
        """
        try:
            rows = self._conn.execute('''
                SELECT device_id, current_status, last_log_status, count, last_updated
                FROM device_status
                ORDER BY last_updated DESC
            ''').fetchall()
            
            statuses = {}
            for row in rows:
                device_id = row[0]
                last_updated = datetime.fromisoformat(row[4]) if row[4] else datetime.now()
                status_info = DeviceStatusInfo.from_db_tuple(device_id, (row[1], row[2], row[3], last_updated))
                statuses[device_id] = status_info
            
            return statuses
        except Exception as e:
            self.logger.error(f"Failed to get all device statuses: {e}")
            return {}
    
    def remove_device(self, device_id: str) -> bool:
        """
        Remove a device from the status tracking
        
        Args:
            device_id: The device identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self._conn.execute('''
                DELETE FROM device_status WHERE device_id = ?
            ''', (device_id,))
            
            if cursor.rowcount > 0:
                self._conn.commit()
                self.logger.info(f"Removed device {device_id} from status tracking")
                return True
            else:
                self.logger.warning(f"Device {device_id} not found for removal")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove device {device_id}: {e}")
            return False
    
    def get_devices_with_status(self, status: str) -> Dict[str, DeviceStatusInfo]:
        """
        Get all devices with a specific status
        
        Args:
            status: The status to filter by
            
        Returns:
            Dictionary mapping device_id to DeviceStatusInfo
        """
        try:
            rows = self._conn.execute('''
                SELECT device_id, current_status, last_log_status, count, last_updated
                FROM device_status
                WHERE current_status = ?
                ORDER BY last_updated DESC
            ''', (status,)).fetchall()
            
            devices = {}
            for row in rows:
                device_id = row[0]
                last_updated = datetime.fromisoformat(row[4]) if row[4] else datetime.now()
                status_info = DeviceStatusInfo.from_db_tuple(device_id, (row[1], row[2], row[3], last_updated))
                devices[device_id] = status_info
            
            return devices
        except Exception as e:
            self.logger.error(f"Failed to get devices with status {status}: {e}")
            return {}
