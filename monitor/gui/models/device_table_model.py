"""Device table model for the device status table view"""

from pathlib import Path
from typing import Dict, List
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QIcon, QColor, QFont
from monitor.services.devices_models import DeviceInfo


class DeviceTableModel(QAbstractTableModel):
    """Table model for displaying all device statuses with icons"""

    _HEADERS = ["Type", "Device ID", "Status", "Consecutive", "Last Updated"]

    # Map device_type string values to icon filenames
    _ICON_MAP = {
        "fan": "fan.svg",
        "sprinkler": "sprinkler.svg",
        "camera": "camera.svg",
        "thread": "software.svg",
        "group": "group.svg",
        "comport": "comport.svg",
        "thi_sensor": "THI.svg",
        "unknown": "warning.svg",
    }

    _STATUS_COLORS = {
        "success": QColor("#2e7d32"),   # dark green
        "fail":    QColor("#c62828"),   # dark red
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: List[DeviceInfo] = []
        self._icons_path = Path(__file__).parent.parent / "icons"
        self._icon_cache: Dict[str, QIcon] = {}
        self._load_icons()

    # ------------------------------------------------------------------
    # icon loading
    # ------------------------------------------------------------------

    def _load_icons(self) -> None:
        fallback = QIcon(str(self._icons_path / "warning.svg")) if (self._icons_path / "warning.svg").exists() else QIcon()
        for device_type, filename in self._ICON_MAP.items():
            path = self._icons_path / filename
            self._icon_cache[device_type] = QIcon(str(path)) if path.exists() else fallback

    def _icon_for_device(self, device_type: str) -> QIcon:
        return self._icon_cache.get(device_type.lower(), self._icon_cache.get("unknown", QIcon()))

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._devices)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._devices):
            return None

        device = self._devices[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return device.device_type
            elif col == 1:
                return device.device_id
            elif col == 2:
                return device.status
            elif col == 3:
                return str(device.last_log_consecutive_count)
            elif col == 4:
                return device.last_updated.strftime("%Y-%m-%d %H:%M:%S") if device.last_updated else ""

        elif role == Qt.DecorationRole:
            if col == 0:
                return self._icon_for_device(device.device_type)

        elif role == Qt.ForegroundRole:
            if col == 2:
                return self._STATUS_COLORS.get(device.status.lower())

        elif role == Qt.TextAlignmentRole:
            if col in (0, 2, 3, 4):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.FontRole:
            font = QFont("DejaVu Sans", 10)
            if col == 2:
                font.setBold(True)
            return font

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._HEADERS[section]
        return None

    # ------------------------------------------------------------------
    # public mutation methods
    # ------------------------------------------------------------------

    def set_devices(self, devices: Dict[str, DeviceInfo]) -> None:
        """Replace all device data and reset the model."""
        self.beginResetModel()
        self._devices = sorted(devices.values(), key=lambda d: d.device_id)
        self.endResetModel()
