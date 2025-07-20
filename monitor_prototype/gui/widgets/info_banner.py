"""Info banner widget for displaying location and version information"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class InfoBanner(QWidget):
    """
    Slim horizontal banner displaying location name, monitor version, and Ein Tzofia version.
    Appears above the navigation bar and main content area.
    """

    def __init__(self, config_service):
        super().__init__()
        self._config_service = config_service
        self.setObjectName("info-banner")
        self._setup_ui()
        self._load_banner_data()

    def _setup_ui(self):
        """Set up the banner layout and widgets."""
        # Create horizontal layout with minimal spacing
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)  # Small margins for slim appearance
        layout.setSpacing(20)  # Space between elements

        # Location name label (left side)
        self._location_label = QLabel()
        self._location_label.setObjectName("banner-location")
        self._location_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._location_label)

        # Spacer to push versions to the right
        layout.addStretch(1)

        # Version labels (right side)
        self._monitor_version_label = QLabel()
        self._monitor_version_label.setObjectName("banner-version")
        self._monitor_version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._monitor_version_label)

        self._ein_tzofia_version_label = QLabel()
        self._ein_tzofia_version_label.setObjectName("banner-version")
        self._ein_tzofia_version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._ein_tzofia_version_label)

        # Set fixed height for slim appearance
        self.setFixedHeight(40)

    def _load_banner_data(self):
        """Load and display data from the config service."""
        self.refresh_location()
        self.refresh_versions()

    def refresh_location(self):
        """Refresh only the location name from config."""
        location_name = self._config_service.get("general", "location_name", "Unknown Location")
        self._set_location_label(location_name)

    def refresh_versions(self):
        """Refresh only the version information from config."""
        monitor_version = self._config_service.get(section="versions", key="monitor_version", default="Unknown")
        ein_tzofia_version = self._config_service.get(section="versions", key="ein_tzofia_version", default="Unknown")
        
        self._set_monitor_version_label(monitor_version)
        self._set_eintzofia_version_label(ein_tzofia_version)

    def refresh(self):
        """Refresh all banner data from config."""
        self._load_banner_data()
    
    def _set_location_label(self, location_name):
        self._location_label.setText(f"Location: {location_name}")
    
    def _set_monitor_version_label(self, monitor_version):
        self._monitor_version_label.setText(f"Monitor v{monitor_version}")

    def _set_eintzofia_version_label(self, ein_tzofia_version):
        self._ein_tzofia_version_label.setText(f"Ein Tzofia v{ein_tzofia_version}")