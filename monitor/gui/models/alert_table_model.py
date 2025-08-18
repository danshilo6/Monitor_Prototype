"""Alert table model for the alert table view"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal
from PySide6.QtGui import QIcon, QPixmap
from typing import List
from pathlib import Path
from monitor.services.alert_models import Alert, AlertType

class AlertTableModel(QAbstractTableModel):
    """Table model for displaying alerts with icons and remove buttons"""
    
    remove_alert_requested = Signal(str)  # Emits alert_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._alerts: List[Alert] = []
        self._headers = ["Type", "Description", "Timestamp", ""]
        self._icons_path = Path(__file__).parent.parent / "icons"
        self._icon_cache = {}  # Cache for loaded icons
        self._load_icons()
    
    def _load_icons(self):
        """Load and cache icons for each alert type"""
        icon_mapping = {
            AlertType.FAN: "fan.svg",
            AlertType.SPRINKLER: "sprinkler.svg", 
            AlertType.CAMERA: "camera.svg",
            AlertType.SOFTWARE: "software.svg",
            AlertType.GROUP: "group.svg",
            AlertType.THREAD: "software.svg",  # All thread alerts use software icon
            AlertType.COMPORT: "comport.svg",
            AlertType.THI: "THI.svg",
            AlertType.UNKNOWN: "warning.svg"  # Unknown alerts use warning icon
        }
        
        for alert_type, icon_file in icon_mapping.items():
            icon_path = self._icons_path / icon_file
            if icon_path.exists():
                self._icon_cache[alert_type] = QIcon(str(icon_path))
            else:
                # Fallback to warning icon if specific icon not found
                warning_path = self._icons_path / "warning.svg"
                if warning_path.exists():
                    self._icon_cache[alert_type] = QIcon(str(warning_path))
                else:
                    # If even warning icon doesn't exist, create empty icon
                    self._icon_cache[alert_type] = QIcon()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._alerts)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._alerts):
            return None
        
        alert = self._alerts[index.row()]
        column = index.column()
        
        if role == Qt.DisplayRole:
            if column == 0:  # Type - show text
                return alert.alert_type.value
            elif column == 1:  # Description
                return str(alert.description)  # Ensure string conversion
            elif column == 2:  # Timestamp
                return alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            elif column == 3:  # Action column (handled by delegate, no text needed)
                return None
        
        elif role == Qt.DecorationRole:
            if column == 0:  # Type - show icon
                return self._icon_cache.get(alert.alert_type)
        
        elif role == Qt.TextAlignmentRole:
            if column == 0:  # Center align type column with icon and text
                return Qt.AlignCenter
            elif column == 2:  # Center align timestamp
                return Qt.AlignCenter
            elif column == 3:  # Center align action column
                return Qt.AlignCenter
        
        elif role == Qt.FontRole:
            # Ensure consistent font across platforms
            from PySide6.QtGui import QFont
            font = QFont("DejaVu Sans", 10)
            if column == 1:  # Description column - use monospace
                font.setFamily("DejaVu Sans Mono")
            return font
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None
    
    def add_alert(self, alert: Alert):
        """Add a new alert"""
        row = len(self._alerts)
        self.beginInsertRows(QModelIndex(), row, row)
        self._alerts.append(alert)
        self.endInsertRows()
    
    def remove_alert_by_id(self, alert_id: str):
        """Remove alert by ID"""
        for row, alert in enumerate(self._alerts):
            if alert.id == alert_id:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._alerts[row]
                self.endRemoveRows()
                break
    
    def set_alerts(self, alerts: List[Alert]):
        """Set the entire alert list"""
        self.beginResetModel()
        self._alerts = alerts.copy()
        self.endResetModel()
    
    def get_alert_at_row(self, row: int) -> Alert:
        """Get alert at specific row"""
        if 0 <= row < len(self._alerts):
            return self._alerts[row]
        return None
    
    def clear(self):
        """Clear all alerts from the model"""
        self.beginResetModel()
        self._alerts.clear()
        self.endResetModel()
