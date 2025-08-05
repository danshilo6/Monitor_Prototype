"""Reusable delegate for clickable icon buttons in table cells"""

from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QIcon, QMouseEvent
from pathlib import Path


class IconButtonDelegate(QStyledItemDelegate):
    """Delegate that renders clickable icon buttons in table cells
    
    This delegate can be used in any table to add clickable icons.
    Configure the target column and provide normal/hover icon paths.
    """
    
    button_clicked = Signal(int)  # Emits row index when button is clicked
    
    def __init__(self, target_column: int, normal_icon_path: str, hover_icon_path: str, 
                 icon_size: int = 18, parent=None):
        """Initialize the icon button delegate
        
        Args:
            target_column: Which column to render the button in (0-based)
            normal_icon_path: Path to the normal state icon
            hover_icon_path: Path to the hover state icon  
            icon_size: Size of the icon in pixels (default: 18)
            parent: Parent widget
        """
        super().__init__(parent)
        self.target_column = target_column
        self.icon_size = icon_size
        self._normal_icon = QIcon(normal_icon_path)
        self._hover_icon = QIcon(hover_icon_path)
        self._hovered_row = None
    
    def paint(self, painter, option, index):
        """Draw the icon button in the target column"""
        if index.column() == self.target_column:
            # Maintain table styling (alternating colors, borders, etc.)
            super().paint(painter, option, index)
            
            # Center the icon in the cell
            icon_rect = QRect(
                option.rect.x() + (option.rect.width() - self.icon_size) // 2,
                option.rect.y() + (option.rect.height() - self.icon_size) // 2,
                self.icon_size,
                self.icon_size
            )
            
            # Choose icon based on hover state
            icon = self._hover_icon if self._hovered_row == index.row() else self._normal_icon
            icon.paint(painter, icon_rect)
        else:
            super().paint(painter, option, index)
    
    def editorEvent(self, event, model, option, index):
        """Handle mouse clicks and hover effects"""
        if index.column() == self.target_column:
            icon_rect = QRect(
                option.rect.x() + (option.rect.width() - self.icon_size) // 2,
                option.rect.y() + (option.rect.height() - self.icon_size) // 2,
                self.icon_size,
                self.icon_size
            )
            
            if event.type() == QMouseEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and icon_rect.contains(event.pos()):
                    self.button_clicked.emit(index.row())
                    return True
            
            elif event.type() == QMouseEvent.Type.MouseMove:
                should_hover = icon_rect.contains(event.pos())
                new_hover_row = index.row() if should_hover else None
                
                if self._hovered_row != new_hover_row:
                    self._hovered_row = new_hover_row
                    # Check if parent exists and has viewport before updating
                    if hasattr(self, 'parent') and callable(self.parent) and self.parent():
                        parent_widget = self.parent()
                        if hasattr(parent_widget, 'viewport') and parent_widget.viewport():
                            parent_widget.viewport().update()
                return True
        else:
            # Clear hover when mouse leaves target column
            if self._hovered_row is not None:
                self._hovered_row = None
                # Check if parent exists and has viewport before updating
                if hasattr(self, 'parent') and callable(self.parent) and self.parent():
                    parent_widget = self.parent()
                    if hasattr(parent_widget, 'viewport') and parent_widget.viewport():
                        parent_widget.viewport().update()
        
        return super().editorEvent(event, model, option, index)
    
    def clear_hover(self):
        """Clear hover state (useful when mouse leaves table or data changes)"""
        if self._hovered_row is not None:
            self._hovered_row = None
            # Check if parent still exists and has viewport before updating
            if hasattr(self, 'parent') and callable(self.parent) and self.parent():
                parent_widget = self.parent()
                if hasattr(parent_widget, 'viewport') and parent_widget.viewport():
                    parent_widget.viewport().update()
    
    def reset_hover_state(self):
        """Reset hover state - alias for clear_hover for clarity"""
        self.clear_hover()
    
    def createEditor(self, parent, option, index):
        """No editor needed - we handle everything in paint/editorEvent"""
        return None
    
    def setEditorData(self, editor, index):
        """No data to set for buttons"""
        pass
    
    def setModelData(self, editor, model, index):
        """No model data to set for buttons"""
        pass
    

