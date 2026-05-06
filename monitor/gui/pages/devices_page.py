"""Devices page showing live status of all monitored devices"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QTableView, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QFont
from monitor.gui.pages.base_page import BasePage
from monitor.gui.models.device_table_model import DeviceTableModel
from monitor.services.devices_db import DevicesDatabase


class _EmptyDevicesView(QTableView):
    """QTableView that renders a placeholder message when the model is empty."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.empty_message = "No devices found"

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.model() and self.model().rowCount() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.gray)
            painter.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter, self.empty_message)
            painter.restore()


class DevicesPage(BasePage):
    """Page that displays live device status, refreshed every few seconds."""

    _REFRESH_INTERVAL_MS = 3000  # match decision engine cycle

    def __init__(self):
        self._devices_db = DevicesDatabase()
        self._refresh_timer: QTimer | None = None
        super().__init__()

    # ------------------------------------------------------------------
    # BasePage interface
    # ------------------------------------------------------------------

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("Device Status")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self._model = DeviceTableModel(self)
        self._view = _EmptyDevicesView(self)
        self._view.setObjectName("devicesTable")
        self._view.setModel(self._model)

        # Column sizing
        hh = self._view.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)            # Type
        hh.setSectionResizeMode(1, QHeaderView.Stretch)          # Device ID
        hh.setSectionResizeMode(2, QHeaderView.Fixed)            # Status
        hh.setSectionResizeMode(3, QHeaderView.Fixed)            # Consecutive
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Timestamp
        self._view.setColumnWidth(0, 110)
        self._view.setColumnWidth(2, 80)
        self._view.setColumnWidth(3, 100)

        # Appearance
        self._view.setAlternatingRowColors(True)
        self._view.setShowGrid(False)
        self._view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._view.setSelectionMode(QAbstractItemView.NoSelection)
        self._view.setFocusPolicy(Qt.NoFocus)
        self._view.verticalHeader().setDefaultSectionSize(45)
        self._view.verticalHeader().hide()

        layout.addWidget(self._view)

    def connect_signals(self) -> None:
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start(self._REFRESH_INTERVAL_MS)
        # Populate immediately on load
        self._refresh()

    def get_title(self) -> str:
        return "Device Status"

    def cleanup(self) -> None:
        super().cleanup()
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        try:
            devices = self._devices_db.get_all()
            self._model.set_devices(devices)
        except Exception:
            pass  # Keep existing data if db read fails
