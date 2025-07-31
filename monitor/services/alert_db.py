"""Alert database for persistent storage of alerts"""

import sqlite3
import os
from typing import List
from datetime import datetime
from PySide6.QtCore import QObject, Signal
from monitor.services.alert_models import Alert, AlertType
from monitor.log_setup import get_logger
# TODO: REMOVE TEST CODE BEFORE PRODUCTION - Start
import threading
import time
import random
# TODO: REMOVE TEST CODE BEFORE PRODUCTION - End

class AlertDatabase(QObject):
    """Database for persistent alert storage"""
    
    # Signals for real-time updates
    alert_added = Signal(Alert)
    alert_resolved = Signal(str)  # alert_id
    alerts_loaded = Signal(list)  # List[Alert]
    
    def __init__(self, db_file: str = "data/alerts.db"):
        super().__init__()
        self.logger = get_logger("monitor.services.alert_db")
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self.logger.info(f"Initializing alert database: {db_file}")
        self._init_database()
        
        # TODO: REMOVE TEST CODE BEFORE PRODUCTION - Start
        # Test thread control
        self._test_thread = None
        self._stop_test = False
        # TODO: REMOVE TEST CODE BEFORE PRODUCTION - End
    
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
            self.logger.info(f"Added alert: {alert.alert_type.value} - {alert.description}")
            self.alert_added.emit(alert)  # Emit signal
            return True
        except Exception as e:
            self.logger.error(f"Failed to add alert {alert.id}: {e}")
            return False
    
    # TODO: REMOVE TEST CODE BEFORE PRODUCTION - Start
    def start_threaded_test_alerts(self, interval_seconds: float = 2.0):
        """Start generating test alerts from background thread"""
        if self._test_thread and self._test_thread.is_alive():
            self.logger.warning("Test thread already running")
            return
            
        self._stop_test = False
        self._test_thread = threading.Thread(
            target=self._threaded_alert_generator,
            args=(interval_seconds,),
            daemon=True  # Dies when main program exits
        )
        self._test_thread.start()
        self.logger.info(f"Started threaded test alerts (interval: {interval_seconds}s)")

    def stop_threaded_test_alerts(self):
        """Stop the background test thread"""
        self._stop_test = True
        if self._test_thread:
            self._test_thread.join(timeout=1.0)  # Wait max 1 second
        self.logger.info("Stopped threaded test alerts")

    def _threaded_alert_generator(self, interval: float):
        """Background thread that generates test alerts"""
        counter = 0
        
        while not self._stop_test:
            counter += 1
            alert_type = random.choice(list(AlertType))
            
            # Generate alert data based on type (from your dummy logic)
            if alert_type == AlertType.SPRINKLER:
                letter = chr(65 + random.randint(0, 25))
                group = random.randint(1, 5)
                sprinkler_number = random.randint(1, 4)
                description = f"{letter}{group} - {sprinkler_number}"
            elif alert_type == AlertType.FAN:
                group = random.randint(1, 5)
                description = f"AY{group} - 1, 2, 3, 4"
            elif alert_type == AlertType.CAMERA:
                ip = f"192.168.1.{202 + random.randint(0, 8)}"
                description = ip
            else:  # SOFTWARE
                description = "error"
            
            # Create alert (this runs in background thread)
            test_alert = Alert(
                id=f"thread-test-{counter}",
                alert_type=alert_type,
                description=description,
                timestamp=datetime.now()
            )
            
            # Add to database (this method handles thread-safety via signals)
            self.add_alert(test_alert)
            
            time.sleep(interval)
    # TODO: REMOVE TEST CODE BEFORE PRODUCTION - End
    
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
            self.alerts_loaded.emit(alerts)  # Emit signal
            return alerts
    
    def load_alerts(self):
        """Load active alerts and emit signal (signal-based interface)"""
        alerts = self.get_active_alerts()
        
        # Generate dummy data if needed (remove later)
        if not alerts:
            from monitor.services.alert_models import generate_dummy_alerts
            self.logger.info("No alerts found, generating dummy data")
            dummy_alerts = generate_dummy_alerts()
            for alert in dummy_alerts:
                self.add_alert(alert)
            # Get the alerts again after adding dummy data
            self.get_active_alerts()
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute('''
                    UPDATE alerts SET resolved = 1 WHERE id = ?
                ''', (alert_id,))
                if cursor.rowcount > 0:
                    self.logger.info(f"Resolved alert: {alert_id}")
                    self.alert_resolved.emit(alert_id)  # Emit signal
                    return True
                else:
                    self.logger.warning(f"Alert not found for resolution: {alert_id}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
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
