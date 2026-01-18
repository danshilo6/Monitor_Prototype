import sys
import argparse
import platform
import pickle
from pathlib import Path
import time
import re
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox, QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PySide6.QtCore import QDir, QFile, QTimer, Qt
from PySide6.QtGui import QIcon
from monitor.gui.main_window import MainWindow
from monitor.gui.widgets import AuthDialog
from monitor.gui.styles.style_manager import StyleManager
from monitor.services.config_service import ConfigService
from monitor.core.thread_manager import ThreadManager, setup_signal_handlers
from monitor.core.os_manager import OSManager
from monitor.core.server_manager import ServerManager
from monitor.log_setup import init_logging, get_logger
from monitor.services.alert_db import AlertDatabase
from monitor.services.contact_db import ContactDatabase        


def auto_start_eintzofia_with_feedback(config_service, parent_window=None):
    """
    Auto-start EinTzofia with user feedback on failure (when auto-reopen is enabled).
    Uses QTimer to avoid blocking the UI thread.
    
    Args:
        config_service: Configuration service to get EinTzofia path
        parent_window: Parent window for error dialogs (optional)
    """
    logger = get_logger("monitor.gui.app")
    
    def delayed_start():
        """Execute auto-start after UI is fully loaded"""
        try:
            # Check if auto-reopen is enabled
            auto_reopen_enabled = config_service.get("system", "enable_eintzofia_auto_reopen", True)
            if not auto_reopen_enabled:
                logger.info("EinTzofia auto-reopen is disabled, skipping auto-start")
                return
            
            # Get EinTzofia path from config
            eintzofia_path = config_service.get("general", "eintzofia_path", "")
            logger.info(f"Attempting to auto-start EinTzofia: {eintzofia_path}")
            
            if not eintzofia_path:
                logger.info("EinTzofia path not configured, skipping auto-start")
                return
            
            # Create OSManager and try to open EinTzofia
            os_manager = OSManager(config_service)
            success = os_manager.open_file(eintzofia_path)
            
            if success:
                logger.info("EinTzofia auto-started successfully")
            else:
                logger.warning("EinTzofia auto-start failed")
                _show_eintzofia_error(
                    "Failed to launch EinTzofia",
                    f"Could not start EinTzofia automatically.\n\n"
                    f"Path: {eintzofia_path}\n\n"
                    "Please check if the file exists and try using the manual "
                    "'Open/Restart EinTzofia' button in Settings > System.",
                    parent_window
                )
                
        except Exception as e:
            logger.error(f"Error during EinTzofia auto-start: {e}")
            _show_eintzofia_error(
                "EinTzofia startup error",
                f"An unexpected error occurred:\n\n{str(e)}\n\n"
                "You can manually start EinTzofia using the button in Settings > System.",
                parent_window
            )
    
    # Delay the auto-start by 1 second to let UI finish loading
    QTimer.singleShot(1000, delayed_start)


def _show_eintzofia_error(title: str, message: str, parent_window=None):
    """Show EinTzofia error dialog"""
    from PySide6.QtWidgets import QMessageBox
    
    msg_box = QMessageBox(parent_window)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle("EinTzofia Auto-Start Failed")
    msg_box.setText(title)
    msg_box.setDetailedText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def set_app_icon(app: QApplication) -> None:
    """Set the application icon if available."""
    logger = get_logger("monitor.gui.app")
    icon_path = Path(__file__).parent / "icons" / "ecg-monitor.png"
    
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        logger.debug(f"Application icon set from: {icon_path}")
    else:
        logger.warning(f"Application icon not found at: {icon_path}")


