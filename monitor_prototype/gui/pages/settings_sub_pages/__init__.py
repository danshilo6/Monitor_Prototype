"""Settings sub-pages initialization"""

from .general_settings import GeneralSettings
from .system_settings import SystemSettings  
from .devices_settings import DevicesSettings

__all__ = ["GeneralSettings", "SystemSettings", "DevicesSettings"]
