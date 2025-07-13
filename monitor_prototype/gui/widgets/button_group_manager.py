from PySide6.QtWidgets import QPushButton, QButtonGroup
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPalette
from functools import partial
from typing import Dict

class ButtonGroupManager(QObject):
    """Manages a group of exclusive buttons with selection state and signals"""
    
    # Signal emitted when button selection changes
    selection_changed = Signal(str)
    
    def __init__(self) -> None:
        super().__init__()
        self._btn_map: Dict[str, QPushButton] = {}
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
    
    # --------------------------------------------------------------------------
    # public interface
    # --------------------------------------------------------------------------
    
    def add_button(self, label: str, name: str, 
                   icon_path: str | None = None) -> QPushButton:
        """Creates and registers a button with the given name"""
        btn = QPushButton(label)
        btn.setObjectName(name)
        btn.setCheckable(True)
        
        if icon_path:
            btn.setIcon(QIcon(icon_path))
            btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        btn.clicked.connect(partial(self.selection_changed.emit, name))
        
        self._btn_group.addButton(btn)
        self._btn_map[name] = btn
        return btn
    
    def select(self, name: str) -> None:
        """Selects the button with the given name (does not emit signal)"""
        if btn := self._btn_map.get(name):
            btn.setChecked(True)
    
    def get_button(self, name: str) -> QPushButton | None:
        """Returns the button with the given name"""
        return self._btn_map.get(name)
    
    @property
    def selected_name(self) -> str | None:
        """Returns the name of the currently selected button"""
        if selected_btn := self._btn_group.checkedButton():
            return selected_btn.objectName()
        return None
    
    @property
    def button_count(self) -> int:
        """Returns the number of registered buttons"""
        return len(self._btn_map)