def setup_application() -> QApplication:
    """Initialize and configure the Qt application."""
    logger = get_logger("monitor.gui.app")
    logger.info("Initializing Qt application")
    
    try:
        app = QApplication(sys.argv)
        
        # Set application-wide font for Linux compatibility
        if platform.system() == "Linux":
            from PySide6.QtGui import QFont
            font = QFont("DejaVu Sans", 10)
            if not font.exactMatch():
                font = QFont("Liberation Sans", 10)
            if not font.exactMatch():
                font = QFont("Noto Sans", 10)
            if not font.exactMatch():
                font = QFont() # Fallback to system default
                font.setPointSize(10)
            app.setFont(font)
            logger.info(f"Set Linux font: {font.family()}")
        
        set_app_icon(app)
        logger.info("Qt application initialized successfully")
        return app
    except Exception as e:
        logger.error("Failed to initialize Qt application", exc_info=True)
        raise


def create_services():
    """Create and initialize application services."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Initializing application services")
    
    try:
        config_service = ConfigService("config.json")
        logger.info("Configuration service initialized")
        return config_service
    except Exception as e:
        logger.error("Failed to initialize configuration service", exc_info=True)
        raise


def create_databases():
    """Create and initialize database services."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Initializing database services")
    
    try:
        
        alert_db = AlertDatabase()
        contact_db = ContactDatabase()
        
        logger.info("Database services initialized")
        return alert_db, contact_db
    except Exception as e:
        logger.error("Failed to initialize database services", exc_info=True)
        raise


def migrate_location_from_old_settings(config_service: ConfigService) -> None:
    """
    Migrate location from legacy settings.pkl file to config.json.
    
    Checks for settings.pkl in the current directory and extracts the location
    if it hasn't been migrated yet. Only sets migration flag if location is actually extracted.
    
    Args:
        config_service: Configuration service instance to update
    """
    logger = get_logger("monitor.gui.app")
    
    try:
        # Check if migration has already been done
        migration_done = config_service.get("general", "location_extracted_from_old_settings", False)
        if migration_done:
            logger.debug("Location migration from settings.pkl already completed")
            print(f"DEBUG: [Legacy] Location migration from settings.pkl not needed")
            return
        
        # Look for settings.pkl in current directory
        settings_file = Path.cwd() / "settings.pkl"
        if not settings_file.exists():
            logger.debug("No settings.pkl file found - skipping migration")
            print(f"DEBUG: [Legacy] No settings.pkl file found - skipping migration")
            return
        print(f"DEBUG: [Legacy] Found old settings file: {settings_file}")
        logger.info(f"Found legacy settings file: {settings_file}")
        
        # Load the pickle file
        with open(settings_file, 'rb') as f:
            old_settings = pickle.load(f)
        
        # Check if it's a dictionary and has the Location key
        if not isinstance(old_settings, dict):
            logger.warning("settings.pkl does not contain a dictionary")
            print(f"DEBUG: [Legacy] settings.pkl does not contain a dictionary")
            return
        
        if "Location" not in old_settings:
            logger.warning("No 'Location' key found in settings.pkl")
            print(f"DEBUG: [Legacy] No 'Location' key found in settings.pkl")
            return
        
        # Extract location value
        old_location = old_settings["Location"]
        if not old_location or not isinstance(old_location, str):
            logger.warning(f"Invalid location value in settings.pkl: {old_location}")
            print(f"DEBUG: [Legacy] Invalid location value in settings.pkl: {old_location}")
            return
        
        # Set the location in config.json
        config_service.set("general", "location_name", old_location)
        logger.info(f"Migrated location from settings.pkl: '{old_location}'")

        # Only set migration flag when we actually migrated the location
        config_service.set("general", "location_extracted_from_old_settings", True)
        print(f"DEBUG: [Legacy] Location name extracted from old settings file: {old_location}")
        logger.info("Location migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during location migration from settings.pkl: {e}")
        print(f"DEBUG: [Legacy] Error during location migration from settings.pkl: {e}")


