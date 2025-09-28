"""Restart History page for displaying restart history from database"""

from PySide6.QtWidgets import (QVBoxLayout, QLabel, QTableView, QHeaderView, 
                               QAbstractItemView, QHBoxLayout, QPushButton, QFrame)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QPainter, QFont
from monitor.gui.pages.base_page import BasePage
from monitor.core.restart_db import RestartDB
from datetime import datetime
from typing import List, Dict, Any


class RestartHistoryTableModel(QAbstractTableModel):
    """Table model for displaying restart history data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, str]] = []
        self._headers = ["Timestamp", "Reason"]
        self.restart_db = RestartDB()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows in the model"""
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns in the model"""
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for the given index and role"""
        if not index.isValid() or index.row() >= len(self._data):
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            row_data = self._data[index.row()]
            if index.column() == 0:  # Timestamp
                # Format timestamp for better readability
                try:
                    timestamp = datetime.fromisoformat(row_data['timestamp'])
                    return timestamp.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, KeyError):
                    return row_data.get('timestamp', 'Unknown')
            elif index.column() == 1:  # Reason
                return row_data.get('reason', 'No reason provided')
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 0:  # Timestamp column - center align
                return Qt.AlignmentFlag.AlignCenter
            else:  # Reason column - left align
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data for the given section and role"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None
    
    def refresh_data(self, limit: int = 100) -> None:
        """Refresh the model data from the database"""
        self.beginResetModel()
        try:
            self._data = self.restart_db.get_restart_history(limit)
        except Exception as e:
            print(f"Error loading restart history: {e}")
            self._data = []
        self.endResetModel()


class EmptyRestartHistoryView(QTableView):
    """Custom QTableView that shows a message when no restart history exists"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.empty_message = "No restart history found\nThe system hasn't been restarted yet"
    
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


class RestartHistoryPage(BasePage):
    """Restart History page displaying restart history from database"""
    
    # Signal for requesting data refresh
    refresh_requested = Signal()
    
    def __init__(self):
        super().__init__()
    
    def setup_ui(self):
        """Setup the restart history page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Add header
        header = QLabel("Restart History")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Add statistics section
        self.stats_frame = self._create_statistics_section()
        layout.addWidget(self.stats_frame)
        
        # Create model and view
        self.restart_model = RestartHistoryTableModel(self)
        self.restart_view = EmptyRestartHistoryView(self)
        self.restart_view.setObjectName("restartHistoryTable")  # For CSS styling
        self.restart_view.setModel(self.restart_model)
        
        # Configure table view
        self.restart_view.horizontalHeader().setStretchLastSection(False)
        self.restart_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Timestamp
        self.restart_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)           # Reason
        
        # Table appearance
        self.restart_view.setAlternatingRowColors(True)
        self.restart_view.setShowGrid(False)  # Turn off grid for cleaner look
        self.restart_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.restart_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.restart_view.setFocusPolicy(Qt.NoFocus)
        
        # Row height - match alerts page
        self.restart_view.verticalHeader().setDefaultSectionSize(45)
        self.restart_view.verticalHeader().hide()  # Hide row numbers
        
        layout.addWidget(self.restart_view)
        
        # Load initial data
        self.refresh_data()
    
    def _create_statistics_section(self) -> QFrame:
        """Create the statistics section showing restart summary"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setObjectName("statsFrame")  # For CSS styling
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)  # Match alerts page margins
        
        self.total_restarts_label = QLabel("Total Restarts: Loading...")
        self.total_restarts_label.setObjectName("statsLabel")
        
        self.last_restart_label = QLabel("Last Restart: Loading...")
        self.last_restart_label.setObjectName("statsLabel")
        
        self.recent_restarts_label = QLabel("Last 24h: Loading...")
        self.recent_restarts_label.setObjectName("statsLabel")
        
        # Create separator labels with consistent styling
        separator1 = QLabel("|")
        separator1.setObjectName("statsSeparator")
        separator2 = QLabel("|") 
        separator2.setObjectName("statsSeparator")
        
        layout.addWidget(self.total_restarts_label)
        layout.addWidget(separator1)
        layout.addWidget(self.last_restart_label)
        layout.addWidget(separator2)
        layout.addWidget(self.recent_restarts_label)
        layout.addStretch()
        
        return frame
    
    def refresh_data(self, limit: int = 100):
        """Refresh the restart history data and statistics"""
        try:
            # Refresh table data
            self.restart_model.refresh_data(limit)
            
            # Update statistics
            self._update_statistics()
            
        except Exception as e:
            print(f"Error refreshing restart history data: {e}")
    
    def _update_statistics(self):
        """Update the statistics labels with current data"""
        try:
            restart_db = RestartDB()
            stats = restart_db.get_restart_statistics()
            
            # Update labels
            self.total_restarts_label.setText(f"Total Restarts: {stats.get('total_restarts', 0)}")
            self.recent_restarts_label.setText(f"Last 24h: {stats.get('restarts_last_24h', 0)}")
            
            # Format last restart time
            last_restart = stats.get('last_restart')
            if last_restart:
                try:
                    timestamp = datetime.fromisoformat(last_restart['timestamp'])
                    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
                    self.last_restart_label.setText(f"Last Restart: {formatted_time}")
                except (ValueError, KeyError):
                    self.last_restart_label.setText("Last Restart: Unknown")
            else:
                self.last_restart_label.setText("Last Restart: Never")
                
        except Exception as e:
            print(f"Error updating statistics: {e}")
            self.total_restarts_label.setText("Total Restarts: Error")
            self.last_restart_label.setText("Last Restart: Error")
            self.recent_restarts_label.setText("Last 24h: Error")
    
    def connect_signals(self):
        """Connect to service signals - override from base class"""
        # Connect the refresh signal if needed
        self.refresh_requested.connect(self.refresh_data)
    
    def get_title(self) -> str:
        """Return the page title"""
        return "Restart History"
    
    def get_description(self) -> str:
        """Return the page description"""
        return "View the history of system restarts with timestamps and reasons"