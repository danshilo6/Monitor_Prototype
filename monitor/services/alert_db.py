"""Alert database for persistent storage of alerts"""

import sqlite3
from typing import List
from datetime import datetime
from monitor.services.alert_models import Alert, AlertType

class AlertDatabase:
    """Database for persistent alert storage"""
    
    def __init__(self, db_file: str = "alerts.db"):
        self.db_file = db_file
        self._init_database()
    
    def _init_database(self):
        """Initialize alerts table"""
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
            return True
        except Exception as e:
            print(f"Failed to add alert: {e}")
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts"""
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
            return alerts
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute('''
                    UPDATE alerts SET resolved = 1 WHERE id = ?
                ''', (alert_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Failed to resolve alert: {e}")
            return False
    
    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts (including resolved ones)"""
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
            return alerts