def setup_eintzofia_path(config_service: ConfigService) -> None:
    """
    Set up EinTzofia path if not already configured.
    
    Uses auto-detection if first run, or attempts detection if path is empty.
    
    Args:
        config_service: Configuration service instance to update
    """
    logger = get_logger("monitor.gui.app")
    
    try:
        # Get EinTzofia program path from config
        eintzofia_path = config_service.get("general", "eintzofia_path", "")
        print(f"DEBUG: Current EinTzofia path in config: '{eintzofia_path}'")
        logger.debug(f"Current EinTzofia path in config: '{eintzofia_path}'")
        
        # Auto-detect if not configured

        print("DEBUG: EinTzofia path not configured, attempting auto-detection...")
        logger.info("EinTzofia path not configured, attempting auto-detection...")
        eintzofia_path = find_eintzofia_path() # this method uses os_manager's method
        
        if eintzofia_path:
            # Save the auto-detected path to config
            config_service.set("general", "eintzofia_path", eintzofia_path)
            print(f"DEBUG: Auto-detected and saved EinTzofia path: {eintzofia_path}")
            logger.info(f"Auto-detected and saved EinTzofia path: {eintzofia_path}")
        else:
            print("DEBUG: Could not auto-detect EinTzofia path")
            logger.warning("Could not auto-detect EinTzofia path")
            
    except Exception as e:
        print(f"DEBUG: Error setting up EinTzofia path: {e}")
        logger.error(f"Error setting up EinTzofia path: {e}")


def extract_eintzofia_version(config_service: ConfigService) -> None:
    """
    Extract EinTzofia version from executable filename and save to config.
    
    Looks for date pattern dd_mm_yy in the EinTzofia executable name and
    saves it to the configuration as 'eintzofia_version'.
    
    Args:
        config_service: Configuration service instance to update
    """
    logger = get_logger("monitor.gui.app")
    
    try:
        # Get EinTzofia path from config
        eintzofia_path = config_service.get("general", "eintzofia_path", "")
        
        if not eintzofia_path:
            logger.debug("No EinTzofia path configured, skipping version extraction")
            return
        
        # Extract filename from path
        eintzofia_filename = Path(eintzofia_path).name
        logger.debug(f"Extracting version from filename: {eintzofia_filename}")
        
        # Pattern to match dd_mm_yy format (two digits, underscore, two digits, underscore, two digits)
        date_pattern = r'\d{2}_\d{2}_\d{2}'
        match = re.search(date_pattern, eintzofia_filename)
        
        if match:
            version_date = match.group()
            print(f"DEBUG: Found EinTzofia version: {version_date}")
            logger.info(f"Found EinTzofia version: {version_date}")
            
            # Save version to config
            config_service.set("versions", "eintzofia_version", version_date)
            logger.info(f"Saved EinTzofia version to config: {version_date}")
        else:
            logger.warning(f"No version date found in EinTzofia filename: {eintzofia_filename}")
            print(f"DEBUG: No version date found in EinTzofia filename: {eintzofia_filename}")
            
    except Exception as e:
        logger.error(f"Error extracting EinTzofia version: {e}")
        print(f"DEBUG: Error extracting EinTzofia version: {e}")


