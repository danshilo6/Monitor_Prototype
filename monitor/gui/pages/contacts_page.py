"""Contacts page for managing contact directory"""

import re
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QTableView, 
                               QTableWidgetItem, QPushButton, QInputDialog, 
                               QMessageBox, QWidget, QDialog, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from monitor.gui.pages.base_page import BasePage
from monitor.gui.models.contact_table_model import ContactTableModel
from monitor.gui.delegates.button_delegate import IconButtonDelegate
from monitor.gui.utils.paths import get_icon_path
from monitor.services.contact_db import ContactDatabase
from monitor.gui.widgets.phone_input_dialog import PhoneInputDialog

class ContactsPage(BasePage):
    """Contact management page with email and phone lists"""
    
    def __init__(self, contact_db: ContactDatabase):
        self.contact_db = contact_db  # Injected dependency
        super().__init__()
    
    def setup_ui(self):
        """Setup the contacts page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QLabel("Contacts")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Email section
        email_section = self._create_email_section()
        layout.addWidget(email_section, 1)  # Add stretch factor
        
        # Phone section  
        phone_section = self._create_phone_section()
        layout.addWidget(phone_section, 1)  # Add stretch factor
        
        # Load data
        self._load_data()
    
    def _setup_table_ui(self, table: QTableView, model: ContactTableModel):
        """Setup common table UI properties"""
        table.setObjectName("contact-table")
        table.setModel(model)
        
        # Setup icon button delegate for the Action column (column 1)
        delegate = IconButtonDelegate(
            target_column=1,
            normal_icon_path=get_icon_path('trashcan.svg'),
            hover_icon_path=get_icon_path('trashcan_hover.svg'),
            icon_size=18,
            parent=table
        )
        table.setItemDelegateForColumn(1, delegate)
        
        # Enable mouse tracking for hover effects
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)
        
        # Configure table view
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)          # Contact value column
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)            # Action column
        table.setColumnWidth(1, 50)   # Fixed width for icon-only action column
        
        # Table appearance
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        
        # Row height
        table.verticalHeader().setDefaultSectionSize(40)
        table.verticalHeader().hide()  # Hide row numbers
        
        return delegate  # Return delegate so we can connect its signal

    def _create_email_section(self) -> QWidget:
        """Create email table section"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Horizontal layout for label (left) and button (right), vertically centered
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("Email Addresses")
        header.setObjectName("section-header")
        header_row.addWidget(header, alignment=Qt.AlignVCenter | Qt.AlignLeft)

        header_row.addStretch(1)

        add_btn = QPushButton("Add Email")
        add_btn.setObjectName("add-button")
        add_btn.clicked.connect(self._add_email)
        header_row.addWidget(add_btn, alignment=Qt.AlignVCenter | Qt.AlignRight)

        layout.addLayout(header_row)

        # Email table
        self._email_model = ContactTableModel("email", self)
        self._email_table = QTableView()
        self._email_delegate = self._setup_table_ui(self._email_table, self._email_model)

        # Connect delegate signal
        self._email_delegate.button_clicked.connect(self._on_email_remove_clicked)

        layout.addWidget(self._email_table, 1)  # Add stretch factor

        return widget
    
    def _create_phone_section(self) -> QWidget:
        """Create phone table section"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Horizontal layout for label (left) and button (right), vertically centered
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("Phone Numbers")
        header.setObjectName("section-header")
        header_row.addWidget(header, alignment=Qt.AlignVCenter | Qt.AlignLeft)

        header_row.addStretch(1)

        add_btn = QPushButton("Add Phone")
        add_btn.setObjectName("add-button")
        add_btn.clicked.connect(self._add_phone)
        header_row.addWidget(add_btn, alignment=Qt.AlignVCenter | Qt.AlignRight)

        layout.addLayout(header_row)

        # Phone table
        self._phone_model = ContactTableModel("phone", self)
        self._phone_table = QTableView()
        self._phone_delegate = self._setup_table_ui(self._phone_table, self._phone_model)

        # Connect delegate signal
        self._phone_delegate.button_clicked.connect(self._on_phone_remove_clicked)

        layout.addWidget(self._phone_table, 1)  # Add stretch factor

        return widget
    
    def _load_data(self):
        """Load emails and phones from database"""
        # Clear hover states before updating data to prevent stale hover references
        self._email_delegate.clear_hover()
        self._phone_delegate.clear_hover()
        
        # Load emails
        emails = self.contact_db.get_emails()
        self._email_model.set_contacts(emails)
        
        # Load phones
        phones = self.contact_db.get_phones()
        self._phone_model.set_contacts(phones)
    
    def _add_email(self):
        """Add new email via dialog"""
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Add Email")
        dialog.setLabelText("Enter email address:")
        dialog.setWindowIcon(QIcon())
        dialog.setFixedWidth(400)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            email = dialog.textValue().strip()
            if email:
                # Validate email format
                if not self._validate_email(email):
                    QMessageBox.warning(self, "Invalid Email", 
                                      "Please enter a valid email address format.\n"
                                      "Example: user@example.com")
                    return
                
                # Try to add to database
                if self.contact_db.add_email(email):
                    self._load_data()  # Reload to get the new email with ID
                else:
                    QMessageBox.warning(self, "Error", "Email already exists")
    
    def _add_phone(self):
        """Add new phone via dialog"""
        dialog = PhoneInputDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            phone = dialog.get_full_phone_number()
            
            if not phone:
                QMessageBox.warning(self, "Error", "Please enter a phone number")
                return
            
            # Validate phone format using phonenumbers library
            if not dialog.validate_phone_number(phone):
                QMessageBox.warning(self, "Invalid Phone", 
                                  "Please enter a valid phone number.\n"
                                  "The number format is not valid for the selected country.")
                return
            
            # Try to add to database
            if self.contact_db.add_phone(phone):
                self._load_data()  # Reload to get the new phone with ID
            else:
                QMessageBox.warning(self, "Error", "Phone number already exists")
    
    def _on_email_remove_clicked(self, row_index: int):
        """Handle email remove button click"""
        contact = self._email_model.get_contact_at_row(row_index)
        if contact:
            email_id, email_value = contact
            self._delete_email(email_id)
    
    def _on_phone_remove_clicked(self, row_index: int):
        """Handle phone remove button click"""
        contact = self._phone_model.get_contact_at_row(row_index)
        if contact:
            phone_id, phone_value = contact
            self._delete_phone(phone_id)
    
    def _delete_email(self, email_id: int):
        """Delete email from database and refresh UI"""
        if self.contact_db.remove_email(email_id):
            self._load_data()  # Reload to reflect the deletion
        else:
            QMessageBox.warning(self, "Error", "Failed to delete email")
    
    def _delete_phone(self, phone_id: int):
        """Delete phone from database and refresh UI"""
        if self.contact_db.remove_phone(phone_id):
            self._load_data()  # Reload to reflect the deletion
        else:
            QMessageBox.warning(self, "Error", "Failed to delete phone")
    
    def get_title(self) -> str:
        """Return the page title"""
        return "Emergency Contacts"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "Manage email and phone contacts for emergency notifications"
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        # Basic email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
