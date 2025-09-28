"""
RestartDB

Handles SQLite database operations for restart history tracking.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from monitor.log_setup import get_logger


class RestartDB:
    """
    Manages SQLite database for restart history.
    
    Handles:
    - Database initialization and schema creation
    - Adding new restart records
    - Retrieving restart history with limits
    - Maintaining maximum record count (100 restarts)
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the restart history database.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses default location.
        """
        self.logger = get_logger("monitor.core.restart_db")
        
        # Set default database path if not provided
        if db_path is None:
            db_path = Path("data/restart_history.db")
        
        self.db_path = db_path
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        self.logger.debug(f"RestartDB initialized with database: {self.db_path}")
    
    def _init_database(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS restart_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        reason TEXT NOT NULL
                    )
                """)
                
                # Create index for better performance on timestamp queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_restart_timestamp 
                    ON restart_history(timestamp)
                """)
                
                conn.commit()
                self.logger.debug("Database schema initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    def add_restart_record(self, reason: str, timestamp: Optional[datetime] = None) -> bool:
        """
        Add a new restart record to the database.
        
        Args:
            reason: The reason for the restart
            timestamp: When the restart occurred. If None, uses current time.
            
        Returns:
            True if record was added successfully, False otherwise
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            timestamp_str = timestamp.isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Insert new record
                conn.execute(
                    "INSERT INTO restart_history (timestamp, reason) VALUES (?, ?)",
                    (timestamp_str, reason)
                )
                
                # Maintain maximum of 100 records
                self._cleanup_old_records(conn)
                
                conn.commit()
                
            self.logger.info(f"Added restart record: {timestamp_str} - {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add restart record: {e}")
            return False
    
    def _cleanup_old_records(self, conn: sqlite3.Connection, max_records: int = 100) -> None:
        """
        Remove old records to maintain maximum record count.
        
        Args:
            conn: SQLite connection object
            max_records: Maximum number of records to keep (default: 100)
        """
        try:
            # Delete records beyond the limit, keeping the most recent ones
            conn.execute("""
                DELETE FROM restart_history 
                WHERE id NOT IN (
                    SELECT id FROM restart_history 
                    ORDER BY id DESC LIMIT ?
                )
            """, (max_records,))
            
            deleted_count = conn.total_changes
            if deleted_count > 0:
                self.logger.debug(f"Cleaned up {deleted_count} old restart records")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old records: {e}")
    
    def get_restart_history(self, limit: int = 100) -> List[Dict[str, str]]:
        """
        Get restart history records from the database.
        
        Args:
            limit: Maximum number of records to return (default: 100)
            
        Returns:
            List of dictionaries containing timestamp and reason for each restart,
            ordered by most recent first
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
                
                cursor = conn.execute(
                    "SELECT timestamp, reason FROM restart_history ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                
                records = [dict(row) for row in cursor.fetchall()]
                
            self.logger.debug(f"Retrieved {len(records)} restart history records")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to get restart history: {e}")
            return []
    
    def get_restart_count(self) -> int:
        """
        Get the total number of restart records in the database.
        
        Returns:
            Total count of restart records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM restart_history")
                count = cursor.fetchone()[0]
                
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to get restart count: {e}")
            return 0
    
    def get_restart_statistics(self) -> Dict[str, any]:
        """
        Get comprehensive restart statistics.
        
        Returns:
            Dictionary containing various restart statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get total count
                total_cursor = conn.execute("SELECT COUNT(*) as count FROM restart_history")
                total_count = total_cursor.fetchone()['count']
                
                # Get most recent restart
                recent_cursor = conn.execute(
                    "SELECT timestamp, reason FROM restart_history ORDER BY id DESC LIMIT 1"
                )
                recent_restart = recent_cursor.fetchone()
                
                # Get reason counts
                reason_cursor = conn.execute("""
                    SELECT reason, COUNT(*) as count 
                    FROM restart_history 
                    GROUP BY reason 
                    ORDER BY count DESC
                """)
                reason_counts = {row['reason']: row['count'] for row in reason_cursor.fetchall()}
                
                # Get recent restarts (last 24 hours)
                recent_24h_cursor = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM restart_history 
                    WHERE datetime(timestamp) > datetime('now', '-1 day')
                """)
                recent_24h_count = recent_24h_cursor.fetchone()['count']
                
            return {
                'total_restarts': total_count,
                'last_restart': dict(recent_restart) if recent_restart else None,
                'reason_counts': reason_counts,
                'restarts_last_24h': recent_24h_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get restart statistics: {e}")
            return {
                'total_restarts': 0,
                'last_restart': None,
                'reason_counts': {},
                'restarts_last_24h': 0
            }
    
    def clear_history(self) -> bool:
        """
        Clear all restart history records.
        
        Returns:
            True if history was cleared successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM restart_history")
                conn.commit()
                
            self.logger.info("Cleared all restart history records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear restart history: {e}")
            return False
    
    def get_restarts_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, str]]:
        """
        Get restart records within a specific date range.
        
        Args:
            start_date: Start of the date range
            end_date: End of the date range
            
        Returns:
            List of restart records within the date range
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT timestamp, reason 
                    FROM restart_history 
                    WHERE datetime(timestamp) BETWEEN datetime(?) AND datetime(?)
                    ORDER BY timestamp DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                records = [dict(row) for row in cursor.fetchall()]
                
            self.logger.debug(f"Retrieved {len(records)} restart records for date range")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to get restarts by date range: {e}")
            return []
    
    def get_restarts_by_reason(self, reason_filter: str) -> List[Dict[str, str]]:
        """
        Get restart records that match a specific reason (partial match).
        
        Args:
            reason_filter: Reason text to search for (case-insensitive)
            
        Returns:
            List of restart records matching the reason filter
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("""
                    SELECT timestamp, reason 
                    FROM restart_history 
                    WHERE LOWER(reason) LIKE LOWER(?)
                    ORDER BY timestamp DESC
                """, (f"%{reason_filter}%",))
                
                records = [dict(row) for row in cursor.fetchall()]
                
            self.logger.debug(f"Retrieved {len(records)} restart records for reason filter: {reason_filter}")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to get restarts by reason: {e}")
            return []