def check_eintzofia_version_outdated(config_service: ConfigService) -> None:
    """
    Check if EinTzofia version is older than 27-08-25 and log a warning if so.
    
    Compares the version date from config against the cutoff date 27-08-25.
    Versions older than this date (not including 27-08-25 itself) are considered outdated.
    
    Args:
        config_service: Configuration service instance to read version from
    """
    from datetime import datetime
    logger = get_logger("monitor.gui.app")
    
    try:
        # Get EinTzofia version from config
        version_date_str = config_service.get("versions", "eintzofia_version", "")
        
        if not version_date_str:
            logger.debug("No EinTzofia version found in config, skipping version check")
            return False
        
        # Parse the version date (dd_mm_yy format)
        try:
            # Convert dd_mm_yy to datetime object
            day, month, year = version_date_str.split('_')
            # Assuming yy format means 20yy (e.g., 25 = 2025)
            full_year = 2000 + int(year)
            version_date = datetime(full_year, int(month), int(day))
            
            # Define cutoff date: 27-08-25 (27th August 2025)
            cutoff_date = datetime(2025, 8, 27)
            
            logger.debug(f"Comparing EinTzofia version {version_date_str} ({version_date.strftime('%Y-%m-%d')}) against cutoff {cutoff_date.strftime('%Y-%m-%d')}")
            
            if version_date < cutoff_date:
                warning_msg = f"EinTzofia version {version_date_str} is outdated (older than 27-08-25)"
                logger.warning(warning_msg)
                print(f"DEBUG: [Legacy] WARNING - {warning_msg}")
                return True
            else:
                logger.info(f"EinTzofia version {version_date_str} is current")
                print(f"DEBUG: [Legacy] EinTzofia version {version_date_str} is current")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid version date format '{version_date_str}': {e}")
            print(f"DEBUG: [Legacy] Invalid version date format '{version_date_str}': {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking EinTzofia version: {e}")
        print(f"DEBUG: Error checking EinTzofia version: {e}")
        return False


def find_eintzofia_path() -> str:
    """
    Auto-detect EinTzofia executable path.
    
    Looks in project root's parent folder for:
    1. A folder named "EinTzofia"
    2. An executable file that starts with "EinTzofia"
    
    Returns:
        str: Path to EinTzofia executable, or empty string if not found
    """
    logger = get_logger("monitor.gui.app")
    
    try:
        # Start from project root's parent
        project_root = Path.cwd()
        parent_dir = project_root.parent
        
        logger.debug(f"Searching for EinTzofia in: {parent_dir}")
        
        # Look for EinTzofia folder
        eintzofia_folder = parent_dir / "EinTzofia"
        if not eintzofia_folder.exists() or not eintzofia_folder.is_dir():
            logger.debug(f"EinTzofia folder not found at: {eintzofia_folder}")
            return ""
        
        logger.debug(f"Found EinTzofia folder: {eintzofia_folder}")
        
        # Use OSManager to find the executable
        os_manager = OSManager()
        return os_manager.find_eintzofia_executable(eintzofia_folder)
        
    except Exception as e:
        logger.error(f"Error auto-detecting EinTzofia path: {e}")
        return ""


def create_thread_manager(config_service: ConfigService, alert_db, contact_db, server_manager=None) -> ThreadManager:
    """Create and initialize the thread manager."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Creating thread manager")
    
    try:
        # Get EinTzofia program path from config (should already be set up)
        eintzofia_path = config_service.get("general", "eintzofia_path", "")
        logger.debug(f"Retrieved eintzofia_path = '{eintzofia_path}'")
        
        if eintzofia_path:
            # Logs database is in {exe_parent_directory}/_internal/temp/
            exe_parent_dir = Path(eintzofia_path).parent
            logs_directory = exe_parent_dir / "_internal" / "temp"
            logger.info(f"Using logs directory: {logs_directory}")
            logger.info(f"EinTzofia executable: {eintzofia_path}")
            
            # Check if the logs directory exists
            if not logs_directory.exists():
                logger.warning(f"Logs directory doesn't exist yet: {logs_directory}")
                logger.info("LogReader will wait for logs database files to be created")
        else:
            # Fallback to project root for development/testing
            logs_directory = Path.cwd()
            logger.warning(f"EinTzofia path not found, using fallback: {logs_directory}")
        
        # Data directory is always in project root
        data_directory = Path.cwd() / "data"
        
        # Create thread manager with alert database, contact database, and config service
        thread_manager = ThreadManager(
            logs_directory=logs_directory,
            data_directory=data_directory,
            alert_db=alert_db,
            contact_db=contact_db,
            config_service=config_service,
            server_manager=server_manager
        )
        
        logger.info("Thread manager created successfully")
        return thread_manager
    except Exception as e:
        logger.error("Failed to create thread manager", exc_info=True)
        raise


def create_main_window(config_service: ConfigService, alert_db, contact_db, thread_manager=None) -> MainWindow:
    """Create and configure the main application window."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Creating main window")
    
    try:
        window = MainWindow(config_service, alert_db, contact_db, thread_manager)
        logger.info("Main window created successfully")
        return window
    except Exception as e:
        logger.error("Failed to create main window", exc_info=True)
        raise


