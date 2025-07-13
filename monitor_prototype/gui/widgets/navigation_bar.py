from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from .button_group_manager import ButtonGroupManager
from utils.paths import get_icon_path

_H_MARGIN_PX = 6
_V_MARGIN_PX = 4
_BUTTON_SPACING_PX = 4
ICON_PREFIX = ":/icons"

class NavigationBar(QWidget):
    """Vertical sidebar that emits *page_changed* when the user picks a page"""

    page_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._button_manager = ButtonGroupManager()
        
        # Forward the signal from button manager to maintain API compatibility
        self._button_manager.selection_changed.connect(self.page_changed.emit)
        
        self._setup_ui()

    # --------------------------------------------------------------------------
    # private setup methods
    # --------------------------------------------------------------------------
    
    def _setup_ui(self) -> None:
        """Initialize and layout all UI components"""
        # ---- layout -----------------------------------------------------------------
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(
            _H_MARGIN_PX, _V_MARGIN_PX,
            _H_MARGIN_PX, _V_MARGIN_PX,
        )
        layout.setSpacing(_BUTTON_SPACING_PX)

        # ---- buttons ----------------------------------------------------------------
        for label, page, icon in [
            ("Alerts", "alerts", "warning.svg"),
            ("Contacts", "contacts", "contacts.svg"),
            ("Settings", "settings", "settings.svg"),
        ]:
            btn = self._button_manager.add_button(label, page, get_icon_path(icon))
            layout.addWidget(btn)

        # default selection
        self.select("alerts")


    # --------------------------------------------------------------------------
    # public helpers
    # --------------------------------------------------------------------------
    
    def select(self, page_name: str) -> None:
        """Highlights button *page_name* (does not emit signal)"""
        self._button_manager.select(page_name)
        
    

    
