"""Devices database for persistent storage of device statuses"""

import sqlite3
import os
from typing import Dict, Optional, Tuple
from datetime import datetime
from monitor.log_setup import get_logger
from monitor.services.devices_models import DeviceInfo


class DevicesDatabase:
    """Database for persistent device storage"""
    
    def __init__(self, db_file: str = "data/devices.db"):
        self.logger = get_logger("monitor.services.devices_db")
        # Ensure data directory exists (but not for special paths like :memory:)
        if db_file != ":memory:" and os.path.dirname(db_file):
            os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self._conn: sqlite3.Connection | None = None
        self.logger.info(f"Initializing devices database: {db_file}")
        self._init_database()
    
    def __del__(self):
        """Ensure connection is closed when object is destroyed"""
        self.close()
    
    def _init_database(self):
        """Initialize database connection and create tables"""
        # Close any existing connection first
        if self._conn:
            try:
                self._conn.close()
            except:
                pass  # Ignore errors when closing old connection
            self._conn = None
            
        try:
            self._conn = sqlite3.connect(
                self.db_file,
                check_same_thread=False  # Allow multi-threaded access
            )
            self._conn.row_factory = sqlite3.Row
            
            # Check if table exists and what schema it has
            cursor = self._conn.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='devices'
            ''')
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Check current schema
                cursor = self._conn.execute("PRAGMA table_info(devices)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Check if we need to migrate to the new schema
                required_columns = ['device_id', 'device_type', 'status', 'last_log_status', 
                                  'last_log_consecutive_count', 'success_count', 'fail_count', 'recent_pattern']
                if not all(col in columns for col in required_columns):
                    self.logger.info("Migrating database schema to new format...")
                    self._migrate_to_new_schema()
                else:
                    self.logger.info("Database schema is up to date")
            else:
                # Create new table with new schema
                self.logger.info("Creating new devices table with new schema")
                self._conn.execute('''
                    CREATE TABLE devices (
                        device_id TEXT PRIMARY KEY,
                        device_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        last_log_status TEXT NOT NULL,
                        last_log_consecutive_count INTEGER NOT NULL DEFAULT 1,
                        success_count INTEGER NOT NULL DEFAULT 0,
                        fail_count INTEGER NOT NULL DEFAULT 0,
                        recent_pattern TEXT NOT NULL DEFAULT '',
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                self._conn.commit()
                self.logger.info("Devices table created successfully")
                
        except Exception as e:
            # Clean up partial connection on failure
            if self._conn:
                try:
                    self._conn.close()
                except:
                    pass
                self._conn = None
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _migrate_to_new_schema(self):
        """Migrate from old schema to new schema with device_type and history tracking"""
        try:
            # Create new table with new schema
            self._conn.execute('''
                CREATE TABLE devices_new (
                    device_id TEXT PRIMARY KEY,
                    device_type TEXT NOT NULL DEFAULT 'unknown',
                    status TEXT NOT NULL,
                    last_log_status TEXT NOT NULL,
                    last_log_consecutive_count INTEGER NOT NULL DEFAULT 1,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    recent_pattern TEXT NOT NULL DEFAULT '',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check what columns exist in the old table
            cursor = self._conn.execute("PRAGMA table_info(device_status)")
            old_columns = [row[1] for row in cursor.fetchall()]
            
            # Migrate data from old table if it exists
            if 'device_id' in old_columns:
                self.logger.info("Migrating data from old device_status table...")
                
                # Map old column names to new ones
                if 'current_status' in old_columns:
                    status_col = 'current_status'
                else:
                    status_col = 'status'
                
                if 'count' in old_columns:
                    count_col = 'count'
                elif 'last_log_consecutive_count' in old_columns:
                    count_col = 'last_log_consecutive_count'
                else:
                    count_col = '1'  # Default value
                
                self._conn.execute(f'''
                    INSERT INTO devices_new 
                    (device_id, device_type, status, last_log_status, last_log_consecutive_count, 
                     success_count, fail_count, recent_pattern, last_updated)
                    SELECT 
                        device_id,
                        'unknown' as device_type,
                        {status_col} as status,
                        COALESCE(last_log_status, {status_col}) as last_log_status,
                        COALESCE({count_col}, 1) as last_log_consecutive_count,
                        0 as success_count,
                        0 as fail_count,
                        '' as recent_pattern,
                        COALESCE(last_updated, CURRENT_TIMESTAMP) as last_updated
                    FROM device_status
                ''')
            else:
                self.logger.warning("Old table has unknown schema, starting with empty table")
            
            # Replace old table
            self._conn.execute('DROP TABLE IF EXISTS device_status')
            self._conn.execute('ALTER TABLE devices_new RENAME TO devices')
            self._conn.commit()
            self.logger.info("Schema migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Schema migration failed: {e}")
            # Rollback if possible
            try:
                self._conn.execute('DROP TABLE IF EXISTS devices_new')
                self._conn.commit()
            except:
                pass
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        if self._conn is None:
            self.logger.info("Reconnecting to database...")
            self._init_database()
        else:
            # Test if connection is still valid
            try:
                self._conn.execute("SELECT 1").fetchone()
            except (sqlite3.Error, sqlite3.OperationalError):
                self.logger.warning("Database connection is invalid, reconnecting...")
                self.close()  # Properly close the invalid connection
                self._init_database()
    
    def close(self):
        """Close database connection"""
        if self._conn:
            try:
                # Ensure all transactions are committed before closing
                self._conn.commit()
                self._conn.close()
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")
            finally:
                self._conn = None
                self.logger.info("Database connection closed")
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """
        Get current status for a device
        
        Args:
            device_id: The device identifier
            
        Returns:
            DeviceInfo instance or None if device not found
        """
        self._ensure_connection()
        try:
            row = self._conn.execute('''
                SELECT device_type, status, last_log_status, last_log_consecutive_count, 
                       success_count, fail_count, recent_pattern, last_updated
                FROM devices 
                WHERE device_id = ?
            ''', (device_id,)).fetchone()
            
            if row:
                last_updated = datetime.fromisoformat(row[7]) if row[7] else datetime.now()
                return DeviceInfo(
                    device_id=device_id,
                    device_type=row[0],
                    status=row[1],
                    last_log_status=row[2],
                    last_log_consecutive_count=row[3],
                    success_count=row[4],
                    fail_count=row[5],
                    recent_pattern=row[6],
                    last_updated=last_updated
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get status for device {device_id}: {e}")
            return None
    
    def update_device(self, device_info: DeviceInfo) -> bool:
        """
        Update device status using a DeviceInfo object
        
        Args:
            device_info: DeviceInfo containing all the data to update
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connection()
        try:
            self._conn.execute('''
                INSERT OR REPLACE INTO devices 
                (device_id, device_type, status, last_log_status, last_log_consecutive_count,
                 success_count, fail_count, recent_pattern, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_info.device_id,
                device_info.device_type,
                device_info.status,
                device_info.last_log_status,
                device_info.last_log_consecutive_count,
                device_info.success_count,
                device_info.fail_count,
                device_info.recent_pattern,
                device_info.last_updated.isoformat()
            ))
            self._conn.commit()
            
            self.logger.debug(f"Updated device {device_info.device_id}: status={device_info.status}, "
                            f"last_log={device_info.last_log_status}, count={device_info.last_log_consecutive_count}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update status for device {device_info.device_id}: {e}")
            return False
    
    def get_all(self) -> Dict[str, DeviceInfo]:
        """
        Get all device statuses
        
        Returns:
            Dictionary mapping device_id to DeviceInfo
        """
        self._ensure_connection()
        try:
            rows = self._conn.execute('''
                SELECT device_id, device_type, status, last_log_status, last_log_consecutive_count,
                       success_count, fail_count, recent_pattern, last_updated
                FROM devices
                ORDER BY last_updated DESC
            ''').fetchall()
            
            statuses = {}
            for row in rows:
                device_id = row[0]
                last_updated = datetime.fromisoformat(row[8]) if row[8] else datetime.now()
                status_info = DeviceInfo(
                    device_id=device_id,
                    device_type=row[1],
                    status=row[2],
                    last_log_status=row[3],
                    last_log_consecutive_count=row[4],
                    success_count=row[5],
                    fail_count=row[6],
                    recent_pattern=row[7],
                    last_updated=last_updated
                )
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
        self._ensure_connection()
        try:
            cursor = self._conn.execute('''
                DELETE FROM devices WHERE device_id = ?
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
    
    def get_by_status(self, status: str) -> Dict[str, DeviceInfo]:
        """
        Get all devices with a specific status
        
        Args:
            status: The status to filter by
            
        Returns:
            Dictionary mapping device_id to DeviceInfo
        """
        self._ensure_connection()
        try:
            rows = self._conn.execute('''
                SELECT device_id, device_type, status, last_log_status, last_log_consecutive_count,
                       success_count, fail_count, recent_pattern, last_updated
                FROM devices
                WHERE status = ?
                ORDER BY last_updated DESC
            ''', (status,)).fetchall()
            
            devices = {}
            for row in rows:
                device_id = row[0]
                last_updated = datetime.fromisoformat(row[8]) if row[8] else datetime.now()
                status_info = DeviceInfo(
                    device_id=device_id,
                    device_type=row[1],
                    status=row[2],
                    last_log_status=row[3],
                    last_log_consecutive_count=row[4],
                    success_count=row[5],
                    fail_count=row[6],
                    recent_pattern=row[7],
                    last_updated=last_updated
                )
                devices[device_id] = status_info
            
            return devices
        except Exception as e:
            self.logger.error(f"Failed to get devices with status {status}: {e}")
            return {}
    
    def print_devices(self, title: str = "Devices Database") -> None:
        """
        Print all devices in a formatted table
        
        Args:
            title: Optional title for the output
        """
        self._ensure_connection()
        devices = self.get_all()
        
        if not devices:
            print(f"\n=== {title} ===")
            print("No devices found in database")
            return
        
        # Calculate column widths for nice formatting
        max_id_width = max(len(device_id) for device_id in devices.keys())
        max_id_width = max(max_id_width, len("Device ID"))
        max_type_width = max(len(device.device_type) for device in devices.values())
        max_type_width = max(max_type_width, len("Type"))
        
        # Print header
        print(f"\n=== {title} ===")
        print(f"Total devices: {len(devices)}")
        print()
        
        # Print table header
        header = f"{'Device ID':<{max_id_width}} | {'Type':<{max_type_width}} | {'Status':<7} | {'Consec':<6} | {'S/F':<7} | {'Pattern':<10} | {'Last Updated'}"
        print(header)
        print("-" * len(header))
        
        # Print device rows sorted by last updated (most recent first)
        for device_id, device in devices.items():
            # Format success/fail counts
            sf_count = f"{device.success_count}/{device.fail_count}"
            
            # Truncate pattern if too long
            pattern = device.recent_pattern[:10] if device.recent_pattern else ""
            
            # Format timestamp
            time_str = device.last_updated.strftime("%H:%M:%S") if device.last_updated else "Unknown"
            
            # Color coding for status (if terminal supports it)
            status_display = device.status
            
            row = (f"{device_id:<{max_id_width}} | "
                   f"{device.device_type:<{max_type_width}} | "
                   f"{status_display:<7} | "
                   f"{device.last_log_consecutive_count:<6} | "
                   f"{sf_count:<7} | "
                   f"{pattern:<10} | "
                   f"{time_str}")
            print(row)
        
        # Print summary statistics
        success_count = sum(1 for d in devices.values() if d.status == "success")
        fail_count = sum(1 for d in devices.values() if d.status == "fail")
        device_types = set(d.device_type for d in devices.values())
        
        print()
        print(f"Summary: {success_count} success, {fail_count} fail")
        print(f"Device types: {', '.join(sorted(device_types))}")
        print()
    
    def reset_database(self) -> bool:
        """
        Reset the devices database by clearing all devices
        
        This is useful for manual testing and starting fresh.
        
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connection()
        try:
            # Count devices before reset for logging
            device_count = len(self.get_all())
            
            # Clear all devices from the table
            self._conn.execute('DELETE FROM devices')
            self._conn.commit()
            
            self.logger.info(f"Database reset successful. Removed {device_count} devices")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            return False
