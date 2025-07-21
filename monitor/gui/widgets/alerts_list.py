"""Alert list widget for displaying alerts"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from monitor.gui.utils.paths import get_icon_path
from monitor.services.alert_models import Alert, AlertType
from typing import List

class AlertsList(QWidget):
    """Widget displaying list of alerts using QTableWidget"""
    
    def __init__(self):
        super().__init__()
        self._alerts = []
        self._alert_db = None  # Will be set by parent page
        self.setObjectName("AlertsList")  # Set object name for styling
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["", "Type", "Description", "Time", "Remove"])
        
        # Style the table
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        # Disable selection completely
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setShowGrid(False)
        
        # Set row height
        self._table.verticalHeader().setDefaultSectionSize(45)
        
        # Auto-resize columns
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Icon
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Description
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Time
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Remove
        
        layout.addWidget(self._table)
    
    def set_alert_database(self, alert_db):
        """Set the alert database reference"""
        self._alert_db = alert_db
    
    def add_alert(self, alert: Alert):
        """Add an alert to the table"""
        row = self._table.rowCount()
        self._table.insertRow(row)
        
        # Add icon
        icon_item = QTableWidgetItem()
        icon_path = self._get_alert_icon(alert.alert_type)
        if icon_path:
            icon_item.setIcon(QIcon(icon_path))
        icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        icon_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 0, icon_item)
        
        # Add type
        type_item = QTableWidgetItem(alert.alert_type.value.title())
        type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 1, type_item)
        
        # Add description
        desc_item = QTableWidgetItem(alert.description)
        desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        #desc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use monospace font for technical data
        font = desc_item.font()
        font.setFamily("Consolas, Monaco, monospace")
        desc_item.setFont(font)
        self._table.setItem(row, 2, desc_item)
        
        # Add timestamp
        time_item = QTableWidgetItem(alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 3, time_item)
        
        # Add remove button
        remove_btn = QPushButton("X")
        remove_btn.clicked.connect(lambda: self._remove_by_id(alert.id))
        self._table.setCellWidget(row, 4, remove_btn)
        
        # Store alert data
        self._alerts.append(alert)
    
    def _remove_by_id(self, alert_id: str):
        """Remove alert by ID from both database and UI"""
        # Remove from database first
        if self._alert_db:
            success = self._alert_db.resolve_alert(alert_id)
            if not success:
                print(f"Failed to resolve alert {alert_id} in database")
        
        # Remove from UI
        for row in range(self._table.rowCount()):
            if row < len(self._alerts) and self._alerts[row].id == alert_id:
                self._alerts.pop(row)
                self._table.removeRow(row)
                self._recreate_button_connections()
                break
    
    def _recreate_button_connections(self):
        """Recreate all remove button connections with correct alert associations"""
        for row in range(self._table.rowCount()):
            if row < len(self._alerts):
                alert = self._alerts[row]
                remove_btn = self._table.cellWidget(row, 4)
                if remove_btn:
                    # Disconnect the specific signal
                    remove_btn.clicked.disconnect()
                    # Connect with correct alert ID
                    remove_btn.clicked.connect(lambda checked, aid=alert.id: self._remove_by_id(aid))
    
    def _get_alert_icon(self, alert_type: AlertType) -> str:
        """Get icon path for alert type"""
        icon_map = {
            AlertType.SPRINKLER: "sprinkler.svg",
            AlertType.FAN: "fan.svg", 
            AlertType.CAMERA: "camera.svg",
            AlertType.SOFTWARE: "software.svg"
        }
        return get_icon_path(icon_map.get(alert_type, "warning.svg"))
