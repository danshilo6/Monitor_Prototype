"""Tests for AlertTableModel functionality"""

import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtTest import QSignalSpy
from datetime import datetime
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor.gui.models.alert_table_model import AlertTableModel
from monitor.services.alert_models import Alert, AlertType


class TestAlertTableModel(unittest.TestCase):
    """Test cases for AlertTableModel"""

    def setUp(self):
        """Set up test model"""
        self.model = AlertTableModel()
        
        # Create sample alerts for testing
        self.sample_alerts = [
            Alert(
                id="alert1",
                alert_type=AlertType.FAN,
                description="Fan failure in server room",
                timestamp=datetime(2024, 1, 1, 10, 0, 0)
            ),
            Alert(
                id="alert2", 
                alert_type=AlertType.SPRINKLER,
                description="Sprinkler system activated",
                timestamp=datetime(2024, 1, 1, 11, 0, 0)
            ),
            Alert(
                id="alert3",
                alert_type=AlertType.CAMERA,
                description="Camera offline",
                timestamp=datetime(2024, 1, 1, 12, 0, 0)
            )
        ]

    def test_model_initialization(self):
        """Test model is properly initialized"""
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.columnCount(), 4)
        self.assertEqual(len(self.model._alerts), 0)

    def test_headers(self):
        """Test column headers are correct"""
        expected_headers = ["Type", "Description", "Timestamp", ""]
        for col in range(self.model.columnCount()):
            header = self.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
            self.assertEqual(header, expected_headers[col])

    def test_add_alert(self):
        """Test adding a single alert"""
        initial_count = self.model.rowCount()
        alert = self.sample_alerts[0]
        
        self.model.add_alert(alert)
        
        self.assertEqual(self.model.rowCount(), initial_count + 1)
        self.assertEqual(self.model._alerts[0], alert)

    def test_set_alerts(self):
        """Test setting multiple alerts at once"""
        self.model.set_alerts(self.sample_alerts)
        
        self.assertEqual(self.model.rowCount(), len(self.sample_alerts))
        for i, alert in enumerate(self.sample_alerts):
            self.assertEqual(self.model._alerts[i], alert)

    def test_remove_alert_by_id(self):
        """Test removing alert by ID"""
        self.model.set_alerts(self.sample_alerts)
        initial_count = self.model.rowCount()
        
        self.model.remove_alert_by_id("alert2")
        
        self.assertEqual(self.model.rowCount(), initial_count - 1)
        # Verify the correct alert was removed
        remaining_ids = [alert.id for alert in self.model._alerts]
        self.assertNotIn("alert2", remaining_ids)
        self.assertIn("alert1", remaining_ids)
        self.assertIn("alert3", remaining_ids)

    def test_get_alert_at_row(self):
        """Test getting alert at specific row"""
        self.model.set_alerts(self.sample_alerts)
        
        # Valid row
        alert = self.model.get_alert_at_row(1)
        self.assertEqual(alert, self.sample_alerts[1])
        
        # Invalid rows
        self.assertIsNone(self.model.get_alert_at_row(-1))
        self.assertIsNone(self.model.get_alert_at_row(len(self.sample_alerts)))

    def test_data_display_role(self):
        """Test data retrieval for display role"""
        self.model.set_alerts(self.sample_alerts)
        alert = self.sample_alerts[0]
        
        # Type column (0)
        index = self.model.index(0, 0)
        data = self.model.data(index, Qt.DisplayRole)
        self.assertEqual(data, alert.alert_type.value)
        
        # Description column (1)
        index = self.model.index(0, 1)
        data = self.model.data(index, Qt.DisplayRole)
        self.assertEqual(data, alert.description)
        
        # Timestamp column (2)
        index = self.model.index(0, 2)
        data = self.model.data(index, Qt.DisplayRole)
        self.assertEqual(data, "2024-01-01 10:00:00")
        
        # Action column (3) should return None
        index = self.model.index(0, 3)
        data = self.model.data(index, Qt.DisplayRole)
        self.assertIsNone(data)

    def test_data_decoration_role(self):
        """Test data retrieval for decoration role (icons)"""
        self.model.set_alerts(self.sample_alerts)
        
        # Type column should have icon
        index = self.model.index(0, 0)
        icon = self.model.data(index, Qt.DecorationRole)
        self.assertIsNotNone(icon)
        
        # Other columns should not have icons
        for col in [1, 2, 3]:
            index = self.model.index(0, col)
            icon = self.model.data(index, Qt.DecorationRole)
            self.assertIsNone(icon)

    def test_data_alignment_role(self):
        """Test data alignment"""
        self.model.set_alerts(self.sample_alerts)
        
        # Type column (0) should be center aligned
        index = self.model.index(0, 0)
        alignment = self.model.data(index, Qt.TextAlignmentRole)
        self.assertEqual(alignment, Qt.AlignCenter)
        
        # Description column (1) should not have alignment (None)
        index = self.model.index(0, 1)
        alignment = self.model.data(index, Qt.TextAlignmentRole)
        self.assertIsNone(alignment)
        
        # Timestamp column (2) should be center aligned
        index = self.model.index(0, 2)
        alignment = self.model.data(index, Qt.TextAlignmentRole)
        self.assertEqual(alignment, Qt.AlignCenter)
        
        # Action column (3) should be center aligned
        index = self.model.index(0, 3)
        alignment = self.model.data(index, Qt.TextAlignmentRole)
        self.assertEqual(alignment, Qt.AlignCenter)

    def test_invalid_index_handling(self):
        """Test handling of invalid indices"""
        self.model.set_alerts(self.sample_alerts)
        
        # Invalid row
        invalid_index = self.model.index(999, 0)
        data = self.model.data(invalid_index, Qt.DisplayRole)
        self.assertIsNone(data)
        
        # Invalid column (beyond defined columns)
        invalid_index = self.model.index(0, 999)
        data = self.model.data(invalid_index, Qt.DisplayRole)
        self.assertIsNone(data)

    def test_signal_emission(self):
        """Test that model has required signal"""
        # Verify the signal exists
        self.assertTrue(hasattr(self.model, 'remove_alert_requested'))
        
        # Test signal can be connected (basic test)
        mock_slot = Mock()
        self.model.remove_alert_requested.connect(mock_slot)
        
        # Emit signal manually to test connection
        self.model.remove_alert_requested.emit("test_id")
        mock_slot.assert_called_once_with("test_id")

    @patch('pathlib.Path.exists')
    def test_icon_loading_with_missing_files(self, mock_exists):
        """Test icon loading when files don't exist"""
        mock_exists.return_value = False
        
        # Create new model with mocked file system
        model = AlertTableModel()
        
        # Should not crash even if icon files don't exist
        self.assertEqual(model.rowCount(), 0)
        self.assertEqual(model.columnCount(), 4)


if __name__ == '__main__':
    # Run tests
    unittest.main()
