import os
import sys
import platform
from pathlib import Path
from monitor.log_setup import get_logger

# Import the legacy os_manager class
sys.path.append(str(Path(__file__).parent.parent.parent / "legacy_code"))
from os_class import os_manager as LegacyOSManager


class MockParent:
    """
    Mock parent object that provides everything the legacy os_class needs.
    """
    
    def __init__(self, config_service=None):
        self.config_service = config_service
        
        # Legacy settings dictionary that os_class expects
        self.settings = {
            'File_Path': self._get_eintzofia_path_from_config()
        }
        
        # Legacy enable_pc_restart flag
        self.enable_pc_restart = self._get_restart_setting()
        
        # Mock settings_manager for methods that need data_dir
        self.settings_manager = MockSettingsManager()
    
    def _get_eintzofia_path_from_config(self):
        """Get EinTzofia path from config service."""
        if self.config_service:
            return self.config_service.get("general", "eintzofia_path", "")
        return ""
    
    def _get_restart_setting(self):
        """Get restart permission from config service."""
        if self.config_service:
            return self.config_service.get("general", "enable_pc_restart", True)
        return True


class MockSettingsManager:
    """Mock settings manager for legacy code that needs data_dir."""
    
    def __init__(self):
        # Default data directory for shooshk.pem and other files
        self.data_dir = str(Path.cwd() / "data")


class OSManager:
    """
    Modern OS manager that wraps legacy functionality.
    Provides both new cross-platform methods and legacy compatibility.
    """
    
    def __init__(self, config_service=None):
        """
        Initialize the OS manager.
        
        Args:
            config_service: Optional config service for accessing settings
        """
        self.config_service = config_service
        self.current_os = platform.system()
        print(f"current_os: {self.current_os}")
        
        # Create mock parent and initialize legacy os_manager
        self.mock_parent = MockParent(config_service)
        self.legacy_os = LegacyOSManager(self.mock_parent)
    
    # IMPORTANT FOR DAN methods - use legacy implementation
    def restart_pc(self):
        """Restart the PC using legacy implementation."""
        return self.legacy_os.restart_pc()
    
    def open_file(self, file_path):
        """Open file using legacy implementation."""
        return self.legacy_os.open_file(file_path)
    
    def get_hardware_info(self):
        """Get hardware info using legacy implementation."""
        return self.legacy_os.get_hardware_info()
    
    def generate_device_id(self):
        """Generate device ID using legacy implementation."""
        return self.legacy_os.generate_device_id()
    
    # Modern cross-platform method
    def find_eintzofia_executable(self, search_dir: Path) -> str:
        """
        Find EinTzofia executable in the specified directory.
        
        Cross-platform function that looks for executable files starting with "EinTzofia":
        - Windows: Searches for EinTzofia*.exe files
        - Linux/Unix: Searches for executable files starting with "EinTzofia"
        
        Args:
            search_dir: Directory to search in
            
        Returns:
            str: Path to EinTzofia executable, or empty string if not found
        """
        logger = get_logger("monitor.core.os_manager")
        
        if not search_dir.exists() or not search_dir.is_dir():
            logger.debug(f"Directory not found: {search_dir}")
            return ""
        
        is_windows = self.current_os == "Windows"
        
        try:
            if is_windows:
                # On Windows, look for .exe files
                exe_files = list(search_dir.glob("EinTzofia*.exe"))
                file_type = "*.exe files"
            else:
                # On Linux/Unix, look for executable files starting with "EinTzofia"
                potential_files = list(search_dir.glob("EinTzofia*"))
                exe_files = [
                    f for f in potential_files 
                    if f.is_file() and os.access(f, os.X_OK)
                ]
                file_type = "executable files"
            
            if not exe_files:
                logger.debug(f"No EinTzofia {file_type} found in: {search_dir}")
                return ""
            
            # Use the first matching executable
            exe_path = exe_files[0]
            logger.info(f"Found EinTzofia executable: {exe_path}")
            print(f"DEBUG: Found EinTzofia executable: {exe_path}")
            
            if len(exe_files) > 1:
                logger.warning(f"Multiple EinTzofia {file_type} found, using: {exe_path}")
                logger.debug(f"Other files: {[str(f) for f in exe_files[1:]]}")
                print(f"DEBUG: Multiple EinTzofia files found, using first one")
            
            return str(exe_path)
            
        except Exception as e:
            logger.error(f"Error searching for EinTzofia executable: {e}")
            return ""
    
    # Legacy methods - delegate to wrapped os_class
    def get_EinTzofia_path(self):
        """Get EinTzofia path from config service (overriding legacy implementation)."""
        if self.config_service:
            path = self.config_service.get("general", "eintzofia_path", "")
            if path:
                return path
        
        # Fallback to legacy implementation if no config service or no path in config
        return self.legacy_os.get_EinTzofia_path()
    
    def get_temp_dir_path(self):
        """Get temp directory path using legacy implementation."""
        return self.legacy_os.get_temp_dir_path()
    
    def get_monitor_dir_path(self):
        """Get monitor directory path using legacy implementation."""
        return self.legacy_os.get_monitor_dir_path()
    
    def extract_file(self, zip_path, save_path):
        """Extract file using legacy implementation."""
        return self.legacy_os.extract_file(zip_path, save_path)
    
    def delete_file(self, file_path):
        """Delete file using legacy implementation."""
        return self.legacy_os.delete_file(file_path)
    
    def copy_folder_structure(self, src, dst):
        """Copy folder structure using legacy implementation."""
        return self.legacy_os.copy_folder_structure(src, dst)
    
    def zip_folder(self, folder_path):
        """Create zip file using legacy implementation."""
        return self.legacy_os.zip_folder(folder_path)
    
    def delete_folder_by_path(self, folder_path):
        """Delete folder using legacy implementation."""
        return self.legacy_os.delete_folder_by_path(folder_path)
    
    def find_monitor_executable(self, directory):
        """Find monitor executable using legacy implementation."""
        return self.legacy_os.find_monitor_executable(directory)
    
    def create_shortcut_and_move_to_startup(self, file_path):
        """Create startup shortcut using legacy implementation."""
        return self.legacy_os.create_shortcut_and_move_to_startup(file_path)
    
    def delete_old_shortcuts(self, shortcut_name):
        """Delete old shortcuts using legacy implementation."""
        return self.legacy_os.delete_old_shortcuts(shortcut_name)
    
    def close_then_open_file(self, file_path):
        """Close then open file using legacy implementation."""
        return self.legacy_os.close_then_open_file(file_path)
