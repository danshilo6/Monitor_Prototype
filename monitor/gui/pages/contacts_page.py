"""Contacts page for managing contact directory"""

import re
from PySide6.QtWidgets import (QVBoxLayout, QLabel, QTableWidget, 
                               QTableWidgetItem, QPushButton, QInputDialog, 
                               QMessageBox, QWidget, QDialog, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from monitor.gui.pages.base_page import BasePage
from monitor.services.contact_db import ContactDatabase
from monitor.gui.widgets.phone_input_dialog import PhoneInputDialog

class ContactsPage(BasePage):
    """Contact management page with email and phone lists"""
    
    def __init__(self):
        self.contact_db = ContactDatabase()
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
    
    def _setup_table_ui(self, table: QTableWidget, column_headers: list):
        """Setup common table UI properties"""
        table.setObjectName("contact-table")
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(column_headers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Disable focus on table
        
        # Hide headers and grid lines
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        
        # Configure columns
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 70)  # Wider to show X button properly
        
        # Add padding to rows
        table.verticalHeader().setDefaultSectionSize(40)

    def _create_email_section(self) -> QWidget:
        """Create email table section"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Section header
        header = QLabel("Email Addresses")
        header.setObjectName("section-header")
        layout.addWidget(header)
        
        # Add button
        add_btn = QPushButton("Add Email")
        add_btn.setObjectName("add-button")
        add_btn.clicked.connect(self._add_email)
        layout.addWidget(add_btn)
        
        # Email table
        self._email_table = QTableWidget()
        email_table_headers = ["Email Address", "Action"]
        self._setup_table_ui(self._email_table, email_table_headers)
        
        layout.addWidget(self._email_table, 1)  # Add stretch factor
        
        return widget
    
    def _create_phone_section(self) -> QWidget:
        """Create phone table section"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Section header
        header = QLabel("Phone Numbers")
        header.setObjectName("section-header")
        layout.addWidget(header)
        
        # Add button
        add_btn = QPushButton("Add Phone")
        add_btn.setObjectName("add-button")
        add_btn.clicked.connect(self._add_phone)
        layout.addWidget(add_btn)
        
        # Phone table
        self._phone_table = QTableWidget()
        phone_table_headers = ["Phone Number", "Action"]
        self._setup_table_ui(self._phone_table, phone_table_headers)
        
        layout.addWidget(self._phone_table, 1)  # Add stretch factor
        
        return widget
    
    def _load_data(self):
        """Load emails and phones from database"""
        self._email_table.setRowCount(0)
        self._phone_table.setRowCount(0)
        
        # Load emails
        emails = self.contact_db.get_emails()
        self._email_table.setRowCount(len(emails))
        
        for row, (email_id, email) in enumerate(emails):
            # Email text
            email_item = QTableWidgetItem(email)
            email_item.setData(Qt.ItemDataRole.UserRole, email_id)
            email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._email_table.setItem(row, 0, email_item)
            
            # Delete button
            delete_btn = QPushButton("X")
            delete_btn.setObjectName("remove-button")
            delete_btn.clicked.connect(lambda checked, eid=email_id: self._delete_email(eid))
            self._email_table.setCellWidget(row, 1, delete_btn)
        
        # Load phones
        phones = self.contact_db.get_phones()
        self._phone_table.setRowCount(len(phones))
        
        for row, (phone_id, phone) in enumerate(phones):
            # Phone text
            phone_item = QTableWidgetItem(phone)
            phone_item.setData(Qt.ItemDataRole.UserRole, phone_id)
            phone_item.setFlags(phone_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._phone_table.setItem(row, 0, phone_item)
            
            # Delete button
            delete_btn = QPushButton("X")
            delete_btn.setObjectName("remove-button")
            delete_btn.clicked.connect(lambda checked, pid=phone_id: self._delete_phone(pid))
            self._phone_table.setCellWidget(row, 1, delete_btn)
    
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
                    self._load_data()
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
                self._load_data()
            else:
                QMessageBox.warning(self, "Error", "Phone number already exists")
    
    def _delete_email(self, email_id: int):
        """Delete email from database and refresh UI"""
        if self.contact_db.remove_email(email_id):
            self._load_data()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete email")
    
    def _delete_phone(self, phone_id: int):
        """Delete phone from database and refresh UI"""
        if self.contact_db.remove_phone(phone_id):
            self._load_data()
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
