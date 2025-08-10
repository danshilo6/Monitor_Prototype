"""Contact table model for the contact table views"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Tuple

class ContactTableModel(QAbstractTableModel):
    """Table model for displaying contacts (emails or phones) with remove buttons"""
    
    def __init__(self, contact_type: str, parent=None):
        """Initialize the contact model
        
        Args:
            contact_type: Either 'email' or 'phone' to determine the column header
            parent: Parent widget
        """
        super().__init__(parent)
        self._contacts: List[Tuple[int, str]] = []  # List of (id, value) tuples
        self.contact_type = contact_type
        self._headers = [
            "Email Address" if contact_type == "email" else "Phone Number", 
            ""  # Empty header for action column
        ]
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._contacts)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._contacts):
            return None
        
        contact_id, contact_value = self._contacts[index.row()]
        
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return contact_value
            elif index.column() == 1:
                return ""  # No text for action column (delegate handles icon)
        
        elif role == Qt.UserRole:
            # Store the contact ID for easy access
            return contact_id
            
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and 0 <= section < len(self._headers):
            return self._headers[section]
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        
        # Make contact value column read-only, action column non-selectable
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled
    
    def set_contacts(self, contacts: List[Tuple[int, str]]):
        """Set the contacts data"""
        self.beginResetModel()
        self._contacts = contacts
        self.endResetModel()
    
    def add_contact(self, contact_id: int, contact_value: str):
        """Add a new contact"""
        self.beginInsertRows(QModelIndex(), len(self._contacts), len(self._contacts))
        self._contacts.append((contact_id, contact_value))
        self.endInsertRows()
    
    def remove_contact_by_id(self, contact_id: int):
        """Remove a contact by ID"""
        for row, (cid, _) in enumerate(self._contacts):
            if cid == contact_id:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._contacts[row]
                self.endRemoveRows()
                break
    
    def get_contact_at_row(self, row: int) -> Tuple[int, str]:
        """Get the contact (id, value) at the specified row"""
        if 0 <= row < len(self._contacts):
            return self._contacts[row]
        return None
    
    def clear(self):
        """Clear all contacts from the model"""
        self.beginResetModel()
        self._contacts.clear()
        self.endResetModel()
