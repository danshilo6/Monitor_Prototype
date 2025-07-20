"""General settings tab"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, 
                               QPushButton, QFileDialog, QFormLayout)
from PySide6.QtCore import Qt
from ...widgets.location_name_dialog import LocationNameDialog

class GeneralSettings(QWidget):
    """General settings tab widget"""
    
    def __init__(self, config_service):
        super().__init__()
        self._config = config_service
        self._setup_ui()
        self._load_from_config()
    
    def _setup_ui(self):
        """Setup the general settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create form layout for better alignment
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Location Name Section
        self._create_location_name_section(form_layout)
        
        # File Path Section  
        self._create_filepath_section(form_layout)
        
        layout.addLayout(form_layout)
        
        # Add stretch to push content to top
        layout.addStretch()
    
    def _create_location_name_section(self, form_layout: QFormLayout):
        """Create location name input section"""
        # Create horizontal layout for location name display and edit button
        location_name_layout = QHBoxLayout()
        
        # Location name display (read-only)
        self._location_name_display = QLineEdit()
        self._location_name_display.setObjectName("settings-display")
        self._location_name_display.setReadOnly(True)
        self._location_name_display.setPlaceholderText("Enter location name...")  # Placeholder text
        
        # Edit button
        self._edit_location_name_btn = QPushButton("Edit")
        self._edit_location_name_btn.setObjectName("settings-button")
        self._edit_location_name_btn.clicked.connect(self._edit_location_name)
        
        # Add to layout
        location_name_layout.addWidget(self._location_name_display)
        location_name_layout.addWidget(self._edit_location_name_btn)
        
        # Add to form
        form_layout.addRow("Location Name:", location_name_layout)
    
    def _create_filepath_section(self, form_layout: QFormLayout):
        """Create file path selection section"""
        # Create horizontal layout for path display and choose button
        filepath_layout = QHBoxLayout()
        
        # File path display (read-only)
        self._filepath_display = QLineEdit()
        self._filepath_display.setObjectName("settings-display")
        self._filepath_display.setReadOnly(True)
        self._filepath_display.setPlaceholderText("No file selected...")
        
        # Choose file button
        self._choose_file_btn = QPushButton("Choose File")
        self._choose_file_btn.setObjectName("settings-button")
        self._choose_file_btn.clicked.connect(self._choose_file)
        
        # Add to layout
        filepath_layout.addWidget(self._filepath_display)
        filepath_layout.addWidget(self._choose_file_btn)
        
        # Add to form
        form_layout.addRow("Monitor Program:", filepath_layout)
    
    def _edit_location_name(self):
        """Open dialog to edit location name"""
        current_location_name = self._location_name_display.text()
        accepted, new_location_name = LocationNameDialog.edit_location_name(current_location_name, self)
        if accepted and new_location_name:
            self._location_name_display.setText(new_location_name)
            self._config.set("general", "location_name", new_location_name)
            print(f"DEBUG: Location name saved to config: {new_location_name}")  # Debug
            
            # Refresh the banner to show the updated location name
            from ...main_window import MainWindow
            main_window = MainWindow.get_instance()
            print(f"DEBUG: MainWindow instance: {main_window}")  # Debug
            if main_window:
                print("DEBUG: Calling refresh_banner_location...")  # Debug
                main_window.refresh_banner_location()
            else:
                print("DEBUG: MainWindow instance is None!")  # Debug
    
    def _choose_file(self):
        """Open file dialog to choose monitored program"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Program to Monitor",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self._filepath_display.setText(file_path)
            self._config.set("general", "monitor_program_path", file_path)

    def _load_from_config(self):
        """Load settings from config on startup"""
        # Block signals to prevent saving during load
        self._location_name_display.blockSignals(True)
        self._filepath_display.blockSignals(True)
        
        # Load values
        location = self._config.get("general", "location_name", "")
        self._location_name_display.setText(location)
        program_path = self._config.get("general", "monitor_program_path", "")
        self._filepath_display.setText(program_path)
        
        # Re-enable signals
        self._location_name_display.blockSignals(False)
        self._filepath_display.blockSignals(False)
    
    def get_location_name(self) -> str:
        """Get the current location name"""
        return self._location_name_display.text()
    
    def get_monitor_program_path(self) -> str:
        """Get the current monitor program path"""
        return self._filepath_display.text()
    
    def set_location_name(self, name: str):
        """Set the location name"""
        self._location_name_display.setText(name)
    
    def set_monitor_program_path(self, path: str):
        """Set the monitor program path"""
        self._filepath_display.setText(path)
