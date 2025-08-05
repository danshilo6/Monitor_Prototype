"""Base page class for all application pages"""

from PySide6.QtWidgets import QWidget

class BasePage(QWidget):
    """Base class for all application pages"""
    
    def __init__(self):
        super().__init__()
        self._signals_connected = []  # Track connected signals for cleanup
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup the page's UI components - override in subclasses"""
        raise NotImplementedError("Subclasses must implement setup_ui()")
    
    def connect_signals(self):
        """Connect to service signals - override in subclasses"""
        pass
    
    def get_title(self) -> str:
        """Return the page title - override in subclasses"""
        raise NotImplementedError("Subclasses must implement get_title()")
    
    def get_description(self) -> str:
        """Return the page description (optional override)"""
        return "Page description not provided"
    
    def cleanup(self):
        """Clean up resources when page is destroyed (optional override)"""
        # Disconnect any tracked signals
        for signal, slot in self._signals_connected:
            try:
                signal.disconnect(slot)
            except Exception:
                pass  # Signal may already be disconnected
        self._signals_connected.clear()
    
    def track_signal_connection(self, signal, slot):
        """Track a signal connection for later cleanup"""
        self._signals_connected.append((signal, slot))
