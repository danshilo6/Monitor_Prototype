import os
import sys
import platform
from pathlib import Path
from monitor.log_setup import get_logger

# Import the legacy os_manager class via package so PyInstaller can discover it
from legacy_code import os_manager as LegacyOSManager


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
        Find EinTzofia executable with the newest version in the specified directory.
        
        Cross-platform function that looks for executable files starting with "EinTzofia":
        - Windows: Searches for EinTzofia*.exe files
        - Linux/Unix: Searches for executable files starting with "EinTzofia"
        
        Finds the executable with the newest version based on the date format dd_mm_yy
        in the filename (e.g., EinTzofia_01_09_25.exe for September 1, 2025).
        
        Args:
            search_dir: Directory to search in
            
        Returns:
            str: Path to EinTzofia executable with newest version, or empty string if not found
        """
        import re
        from datetime import datetime
        
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
                print(f"DEBUG: No EinTzofia {file_type} found in: {search_dir}")
                return ""
            
            
            # If only one file found, return it
            if len(exe_files) == 1:
                exe_path = exe_files[0]
                logger.info(f"Found EinTzofia executable: {exe_path}")
                print(f"DEBUG: Found EinTzofia executable: {exe_path}")
                return str(exe_path)
            
            # Multiple files found - find the one with the newest version date
            newest_file = None
            newest_date = None
            
            # Regex pattern to match date format dd_mm_yy in filename
            date_pattern = r'(\d{2})_(\d{2})_(\d{2})'
            
            for exe_file in exe_files:
                filename = exe_file.name
                match = re.search(date_pattern, filename)
                
                print(f"Found EinTzofia executable: {newest_file}")

                if match:
                    day, month, year = match.groups()
                    try:
                        # Convert 2-digit year to 4-digit (assuming 20xx for years 00-99)
                        full_year = 2000 + int(year)
                        file_date = datetime(full_year, int(month), int(day))
                        
                        if newest_date is None or file_date > newest_date:
                            newest_date = file_date
                            newest_file = exe_file

                        logger.debug(f"Found EinTzofia file with date {day}/{month}/{year}: {filename}")
                        
                    except ValueError as e:
                        logger.warning(f"Invalid date in filename {filename}: {e}")
                        # If date parsing fails, we'll still consider files without dates
                        if newest_file is None:
                            newest_file = exe_file
                else:
                    logger.debug(f"No date pattern found in filename: {filename}")
                    # If no date found and no newest_file yet, use this as fallback
                    if newest_file is None:
                        newest_file = exe_file
            
            if newest_file is None:
                # Fallback to first file if no valid file found
                newest_file = exe_files[0]
                logger.warning(f"No valid EinTzofia file found with date pattern, using first file: {newest_file}")
            else:
                if newest_date:
                    logger.info(f"Found newest EinTzofia executable with date {newest_date.strftime('%d/%m/%Y')}: {newest_file}")
                    print(f"DEBUG: Using newest EinTzofia executable with date {newest_date.strftime('%d/%m/%Y')}: {newest_file}")
                else:
                    logger.info(f"Found EinTzofia executable (no date in filename): {newest_file}")
                    print(f"DEBUG: Using EinTzofia executable (no date pattern): {newest_file}")
                    
                if len(exe_files) > 1:
                    other_files = [str(f) for f in exe_files if f != newest_file]
                    logger.debug(f"Other EinTzofia files found: {other_files}")
            
            print(f"DEBUG: Returning EinTzofia executable path: {newest_file}")
            return str(newest_file)
            
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
