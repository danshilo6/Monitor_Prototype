"""Phone input dialog widget with country code dropdown"""

import phonenumbers
import pycountry
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QDialog, 
                               QLineEdit, QComboBox, QDialogButtonBox, QStyledItemDelegate)
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QIcon

class CountryComboBoxDelegate(QStyledItemDelegate):
    """Custom delegate to show full country names in dropdown"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dropdown_texts = {}
    
    def set_dropdown_text(self, index: int, text: str):
        """Set the text to display in dropdown for a specific index"""
        self.dropdown_texts[index] = text
    
    def displayText(self, value, locale):
        """Return the text to display in dropdown"""
        # Get the model index to determine which item this is
        if hasattr(self, 'current_index'):
            dropdown_text = self.dropdown_texts.get(self.current_index)
            if dropdown_text:
                return dropdown_text
        return value
    
    def paint(self, painter, option, index):
        """Custom paint method for dropdown items"""
        # Store current index for displayText method
        self.current_index = index.row()
        
        # Get the dropdown text for this index
        dropdown_text = self.dropdown_texts.get(index.row())
        if dropdown_text:
            # Create a copy of the index with the dropdown text
            temp_index = index.model().createIndex(index.row(), index.column())
            temp_index.model().setData(temp_index, dropdown_text, Qt.ItemDataRole.DisplayRole)
            
            # Temporarily change the display text
            original_text = index.data(Qt.ItemDataRole.DisplayRole)
            index.model().setData(index, dropdown_text, Qt.ItemDataRole.DisplayRole)
            
            # Paint with the new text
            super().paint(painter, option, index)
            
            # Restore original text
            index.model().setData(index, original_text, Qt.ItemDataRole.DisplayRole)
        else:
            super().paint(painter, option, index)

class PhoneInputDialog(QDialog):
    """Custom dialog for phone number input with country code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Phone Number")
        self.setModal(True)
        self.setFixedSize(360, 140)  # Increased width for longer country names
        
        # Remove window icon
        self.setWindowIcon(QIcon())
        
        layout = QVBoxLayout(self)
        
        # Instruction label
        instruction = QLabel("Enter phone number:")
        layout.addWidget(instruction)
        
        # Phone input layout
        phone_layout = QHBoxLayout()
        
        # Country code dropdown
        self.country_combo = QComboBox()
        self.country_combo.setFixedWidth(74)  # Compact button
        self.country_combo.setFixedHeight(32)  # Match input height
        
        # Set up custom delegate for dropdown display
        self.delegate = CountryComboBoxDelegate(self)
        self.country_combo.setItemDelegate(self.delegate)
        
        self._populate_country_codes()
        phone_layout.addWidget(self.country_combo)
        
        # Phone number input
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number")
        self.phone_input.setFixedHeight(32)  # Match dropdown height
        phone_layout.addWidget(self.phone_input)
        
        layout.addLayout(phone_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set focus to phone input
        self.phone_input.setFocus()
    
    def _populate_country_codes(self):
        """Populate country code dropdown using phonenumbers and pycountry"""
        country_data = []
        
        # Get all supported regions from phonenumbers
        for region_code in phonenumbers.SUPPORTED_REGIONS:
            try:
                # Get country code for this region
                country_code = phonenumbers.country_code_for_region(region_code)
                if country_code:
                    # Get country name from pycountry
                    country = pycountry.countries.get(alpha_2=region_code)
                    if country:
                        country_name = country.name
                        # Button display: shorthand + code (e.g., "IL +972")
                        button_display = f"{region_code} +{country_code}"
                        # Dropdown display: full name + code (e.g., "Israel (+972)")
                        dropdown_display = f"{country_name} (+{country_code})"
                        country_data.append((button_display, dropdown_display, f"+{country_code}", country_name, region_code))
            except:
                # Skip any regions that cause errors
                continue
        
        # Sort by country name
        country_data.sort(key=lambda x: x[3])
        
        # Add to combo box - for now, add the button display
        for button_display, dropdown_display, country_code, _, region_code in country_data:
            self.country_combo.addItem(button_display, country_code)
            # Store the dropdown display text for the delegate
            item_index = self.country_combo.count() - 1
            self.delegate.set_dropdown_text(item_index, dropdown_display)
        
        # Make dropdown list wider than the button to show full country names
        self.country_combo.view().setMinimumWidth(320)
        
        # Set default to Israel if available
        for i in range(self.country_combo.count()):
            if "IL +972" in self.country_combo.itemText(i):
                self.country_combo.setCurrentIndex(i)
                break
    
    def get_full_phone_number(self) -> str:
        """Get the complete phone number with country code"""
        country_code = self.country_combo.currentData()
        phone_number = self.phone_input.text().strip()
        
        if phone_number:
            # Remove any leading + or country code from input
            phone_number = phone_number.lstrip('+')
            # Remove country code if user entered it
            if country_code and len(country_code) > 1:
                country_digits = country_code[1:]  # Remove the +
                if phone_number.startswith(country_digits):
                    phone_number = phone_number[len(country_digits):]
            
            return f"{country_code} {phone_number}"
        return ""
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number using phonenumbers library"""
        try:
            # Parse the phone number
            parsed = phonenumbers.parse(phone_number, None)
            # Check if it's valid
            return phonenumbers.is_valid_number(parsed)
        except phonenumbers.NumberParseException:
            return False