def create_server_manager(config_service: ConfigService) -> ServerManager:
    """Create and initialize the server manager."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Creating server manager")
    
    try:
        # Create OS manager instance  
        os_manager = OSManager(config_service)
        # Create server manager with dependencies
        server_manager = ServerManager(config_service, os_manager)
        
        logger.info("Server manager created successfully")
        return server_manager
        
    except Exception as e:
        logger.error(f"Failed to create server manager: {e}")
        raise

def setup_location_name(config_service: ConfigService) -> None:
    """
    Setup location name in config using device ID if not already configured.
    Uses first 5 and last 5 characters of device ID for a unique but shorter identifier.
    
    Args:
        config_service: Configuration service instance to update
    """
    logger = get_logger("monitor.gui.app")
    
    try:
        # Get location name from config
        location_name = config_service.get("general", "location_name", "")
        
        if not location_name:
            # Create OS manager to get unique device ID
            os_manager = OSManager(config_service)
            device_id = os_manager.generate_device_id()
            
            # Use first 5 and last 5 characters of device ID
            if len(device_id) >= 10:
                location_name = device_id[:5] + device_id[-5:]
            else:
                # If device ID is shorter than 10 chars, use the whole ID
                location_name = device_id
            
            # Save to config
            config_service.set("general", "location_name", location_name)
            logger.info(f"Location name was empty, set to device ID subset '{location_name}' in config")
            print(f"DEBUG: Location name set to device ID subset: {location_name}")
        else:
            logger.debug(f"Location name already configured: {location_name}")
            print(f"DEBUG: Location name already configured: {location_name}")
            
    except Exception as e:
        logger.error(f"Error setting up location name: {e}")
        print(f"DEBUG: Error setting up location name: {e}")

def authenticate_with_server_auto(config_service: ConfigService, server_manager: ServerManager, parent=None) -> bool:
    """
    Automated authentication with server using predefined password and config location.
    Bypasses the authentication dialog and uses hardcoded credentials.
    
    Args:
        config_service: Configuration service instance
        server_manager: Server manager instance
        parent: Parent widget for dialogs (optional, unused in auto mode)
        
    Returns:
        bool: True if authenticated successfully, False otherwise
    """
    logger = get_logger("monitor.gui.app")
    # TODO REMOVE THIS METHOD -- migration from old version
    try:
        # Check if device ID exists and is approved on server
        id_exists, id_approved = server_manager.check_id_exists_and_approved()
        logger.info(f"Server check - ID exists: {id_exists}, ID approved: {id_approved}")
        
        id = config_service.get("device", "signed_id", "")
        print(f"\nSIGNED_ID: {id}\n")
        if not id:
            id = ""
        
        # If already approved, proceed with monitoring
        if id_approved and id_exists and id != "":
            logger.info("Device already approved - authentication successful")
            return True

        # Get location name from config
        location_name = config_service.get("general", "location_name", "")
        print(f"LOCATION NAME: {location_name}\n")

        # Use hardcoded password
        password = "Bulltech2023"
        
        logger.info(f"Auto-authenticating with location: '{location_name}'")
        
        # Update server manager with location name if available
        if location_name:
            server_manager.update_location_name(location_name)
            logger.info(f"Location name updated in server manager: {location_name}")

        # Attempt authentication with server
        logger.info("Attempting automated server authentication")
        is_password_correct, download_files, signed_id = server_manager.pulse_to_server(
            password, 
            return_id=True
        )
        
        if is_password_correct:
            logger.info("Automated authentication successful")
            
            # Save the signed ID to config
            if signed_id:
                config_service.set("device", "signed_id", signed_id)
                logger.info("Signed ID saved to configuration")
            
            return True
        else:
            logger.error("Automated authentication failed - incorrect password")
            return False
                
    except Exception as e:
        logger.error(f"Error during automated server authentication: {e}")
        return False

def authenticate_with_server(config_service: ConfigService, server_manager: ServerManager, parent=None) -> bool:
    """
    Authenticate with server using hardcoded password and config location.
    Returns True if authentication succeeds, False otherwise.
    
    Args:
        config_service: Configuration service instance
        server_manager: Server manager instance
        parent: Parent widget for dialogs (optional, unused)
        
    Returns:
        bool: True if authenticated and monitoring should start, False otherwise
    """
    logger = get_logger("monitor.gui.app")
    
    try:
        # Check if device ID exists and is approved on server
        id_exists, id_approved = server_manager.check_id_exists_and_approved()
        logger.info(f"Server check - ID exists: {id_exists}, ID approved: {id_approved}")
        
        id = config_service.get("device", "signed_id", "")
        print(f"\nSIGNED_ID: {id}\n")
        if not id:
            id = ""
        
        # If already approved, proceed with monitoring
        if id_approved and id_exists and id != "":
            logger.info("Device already approved - authentication successful")
            return True

        # Get location name from config (should already be set by setup_location_name)
        location_name = config_service.get("general", "location_name", "")
        print(f"LOCATION NAME: {location_name}\n")

        # Use hardcoded password
        password = "Bulltech2023"
        
        logger.info(f"Auto-authenticating with location: '{location_name}'")
        
        # Update server manager with location name
        server_manager.update_location_name(location_name)
        logger.info(f"Location name updated in server manager: {location_name}")

        # Attempt authentication with server
        logger.info("Attempting automated server authentication")
        print("DEBUG: Starting authentication pulse to server...")
        is_password_correct, download_files, signed_id = server_manager.pulse_to_server(
            password, 
            return_id=True
        )
        print(f"DEBUG: Authentication pulse completed - Password correct: {is_password_correct}")
        
        if is_password_correct:
            logger.info("Automated authentication successful")
            
            # Save the signed ID to config
            if signed_id:
                config_service.set("device", "signed_id", signed_id)
                logger.info("Signed ID saved to configuration")
            
            # Handle download flags from authentication pulse using decision engine logic
            if download_files:
                logger.info("Handling download flags from authentication pulse")
                print(f"DEBUG: Download flags from authentication: {download_files}")
                
                # Import and use the decision engine's download handling methods
                from monitor.core.decision_engine import DecisionEngine
                
                # Create a temporary decision engine instance to use its methods
                temp_decision_engine = DecisionEngine(
                    config_service=config_service,
                    server_manager=server_manager,
                    logs_directory=Path("logs"),  # Minimal path needed
                    data_directory=Path("data")   # Minimal path needed
                )
                
                # Use decision engine's download handling logic
                if temp_decision_engine._save_download_flags(download_files):
                    logger.info("Download flags saved - preparing monitor downloader")
                    temp_decision_engine._prepare_monitor_downloader()
            
            return True
        else:
            logger.error("Automated authentication failed - incorrect password")
            return False
                
    except Exception as e:
        logger.error(f"Error during automated server authentication: {e}")
        return False


def _show_auth_error(parent_window, message: str):
    """Show authentication error dialog."""
    msg_box = QMessageBox(parent_window)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle("Authentication Error")
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def start_background_operations(app, window, config_service, server_manager, thread_manager, args):
    """
    Handle EinTzofia startup and thread initialization.
    
    Args:
        app: QApplication instance
        window: Main window instance  
        config_service: Configuration service
        server_manager: Server manager for authentication
        thread_manager: Thread manager instance
        args: Command line arguments
    """
    logger = get_logger("monitor.gui.app")
    
    # Auto-start EinTzofia with user feedback
    auto_start_eintzofia_with_feedback(config_service, window)
    
    # Start worker threads
    if not thread_manager.start_threads():
        logger.error("Failed to start worker threads")
        app.quit()
        return
    
    # TODO: REMOVE TEST CODE BEFORE PRODUCTION - Start
    # Start test alert generation if requested
    if args.test_alerts and hasattr(window, '_alert_db'):
        window._alert_db.start_threaded_test_alerts(args.test_interval)
        logger.info(f"Started test alert generation (interval: {args.test_interval}s)")
    # TODO: REMOVE TEST CODE BEFORE PRODUCTION - End
    
    logger.info("Application startup completed")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Monitor Prototype Application")
    # TODO: REMOVE TEST CODE BEFORE PRODUCTION - Start
    parser.add_argument(
        "--test-alerts", 
        action="store_true", 
        help="Enable test alert generation for GUI testing"
    )
    parser.add_argument(
        "--test-interval", 
        type=float, 
        default=3.0, 
        help="Interval between test alerts in seconds (default: 3.0)"
    )
    # TODO: REMOVE TEST CODE BEFORE PRODUCTION - End
    return parser.parse_args()


# COMMENTED OUT - Manifest processing now handled by separate downloader
# def check_and_process_manifest_updates(config_service, server_manager) -> None:
#     """
#     Check if manifest processing is needed and process updates if flagged.
#     
#     Args:
#         config_service: Configuration service instance
#         server_manager: Server manager instance
#     """
#     logger = get_logger("monitor.gui.app")
#     
#     try:
#         # Check if manifest processing flag is set
#         process_manifest = config_service.get("system", "process_manifest_on_startup", False)
#         
#         if process_manifest:
#             logger.info("Manifest processing flag detected - processing manifest updates...")
#             print("DEBUG: Processing manifest updates on startup...")
#             
#             # Clear the flag first to prevent repeated processing
#             config_service.set("system", "process_manifest_on_startup", False)
#             logger.info("Manifest processing flag cleared")
#             
#             try:
#                 success = server_manager.process_manifest_updates()
#                 if success:
#                     logger.info("Manifest processing completed successfully")
#                     print("DEBUG: Manifest processing completed successfully")
#                 else:
#                     logger.warning("Manifest processing failed or incomplete")
#                     print("DEBUG: Manifest processing failed or incomplete")
#             except Exception as e:
#                 logger.error(f"Exception during manifest processing: {e}")
#                 print(f"DEBUG: Exception during manifest processing: {e}")
#         else:
#             logger.debug("No manifest processing needed")
#             print("DEBUG: No manifest processing flag set")
#     
#     except Exception as e:
#         logger.error(f"Error checking manifest processing flag: {e}")
#         print(f"DEBUG: Error checking manifest processing flag: {e}")


