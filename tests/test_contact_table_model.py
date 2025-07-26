"""Tests for ContactTableModel functionality"""

import unittest
from unittest.mock import Mock
from PySide6.QtCore import Qt, QModelIndex
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor.gui.models.contact_table_model import ContactTableModel


class TestContactTableModel(unittest.TestCase):
    """Test cases for ContactTableModel"""

    def setUp(self):
        """Set up test models"""
        self.email_model = ContactTableModel("email")
        self.phone_model = ContactTableModel("phone")
        
        # Sample contact data: (id, value) tuples
        self.sample_emails = [
            (1, "admin@company.com"),
            (2, "security@company.com"),
            (3, "it-support@company.com")
        ]
        
        self.sample_phones = [
            (1, "+1-555-0123"),
            (2, "+1-555-0456"),
            (3, "+44-20-7946-0958")
        ]

    def test_email_model_initialization(self):
        """Test email model is properly initialized"""
        self.assertEqual(self.email_model.rowCount(), 0)
        self.assertEqual(self.email_model.columnCount(), 2)
        self.assertEqual(self.email_model.contact_type, "email")
        self.assertEqual(len(self.email_model._contacts), 0)

    def test_phone_model_initialization(self):
        """Test phone model is properly initialized"""
        self.assertEqual(self.phone_model.rowCount(), 0)
        self.assertEqual(self.phone_model.columnCount(), 2)
        self.assertEqual(self.phone_model.contact_type, "phone")
        self.assertEqual(len(self.phone_model._contacts), 0)

    def test_email_headers(self):
        """Test email model column headers"""
        header_0 = self.email_model.headerData(0, Qt.Horizontal, Qt.DisplayRole)
        header_1 = self.email_model.headerData(1, Qt.Horizontal, Qt.DisplayRole)
        
        self.assertEqual(header_0, "Email Address")
        self.assertEqual(header_1, "")  # Empty for action column

    def test_phone_headers(self):
        """Test phone model column headers"""
        header_0 = self.phone_model.headerData(0, Qt.Horizontal, Qt.DisplayRole)
        header_1 = self.phone_model.headerData(1, Qt.Horizontal, Qt.DisplayRole)
        
        self.assertEqual(header_0, "Phone Number")
        self.assertEqual(header_1, "")  # Empty for action column

    def test_set_contacts_email(self):
        """Test setting email contacts"""
        self.email_model.set_contacts(self.sample_emails)
        
        self.assertEqual(self.email_model.rowCount(), len(self.sample_emails))
        for i, (contact_id, contact_value) in enumerate(self.sample_emails):
            self.assertEqual(self.email_model._contacts[i], (contact_id, contact_value))

    def test_set_contacts_phone(self):
        """Test setting phone contacts"""
        self.phone_model.set_contacts(self.sample_phones)
        
        self.assertEqual(self.phone_model.rowCount(), len(self.sample_phones))
        for i, (contact_id, contact_value) in enumerate(self.sample_phones):
            self.assertEqual(self.phone_model._contacts[i], (contact_id, contact_value))

    def test_add_contact_email(self):
        """Test adding a single email contact"""
        initial_count = self.email_model.rowCount()
        
        self.email_model.add_contact(99, "test@example.com")
        
        self.assertEqual(self.email_model.rowCount(), initial_count + 1)
        self.assertEqual(self.email_model._contacts[0], (99, "test@example.com"))

    def test_add_contact_phone(self):
        """Test adding a single phone contact"""
        initial_count = self.phone_model.rowCount()
        
        self.phone_model.add_contact(99, "+1-555-9999")
        
        self.assertEqual(self.phone_model.rowCount(), initial_count + 1)
        self.assertEqual(self.phone_model._contacts[0], (99, "+1-555-9999"))

    def test_remove_contact_by_id_email(self):
        """Test removing email contact by ID"""
        self.email_model.set_contacts(self.sample_emails)
        initial_count = self.email_model.rowCount()
        
        self.email_model.remove_contact_by_id(2)  # Remove security@company.com
        
        self.assertEqual(self.email_model.rowCount(), initial_count - 1)
        # Verify the correct contact was removed
        remaining_ids = [contact_id for contact_id, _ in self.email_model._contacts]
        self.assertNotIn(2, remaining_ids)
        self.assertIn(1, remaining_ids)
        self.assertIn(3, remaining_ids)

    def test_remove_contact_by_id_phone(self):
        """Test removing phone contact by ID"""
        self.phone_model.set_contacts(self.sample_phones)
        initial_count = self.phone_model.rowCount()
        
        self.phone_model.remove_contact_by_id(2)  # Remove +1-555-0456
        
        self.assertEqual(self.phone_model.rowCount(), initial_count - 1)
        # Verify the correct contact was removed
        remaining_ids = [contact_id for contact_id, _ in self.phone_model._contacts]
        self.assertNotIn(2, remaining_ids)
        self.assertIn(1, remaining_ids)
        self.assertIn(3, remaining_ids)

    def test_get_contact_at_row_email(self):
        """Test getting email contact at specific row"""
        self.email_model.set_contacts(self.sample_emails)
        
        # Valid row
        contact = self.email_model.get_contact_at_row(1)
        self.assertEqual(contact, self.sample_emails[1])
        
        # Invalid rows
        self.assertIsNone(self.email_model.get_contact_at_row(-1))
        self.assertIsNone(self.email_model.get_contact_at_row(len(self.sample_emails)))

    def test_get_contact_at_row_phone(self):
        """Test getting phone contact at specific row"""
        self.phone_model.set_contacts(self.sample_phones)
        
        # Valid row
        contact = self.phone_model.get_contact_at_row(1)
        self.assertEqual(contact, self.sample_phones[1])
        
        # Invalid rows
        self.assertIsNone(self.phone_model.get_contact_at_row(-1))
        self.assertIsNone(self.phone_model.get_contact_at_row(len(self.sample_phones)))

    def test_data_display_role_email(self):
        """Test data retrieval for email model display role"""
        self.email_model.set_contacts(self.sample_emails)
        contact_id, contact_value = self.sample_emails[0]
        
        # Contact value column (0)
        index = self.email_model.index(0, 0)
        data = self.email_model.data(index, Qt.DisplayRole)
        self.assertEqual(data, contact_value)
        
        # Action column (1) should return empty string (handled by delegate)
        index = self.email_model.index(0, 1)
        data = self.email_model.data(index, Qt.DisplayRole)
        self.assertEqual(data, "")

    def test_data_display_role_phone(self):
        """Test data retrieval for phone model display role"""
        self.phone_model.set_contacts(self.sample_phones)
        contact_id, contact_value = self.sample_phones[0]
        
        # Contact value column (0)
        index = self.phone_model.index(0, 0)
        data = self.phone_model.data(index, Qt.DisplayRole)
        self.assertEqual(data, contact_value)
        
        # Action column (1) should return empty string (handled by delegate)
        index = self.phone_model.index(0, 1)
        data = self.phone_model.data(index, Qt.DisplayRole)
        self.assertEqual(data, "")

    def test_data_alignment_role(self):
        """Test data alignment for both models"""
        self.email_model.set_contacts(self.sample_emails)
        self.phone_model.set_contacts(self.sample_phones)
        
        for model in [self.email_model, self.phone_model]:
            # Contact value column (0) should not have special alignment
            index = model.index(0, 0)
            alignment = model.data(index, Qt.TextAlignmentRole)
            self.assertIsNone(alignment)
            
            # Action column (1) should also not have special alignment in this model
            index = model.index(0, 1)
            alignment = model.data(index, Qt.TextAlignmentRole)
            self.assertIsNone(alignment)

    def test_invalid_index_handling(self):
        """Test handling of invalid indices"""
        self.email_model.set_contacts(self.sample_emails)
        
        # Invalid row
        invalid_index = self.email_model.index(999, 0)
        data = self.email_model.data(invalid_index, Qt.DisplayRole)
        self.assertIsNone(data)
        
        # Invalid column
        invalid_index = self.email_model.index(0, 999)
        data = self.email_model.data(invalid_index, Qt.DisplayRole)
        self.assertIsNone(data)

    def test_header_data_invalid(self):
        """Test header data with invalid parameters"""
        # Invalid section - should handle gracefully
        header = self.email_model.headerData(999, Qt.Horizontal, Qt.DisplayRole)
        self.assertIsNone(header)
        
        # Vertical orientation (not supported)
        header = self.email_model.headerData(0, Qt.Vertical, Qt.DisplayRole)
        self.assertIsNone(header)
        
        # Invalid role
        header = self.email_model.headerData(0, Qt.Horizontal, Qt.DecorationRole)
        self.assertIsNone(header)

    def test_empty_contacts_handling(self):
        """Test model behavior with empty contact lists"""
        # Test with empty list
        self.email_model.set_contacts([])
        self.assertEqual(self.email_model.rowCount(), 0)
        
        # Test data access on empty model
        index = self.email_model.index(0, 0)
        data = self.email_model.data(index, Qt.DisplayRole)
        self.assertIsNone(data)

    def test_contact_type_consistency(self):
        """Test that contact type remains consistent"""
        # Email model should always be "email"
        self.assertEqual(self.email_model.contact_type, "email")
        self.email_model.set_contacts(self.sample_emails)
        self.assertEqual(self.email_model.contact_type, "email")
        
        # Phone model should always be "phone"
        self.assertEqual(self.phone_model.contact_type, "phone")
        self.phone_model.set_contacts(self.sample_phones)
        self.assertEqual(self.phone_model.contact_type, "phone")

    def test_model_reset_behavior(self):
        """Test model reset when setting new contacts"""
        # Add initial contacts
        self.email_model.set_contacts(self.sample_emails)
        self.assertEqual(self.email_model.rowCount(), 3)
        
        # Set different contacts (should replace, not append)
        new_contacts = [(10, "new@example.com"), (11, "another@example.com")]
        self.email_model.set_contacts(new_contacts)
        
        self.assertEqual(self.email_model.rowCount(), 2)
        self.assertEqual(self.email_model._contacts[0], new_contacts[0])
        self.assertEqual(self.email_model._contacts[1], new_contacts[1])


if __name__ == '__main__':
    # Run tests
    unittest.main()
