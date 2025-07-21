"""Tests for AlertDatabase functionality"""

import unittest
import tempfile
import os
from datetime import datetime
from monitor.services.alert_db import AlertDatabase
from monitor.services.alert_models import Alert, AlertType, generate_dummy_alerts


class TestAlertDatabase(unittest.TestCase):
    """Test cases for AlertDatabase"""

    def setUp(self):
        """Set up test database with temporary file"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)  # Close file descriptor, we only need the path
        self.alert_db = AlertDatabase(db_file=self.test_db_path)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_database_initialization(self):
        """Test that database is properly initialized"""
        # Database should be created and accessible
        self.assertTrue(os.path.exists(self.test_db_path))
        
        # Should be able to get empty alerts list
        alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(alerts), 0)

    def test_add_alert(self):
        """Test adding an alert to the database"""
        alert = Alert(
            id="test_1",
            alert_type=AlertType.SPRINKLER,
            description="Test sprinkler alert",
            timestamp=datetime.now()
        )
        
        # Add alert should succeed
        result = self.alert_db.add_alert(alert)
        self.assertTrue(result)
        
        # Alert should be retrievable
        alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].id, "test_1")
        self.assertEqual(alerts[0].alert_type, AlertType.SPRINKLER)
        self.assertEqual(alerts[0].description, "Test sprinkler alert")

    def test_add_duplicate_alert(self):
        """Test that adding duplicate alert updates existing one"""
        alert1 = Alert(
            id="duplicate_test",
            alert_type=AlertType.FAN,
            description="Original description",
            timestamp=datetime.now()
        )
        
        alert2 = Alert(
            id="duplicate_test",  # Same ID
            alert_type=AlertType.CAMERA,
            description="Updated description",
            timestamp=datetime.now()
        )
        
        # Add first alert
        self.alert_db.add_alert(alert1)
        
        # Add second alert with same ID
        self.alert_db.add_alert(alert2)
        
        # Should only have one alert with updated information
        alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.CAMERA)
        self.assertEqual(alerts[0].description, "Updated description")

    def test_resolve_alert(self):
        """Test resolving an alert"""
        alert = Alert(
            id="resolve_test",
            alert_type=AlertType.SOFTWARE,
            description="Test software alert",
            timestamp=datetime.now()
        )
        
        # Add alert
        self.alert_db.add_alert(alert)
        
        # Verify it's active
        active_alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
        
        # Resolve the alert
        result = self.alert_db.resolve_alert("resolve_test")
        self.assertTrue(result)
        
        # Should no longer be in active alerts
        active_alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(active_alerts), 0)
        
        # But should still be in all alerts
        all_alerts = self.alert_db.get_all_alerts()
        self.assertEqual(len(all_alerts), 1)

    def test_resolve_nonexistent_alert(self):
        """Test resolving an alert that doesn't exist"""
        result = self.alert_db.resolve_alert("nonexistent_id")
        self.assertFalse(result)

    def test_multiple_alert_types(self):
        """Test adding and retrieving multiple alert types"""
        alerts = [
            Alert("sprinkler_1", AlertType.SPRINKLER, "A1 - 1", datetime.now()),
            Alert("fan_1", AlertType.FAN, "AY2 - 1,2,3,4", datetime.now()),
            Alert("camera_1", AlertType.CAMERA, "192.168.1.202", datetime.now()),
            Alert("software_1", AlertType.SOFTWARE, "error", datetime.now()),
        ]
        
        # Add all alerts
        for alert in alerts:
            result = self.alert_db.add_alert(alert)
            self.assertTrue(result)
        
        # Verify all are retrieved
        active_alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(active_alerts), 4)
        
        # Verify alert types are preserved
        alert_types = {alert.alert_type for alert in active_alerts}
        expected_types = {AlertType.SPRINKLER, AlertType.FAN, AlertType.CAMERA, AlertType.SOFTWARE}
        self.assertEqual(alert_types, expected_types)

    def test_get_all_alerts_includes_resolved(self):
        """Test that get_all_alerts includes both active and resolved alerts"""
        # Add two alerts
        alert1 = Alert("test_1", AlertType.SPRINKLER, "Test 1", datetime.now())
        alert2 = Alert("test_2", AlertType.FAN, "Test 2", datetime.now())
        
        self.alert_db.add_alert(alert1)
        self.alert_db.add_alert(alert2)
        
        # Resolve one alert
        self.alert_db.resolve_alert("test_1")
        
        # Active alerts should have only one
        active_alerts = self.alert_db.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(active_alerts[0].id, "test_2")
        
        # All alerts should have both
        all_alerts = self.alert_db.get_all_alerts()
        self.assertEqual(len(all_alerts), 2)


class TestAlertModels(unittest.TestCase):
    """Test cases for Alert models"""

    def test_alert_creation(self):
        """Test creating Alert objects"""
        timestamp = datetime.now()
        alert = Alert(
            id="test_alert",
            alert_type=AlertType.SPRINKLER,
            description="Test description",
            timestamp=timestamp
        )
        
        self.assertEqual(alert.id, "test_alert")
        self.assertEqual(alert.alert_type, AlertType.SPRINKLER)
        self.assertEqual(alert.description, "Test description")
        self.assertEqual(alert.timestamp, timestamp)

    def test_alert_type_enum(self):
        """Test AlertType enum values"""
        self.assertEqual(AlertType.SPRINKLER.value, "sprinkler")
        self.assertEqual(AlertType.FAN.value, "fan")
        self.assertEqual(AlertType.CAMERA.value, "camera")
        self.assertEqual(AlertType.SOFTWARE.value, "software")

    def test_generate_dummy_alerts(self):
        """Test dummy alert generation"""
        dummy_alerts = generate_dummy_alerts()
        
        # Should generate expected number of alerts
        self.assertEqual(len(dummy_alerts), 9)  # 3 sprinkler + 2 fan + 3 camera + 1 software
        
        # Should have all alert types
        alert_types = {alert.alert_type for alert in dummy_alerts}
        expected_types = {AlertType.SPRINKLER, AlertType.FAN, AlertType.CAMERA, AlertType.SOFTWARE}
        self.assertEqual(alert_types, expected_types)
        
        # All alerts should have valid IDs and descriptions
        for alert in dummy_alerts:
            self.assertTrue(alert.id)
            self.assertTrue(alert.description)
            self.assertIsInstance(alert.timestamp, datetime)


if __name__ == '__main__':
    unittest.main()
