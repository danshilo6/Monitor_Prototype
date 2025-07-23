"""Alert database for persistent storage of alerts"""

import sqlite3
import os
from typing import List
from datetime import datetime
from monitor.services.alert_models import Alert, AlertType
from monitor.log_setup import get_logger

class AlertDatabase:
    """Database for persistent alert storage"""
    
    def __init__(self, db_file: str = "data/alerts.db"):
        self.logger = get_logger("monitor.services.alert_db")
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self.logger.info(f"Initializing alert database: {db_file}")
        self._init_database()
        self.logger.debug("Alert database initialized successfully")
    
    def _init_database(self):
        """Initialize alerts table"""
        self.logger.debug("Creating alerts table if it doesn't exist")
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0
                )
            ''')
    
    def add_alert(self, alert: Alert) -> bool:
        """Add new alert (or update existing)"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO alerts 
                    (id, alert_type, description, timestamp, resolved)
                    VALUES (?, ?, ?, ?, 0)
                ''', (alert.id, alert.alert_type.value, alert.description, 
                      alert.timestamp.isoformat()))
            self.logger.info(f"Added alert: {alert.alert_type.value} - {alert.description}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add alert {alert.id}: {e}")
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts"""
        self.logger.debug("Retrieving active alerts from database")
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute('''
                SELECT id, alert_type, description, timestamp
                FROM alerts WHERE resolved = 0
                ORDER BY timestamp DESC
            ''').fetchall()
            
            alerts = []
            for row in rows:
                alert = Alert(
                    id=row[0],
                    alert_type=AlertType(row[1]),
                    description=row[2],
                    timestamp=datetime.fromisoformat(row[3])
                )
                alerts.append(alert)
            self.logger.debug(f"Retrieved {len(alerts)} active alerts")
            return alerts
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute('''
                    UPDATE alerts SET resolved = 1 WHERE id = ?
                ''', (alert_id,))
                if cursor.rowcount > 0:
                    self.logger.info(f"Resolved alert: {alert_id}")
                    return True
                else:
                    self.logger.warning(f"Alert not found for resolution: {alert_id}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts (including resolved ones)"""
        self.logger.debug("Retrieving all alerts (including resolved) from database")
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute('''
                SELECT id, alert_type, description, timestamp
                FROM alerts
                ORDER BY timestamp DESC
            ''').fetchall()
            
            alerts = []
            for row in rows:
                alert = Alert(
                    id=row[0],
                    alert_type=AlertType(row[1]),
                    description=row[2],
                    timestamp=datetime.fromisoformat(row[3])
                )
                alerts.append(alert)
            self.logger.debug(f"Retrieved {len(alerts)} total alerts")
            return alerts
