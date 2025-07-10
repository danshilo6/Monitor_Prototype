from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon
from functools import partial
from typing import Dict

_H_MARGIN_PX = 6
_V_MARGIN_PX = 4
_BUTTON_SPACING_PX = 4
ICON_PREFIX = ":/icons"

class NavigationBar(QWidget):
    """Vertical sidebar that emits *page_changed* when the user picks a page"""

    page_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._btn_map: Dict[str, QPushButton] = {}
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        # ---- layout -----------------------------------------------------------------
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(
            _H_MARGIN_PX, _V_MARGIN_PX,
            _H_MARGIN_PX, _V_MARGIN_PX,
        )
        layout.setSpacing(_BUTTON_SPACING_PX)

        # ---- buttons ----------------------------------------------------------------
        for label, page, icon in [
            ("Failing Devices", "failing_devices", "warning.svg"),
            ("Contacts", "contacts", "contacts.svg"),
            ("Settings", "settings", "settings.svg"),
        ]:
            self._add_button(layout, label, page, icon)

        # default selection
        self.select("failing_devices")


    # --------------------------------------------------------------------------
    # public helpers
    # --------------------------------------------------------------------------
    
    def select(self, page_name: str) -> None:
        """Highlights button *page_name* (does not emit signal)"""
        if btn := self._btn_map.get(page_name):
            btn.setChecked(True)

    # --------------------------------------------------------------------------
    # internal helpers
    # --------------------------------------------------------------------------

    def _add_button(self, layout: QVBoxLayout, label: str, page_name: str, 
        icon_path: str | None = None) -> None:
        """Creates a button and adds it to the layout"""
        btn = QPushButton(label)
        btn.setObjectName(page_name)
        btn.setCheckable(True)
        if icon_path:
            btn.setIcon(QIcon(f"{ICON_PREFIX}/{icon_path}"))
        btn.clicked.connect(partial(self.page_changed.emit, page_name))

        self._btn_group.addButton(btn)
        self._btn_map[page_name] = btn
        layout.addWidget(btn)
        
    

    
