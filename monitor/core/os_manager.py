import os
import sys
import platform
import os
import sys
import platform
import json
import re
from pathlib import Path
from monitor.log_setup import get_logger

# Import the legacy os_manager class via package so PyInstaller can discover it
from monitor.legacy_code import os_manager as LegacyOSManager


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

    def get_data_dir_path(self):
        """Get data directory path using legacy implementation."""
        return self.legacy_os.get_data_dir_path()
    
    def get_eintzofia_internal_contents(self):
        """Get EinTzofia internal contents using legacy implementation."""
        return self.legacy_os.get_eintzofia_internal_contents()

    def find_missing_eintzofia_contents(self, manifest):
        """Find missing EinTzofia contents based on the provided manifest."""
        return self.legacy_os.find_missing_eintzofia_contents(manifest)

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
    
    def get_path_to_startup_folder(self):
        """Get the startup folder path (wrapper for legacy method)."""
        return self.legacy_os.get_path_to_startup_folder()
    
    def check_configuration_changed(self):
        """
        Check if any camera folders or configfile.json in EinTzofia's _internal/temp directory have changed.
        
        Camera folders are identified by IP address pattern (e.g., "192.168.1.100").
        configfile.json is tracked under the reserved key "_configfile".
        Timestamps are saved to a JSON file in the monitor's data directory and persist between program runs.
        
        Returns:
            bool: True if any tracked item changed since last check, False otherwise
        """
        logger = get_logger("monitor.core.os_manager")
        
        temp_dir = Path(self.get_temp_dir_path())

        if not temp_dir.exists():
            logger.debug(f"Temp directory not found: {temp_dir}")
            print(f"DEBUG: Temp directory not found: {temp_dir}")
            return False
        
        # Path for saved timestamps file in monitor's data directory
        monitor_data_dir = Path(self.get_monitor_dir_path()) / "data"
        timestamps_file = monitor_data_dir / "eintzofia_timestamps.json"
        
        # IP address pattern (basic validation for camera folder names)
        ip_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        
        current_timestamps = {}
        
        try:
            # Find all directories that match IP address pattern
            for item in temp_dir.iterdir():
                if item.is_dir() and ip_pattern.match(item.name):
                    # Get most recent mtime across folder + all files inside it
                    timestamp = self._get_folder_timestamp(item)
                    current_timestamps[item.name] = timestamp
                    
            logger.debug(f"Found {len(current_timestamps)} camera folders in {temp_dir}")
            print(f"DEBUG: Found {len(current_timestamps)} camera folders in {temp_dir}")

            # Also track configfile.json in the temp directory
            configfile = temp_dir / "configfile.json"
            if configfile.exists():
                current_timestamps["_configfile"] = configfile.stat().st_mtime
                logger.debug(f"Tracking configfile.json mtime: {current_timestamps['_configfile']}")
            else:
                logger.debug("configfile.json not found in temp directory")

            # Load saved timestamps from file in monitor's data directory
            saved_timestamps = {}
            if timestamps_file.exists():
                try:
                    with open(timestamps_file, 'r') as f:
                        saved_timestamps = json.load(f)
                    logger.debug(f"Loaded saved timestamps from {timestamps_file}")
                    print(f"DEBUG: Loaded saved timestamps from {timestamps_file}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Error reading timestamps file: {e}")
                    print(f"DEBUG: Error reading timestamps file: {e}")
                    saved_timestamps = {}
            
            # If no saved timestamps (first run), save current state and return False
            if not saved_timestamps:
                self._save_timestamps(timestamps_file, current_timestamps)
                logger.debug("First check - saved camera folder timestamps to monitor data directory")
                print("DEBUG: First check - saved camera folder timestamps to monitor data directory")
                return False
            
            # Check for changes
            changed = False
            
            # Check if any existing folders have newer timestamps
            for folder_name, current_time in current_timestamps.items():
                saved_time = saved_timestamps.get(folder_name, 0)
                print(f"DEBUG: Checking folder {folder_name} - current time: {current_time}, saved time: {saved_time}")
                if current_time > saved_time:
                    logger.debug(f"Configuration item changed: {folder_name}")
                    print(f"DEBUG: *** Configuration item changed: {folder_name}")
                    changed = True
            
            # Check if any folders were added or removed
            if set(current_timestamps.keys()) != set(saved_timestamps.keys()):
                logger.debug("Configuration item list changed")
                print("DEBUG: Configuration item list changed")
                changed = True  
            
            # Save updated timestamps to monitor's data directory
            if changed:
                print("DEBUG: Configuration changes detected - updating timestamps file")
                self._save_timestamps(timestamps_file, current_timestamps)
            else:
                print("DEBUG: No configuration changes detected")
            return changed
            
        except Exception as e:
            logger.error(f"Error checking camera folders: {e}")
            print(f"DEBUG: Error checking camera folders: {e}")
            return False
    
    def _get_folder_timestamp(self, folder: Path) -> float:
        """
        Return the most recent mtime of the two specific camera image files inside the folder.

        Only checks:
          - {ip}.jpeg / {ip}.jpg / {ip}.png
          - {ip}_regions.jpeg / {ip}_regions.jpg / {ip}_regions.png
        """
        _IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png"]
        ip = folder.name
        max_mtime = folder.stat().st_mtime
        candidate_names = (
            [f"{ip}{ext}" for ext in _IMAGE_EXTENSIONS]
            + [f"{ip}_regions{ext}" for ext in _IMAGE_EXTENSIONS]
        )
        try:
            for name in candidate_names:
                candidate = folder / name
                if candidate.is_file():
                    max_mtime = max(max_mtime, candidate.stat().st_mtime)
        except OSError:
            pass
        return max_mtime

    def _save_timestamps(self, file_path, timestamps):
        """
        Save timestamps to JSON file.
        
        Args:
            file_path: Path to save the timestamps file
            timestamps: Dictionary of folder timestamps to save
        """
        logger = get_logger("monitor.core.os_manager")
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save timestamps to JSON file
            with open(file_path, 'w') as f:
                json.dump(timestamps, f, indent=2)
            
            logger.debug(f"Saved {len(timestamps)} camera folder timestamps to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving timestamps file: {e}")