def main() -> int:
    print("Starting Monitor Application...")

    """Main application entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize logging first
    init_logging(mode="sync")  # Simple synchronous logging
    logger = get_logger("monitor.gui.app")
    
    logger.info("=== Monitor Application Starting ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PySide6 available: {QApplication is not None}")
    
    thread_manager = None
    
    try:
        # Initialize Qt application
        app = setup_application()
        
        # Initialize services
        config_service = create_services()
        
        # Migrate location from old settings.pkl if needed
        migrate_location_from_old_settings(config_service)
        
        # Setup location name from device ID if not configured
        setup_location_name(config_service)

        # Setup EinTzofia path if needed
        setup_eintzofia_path(config_service)
        
        # Extract EinTzofia version from executable name
        extract_eintzofia_version(config_service)
        
        # Check if EinTzofia version is outdated
        need_auto_update = check_eintzofia_version_outdated(config_service)
        
        # Initialize databases
        alert_db, contact_db = create_databases()
        
        # Create server manager for email/SMS services
        server_manager = create_server_manager(config_service)
        
        # ---------------------- AUTHENTICATION BEFORE MAIN WINDOW ----------------------
        
        
        
        # Set server URL directly from config
        server_url = config_service.get("general", "server_url", "http://ec2-13-49-189-10.eu-north-1.compute.amazonaws.com:5001")   
        server_manager.update_server_url(server_url)
        print(f"Chosen server: {server_manager.legacy_server.base_url}")
        # connect to server
        if need_auto_update: # TODO REMOVE THIS PART (LEAVE ONLY THE ELSE PART) -- migration from old version
            authentication = authenticate_with_server_auto(config_service, server_manager)
        else:
            authentication = authenticate_with_server(config_service, server_manager)
        if not authentication:
            logger.info("Authentication failed or cancelled - exiting application")
            return 0

        # ---------------------- MANIFEST PROCESSING CHECK ----------------------
        
        # COMMENTED OUT - Manifest processing now handled by separate downloader
        # Check and process manifest updates before starting main application
        # check_and_process_manifest_updates(config_service, server_manager)

        # ---------------------- AUTO-UPDATE CHECK AFTER AUTHENTICATION ----------------------
        
        if need_auto_update:
            logger.info("Auto-update needed - downloading EinTzofia from server")
            print("DEBUG: Auto-update needed - downloading EinTzofia from server")
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(server_manager.download_exefiles(delete_old_file=True))
                loop.close()
                logger.info("EinTzofia auto-update download completed successfully")
                print("DEBUG: EinTzofia auto-update download completed successfully")

                restart_enabled = config_service.get("system", "enable_restart", True)
                if restart_enabled:
                    os_manager = OSManager(config_service)
                    logger.info("Executing immediate restart after auto-update")
                    print("DEBUG: Executing immediate restart after auto-update")
                    os_manager.restart_pc()
                else:
                    logger.info("enable_restart is set to False - skipping immediate restart after auto-update")
                    print("DEBUG: Skipping immediate restart after auto-update because enable_restart is False")

            except Exception as e:
                logger.error(f"Failed to download EinTzofia auto-update: {e}")
                print(f"DEBUG: Failed to download EinTzofia auto-update: {e}")

        # -------------------------------------------------------------------------------

        # Create and setup thread manager with server manager
        thread_manager = create_thread_manager(config_service, alert_db, contact_db, server_manager)
        
        # Create main window with all dependencies
        window = create_main_window(config_service, alert_db, contact_db, thread_manager)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(thread_manager)
        
        # Connect thread manager signals
        thread_manager.thread_error.connect(
            lambda msg: logger.error(f"Thread error: {msg}")
        )
        
        # Show window first - UI is now responsive
        window.show()
        
        # Start background operations after short delay
        QTimer.singleShot(100, lambda: start_background_operations(
            app, window, config_service, server_manager, thread_manager, args
        ))
        
        logger.info("UI ready, background startup initiated")
        
        # Start the application event loop
        exit_code = app.exec()
        
        logger.info(f"Application exiting with code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
        print("Application interrupted by user (Ctrl+C)")
        return 1
    except Exception as e:
        logger.critical("Critical error during application startup", exc_info=True)
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to continue...")  # Keep console open
        return 1
    finally:
        # Ensure threads are stopped gracefully
        if thread_manager:
            logger.info("Stopping worker threads...")
            thread_manager.stop_threads()
            
            # Wait for threads to stop (up to 5 seconds)
           
            start_time = time.time()
            while thread_manager.is_running and (time.time() - start_time) < 5:
                QApplication.processEvents()
                time.sleep(0.1)
            
            if thread_manager.is_running:
                logger.warning("Some threads did not stop gracefully")
        
        logger.info("=== Monitor Application Shutdown ===")


if __name__ == "__main__":
    sys.exit(main())

