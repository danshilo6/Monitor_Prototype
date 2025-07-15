"""Dialog for editing location name"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import Qt

class LocationNameDialog(QDialog):
    """Dialog for editing location name"""
    
    def __init__(self, current_location_name: str = "", parent=None):
        super().__init__(parent)
        self._current_location_name = current_location_name
        self.setWindowTitle("Edit Location Name")
        self.setModal(True)
        self.setObjectName("location-name-dialog")  # Set object name for styling
        self.setMinimumSize(450, 220)  # Set minimum size instead of fixed
        self.setMaximumSize(600, 300)  # Allow some flexibility
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Label
        label = QLabel("Location Name:")
        layout.addWidget(label)
        
        # Input field
        self._location_name_input = QLineEdit()
        self._location_name_input.setText(self._current_location_name)
        self._location_name_input.selectAll()  # Select all text for easy editing
        self._location_name_input.setPlaceholderText("Enter location name...")
        layout.addWidget(self._location_name_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self.accept)
        self._save_btn.setDefault(True)  # Make it the default button (Enter key)
        
        button_layout.addStretch()
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._save_btn)
        
        layout.addLayout(button_layout)
        
        # Connect Enter key to save
        self._location_name_input.returnPressed.connect(self.accept)
        
        # Focus on input field
        self._location_name_input.setFocus()
    
    def get_location_name(self) -> str:
        """Get the entered location name"""
        return self._location_name_input.text().strip()
    
    @staticmethod
    def edit_location_name(current_location_name: str = "", parent=None) -> tuple[bool, str]:
        """
        Static method to show dialog and get result
        Returns (accepted, location_name)
        """
        dialog = LocationNameDialog(current_location_name, parent)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            return True, dialog.get_location_name()
        else:
            return False, current_location_name
