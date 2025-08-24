"""Authentication dialog for server authentication"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton
from PySide6.QtCore import Qt


class AuthDialog(QDialog):
    """Modal dialog for password and location name authentication."""
    
    def __init__(self, current_location_name: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monitor - Server Authentication")
        self.setModal(True)
        self.setObjectName("auth-dialog")  # Set object name for styling
        self._current_location_name = current_location_name
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        #layout.setSpacing(5)
            
        # Location name section - horizontal layout
        location_layout = QHBoxLayout()
        location_label = QLabel("Location:")
        location_label.setObjectName("auth-description")
        location_label.setFixedWidth(65)  # Fixed width for consistent alignment
        location_layout.addWidget(location_label)
        
        self.location_edit = QLineEdit(self)
        self.location_edit.setObjectName("auth-password-input")
        self.location_edit.setText(self._current_location_name)
        self.location_edit.setPlaceholderText("")
        location_layout.addWidget(self.location_edit)
        
        layout.addLayout(location_layout)
        
        # Password section - horizontal layout
        password_layout = QHBoxLayout()
        description_label = QLabel("Password:")
        description_label.setObjectName("auth-description")
        description_label.setFixedWidth(65)  # Fixed width for consistent alignment
        password_layout.addWidget(description_label)
        
        self.password_edit = QLineEdit(self)
        self.password_edit.setObjectName("auth-password-input")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_edit)
        
        layout.addLayout(password_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        #button_layout.setSpacing(2)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("auth-cancel-button")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.setObjectName("auth-ok-button")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # Set focus to location input first
        self.location_edit.setFocus()
        
        # Connect Enter key to accept
        self.location_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self.accept)
    
    def get_password(self):
        """Get the entered password"""
        return self.password_edit.text()
    
    def get_location_name(self):
        """Get the entered location name"""
        return self.location_edit.text().strip()
