"""Alerts page for displaying and managing system alerts"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QTableView, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QFont
from monitor.gui.pages.base_page import BasePage
from monitor.gui.models.alert_table_model import AlertTableModel
from monitor.gui.delegates.button_delegate import IconButtonDelegate
from monitor.gui.utils.paths import get_icon_path
from monitor.services.alert_models import Alert
from typing import List


class EmptyTableView(QTableView):
    """Custom QTableView that shows a message when empty"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.empty_message = "Everything is working!\nThere are no alerts"
    
    def paintEvent(self, event):
        """Override paint event to show empty message when table is empty"""
        super().paintEvent(event)
        
        # Only show message if model has no data
        if self.model() and self.model().rowCount() == 0:
            painter = QPainter(self.viewport())
            painter.save()
            
            # Set font and color for the message
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.gray)
            
            # Draw text centered in the viewport
            rect = self.viewport().rect()
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.empty_message)
            
            painter.restore()


class AlertsPage(BasePage):
    """Alerts management page with Model/View pattern"""
    
    # Signals for communicating with external components
    alert_removal_requested = Signal(str)  # Emits alert_id when removal is requested
    initial_load_requested = Signal()      # Emits when page needs initial data load

    def __init__(self):
        super().__init__()
    
    def setup_ui(self):
        """Setup the alerts page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Add header
        header = QLabel("Alerts List")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Create model and view
        self.alert_model = AlertTableModel(self)
        self.alert_view = EmptyTableView(self)
        self.alert_view.setObjectName("alertsTable")  # For CSS styling
        self.alert_view.setModel(self.alert_model)
        
        # Setup button delegate for the Action column
        self.button_delegate = IconButtonDelegate(
            target_column=3,
            normal_icon_path=get_icon_path('trashcan.svg'),
            hover_icon_path=get_icon_path('trashcan_hover.svg'),
            icon_size=18,
            parent=self
        )
        self.alert_view.setItemDelegateForColumn(3, self.button_delegate)
        
        # Enable mouse tracking for hover effects
        self.alert_view.setMouseTracking(True)
        self.alert_view.viewport().setMouseTracking(True)
        
        # Connect mouse leave event to clear hover state
        self.alert_view.leaveEvent = self._on_table_leave
        
        # Configure table view
        self.alert_view.horizontalHeader().setStretchLastSection(False)
        self.alert_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)           # Type (icon + text)
        self.alert_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)          # Description
        self.alert_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Timestamp
        self.alert_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)            # Action
        self.alert_view.setColumnWidth(0, 120)  # Fixed width for type column (icon + text)
        self.alert_view.setColumnWidth(3, 50)   # Exact width for icon-only action column
        
        # Table appearance
        self.alert_view.setAlternatingRowColors(True)
        self.alert_view.setShowGrid(False)  # Turn off grid for cleaner look
        self.alert_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.alert_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.alert_view.setFocusPolicy(Qt.NoFocus)
        
        # Row height
        self.alert_view.verticalHeader().setDefaultSectionSize(45)
        self.alert_view.verticalHeader().hide()  # Hide row numbers
        
        layout.addWidget(self.alert_view)
        
        # Connect button delegate to removal action
        self.button_delegate.button_clicked.connect(self._on_remove_button_clicked)
    
    def connect_external_signals(self, alert_db):
        """Connect to external database signals for real-time updates"""
        # Connect database signals to model
        alert_db.alert_added.connect(self.alert_model.add_alert)
        alert_db.alert_resolved.connect(self.alert_model.remove_alert_by_id)
        alert_db.alerts_loaded.connect(self.alert_model.set_alerts)
        
        # Track these connections for cleanup
        self.track_signal_connection(alert_db.alert_added, self.alert_model.add_alert)
        self.track_signal_connection(alert_db.alert_resolved, self.alert_model.remove_alert_by_id)
        self.track_signal_connection(alert_db.alerts_loaded, self.alert_model.set_alerts)
        
        # Connect page signals to database
        self.alert_removal_requested.connect(alert_db.resolve_alert)
        self.initial_load_requested.connect(alert_db.load_alerts)
        
        # Track these connections too
        self.track_signal_connection(self.alert_removal_requested, alert_db.resolve_alert)
        self.track_signal_connection(self.initial_load_requested, alert_db.load_alerts)
        
        # Now that signals are connected, request initial data load
        self.initial_load_requested.emit()
    
    def _on_remove_button_clicked(self, row_index: int):
        """Handle remove button click"""
        # Get the alert from the model using the row index
        alert = self.alert_model.get_alert_at_row(row_index)
        if alert:
            # Emit signal instead of calling database directly
            self.alert_removal_requested.emit(alert.id)
    
    def _on_table_leave(self, event):
        """Handle mouse leaving the table view"""
        self.button_delegate._hovered_row = None
        self.alert_view.viewport().update()
        # Call the original leaveEvent if it exists
        if hasattr(QTableView, 'leaveEvent'):
            QTableView.leaveEvent(self.alert_view, event)
    
    def get_title(self) -> str:
        return "System Alerts"
    
    def get_description(self) -> str:
        return "Real-time alerts with Model/View pattern for automatic updates"
    
    def cleanup(self):
        """Clean up resources when page is destroyed"""
        super().cleanup()  # Call base class cleanup
        
        # Clear delegate hover state
        if hasattr(self, 'button_delegate'):
            self.button_delegate.clear_hover()
        
        # Clear model data
        if hasattr(self, 'alert_model'):
            self.alert_model.clear()
        
        # Reset table mouse tracking to prevent stale event handlers
        if hasattr(self, 'alert_view'):
            self.alert_view.setMouseTracking(False)
            self.alert_view.viewport().setMouseTracking(False)
