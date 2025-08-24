import sys
import argparse
import platform
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
from pathlib import Path
import time


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
        # Set EinTzofia path if first run (before any other detection logic)
        config_service.set_eintzofia_path_if_first_run(find_eintzofia_path)
        
        # Get Ein Tzofia program path from config
        eintzofia_path = config_service.get("general", "eintzofia_path", "")
        print(f"DEBUG: Retrieved eintzofia_path = '{eintzofia_path}'")
        
        # Auto-detect if not configured
        if not eintzofia_path:
            logger.info("EinTzofia path not configured, attempting auto-detection...")
            eintzofia_path = find_eintzofia_path()
            
            if eintzofia_path:
                # Save the auto-detected path to config
                config_service.set("general", "eintzofia_path", eintzofia_path)
                logger.info(f"Auto-detected and saved EinTzofia path: {eintzofia_path}")
            else:
                logger.warning("Could not auto-detect EinTzofia path")
        
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
            logger.warning(f"Ein Tzofia path not found, using fallback: {logs_directory}")
        
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


def authenticate_with_server(config_service: ConfigService, server_manager: ServerManager, parent=None) -> bool:
    """
    Show authentication dialog and handle server authentication before main window loads.
    Returns True if authentication succeeds or local monitoring is allowed, False if cancelled.
    
    Args:
        config_service: Configuration service instance
        server_manager: Server manager instance
        parent: Parent widget for dialogs (optional)
        
    Returns:
        bool: True if authenticated and monitoring should start, False otherwise
    """
    logger = get_logger("monitor.gui.app")
    
    while True:
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

            # Show authentication dialog with styling
            current_location = config_service.get("general", "location_name", "")
            dialog = AuthDialog(current_location, parent)
            
            # Apply styling to the dialog
            style_manager = StyleManager()
            try:
                auth_style = style_manager.load_style("auth_dialog")
                dialog.setStyleSheet(auth_style)
            except FileNotFoundError:
                logger.warning("Auth dialog stylesheet not found, using default styling")
            
            if dialog.exec() == QDialog.Accepted:
                password = dialog.get_password()
                location_name = dialog.get_location_name()
                
                # Save location name to config if provided
                if location_name:
                    config_service.set("general", "location_name", location_name)
                    logger.info(f"Location name saved to configuration: {location_name}")
                    server_manager.update_location_name(location_name)

                if not password:  # Empty password - allow local monitoring
                    logger.info("Empty password provided - proceeding with local monitoring only")
                    return True
                
                # Attempt authentication with server
                logger.info("Attempting server authentication")
                is_password_correct, download_files, signed_id = server_manager.pulse_to_server(
                    password, 
                    return_id=True
                )
                
                if is_password_correct:
                    logger.info("Authentication successful")
                    
                    # Save the signed ID to config
                    if signed_id:
                        config_service.set("device", "signed_id", signed_id)
                        logger.info("Signed ID saved to configuration")
                    
                    return True
                else:
                    logger.warning("Authentication failed - incorrect password")
                    QMessageBox.warning(parent, "Authentication Error", "Incorrect password. Please try again.")
                    # Loop continues to ask for password again
            else:
                logger.info("User cancelled authentication")
                return False
                
        except Exception as e:
            logger.error(f"Error during server authentication: {e}")
            QMessageBox.warning(parent, "Authentication Error", f"Server communication error: {str(e)}")
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


def main() -> int:
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
        
        # Initialize databases
        alert_db, contact_db = create_databases()
        
        # Create server manager for email/SMS services
        server_manager = create_server_manager(config_service)
        
        # --- AUTHENTICATION BEFORE MAIN WINDOW ---
        if not authenticate_with_server(config_service, server_manager):
            logger.info("Authentication failed or cancelled - exiting application")
            return 0

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
        return 1
    except Exception as e:
        logger.critical("Critical error during application startup", exc_info=True)
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

