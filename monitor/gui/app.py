import sys
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir, QFile, QTimer
from PySide6.QtGui import QIcon
from monitor.gui.main_window import MainWindow
from monitor.services.config_service import ConfigService
from monitor.core.thread_manager import ThreadManager, setup_signal_handlers
from monitor.log_setup import init_logging, get_logger
from pathlib import Path


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
        from monitor.services.alert_db import AlertDatabase
        from monitor.services.contact_db import ContactDatabase
        
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
    2. An exe file that starts with "EinTzofia"
    
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
        
        # Look for EinTzofia*.exe files
        exe_files = list(eintzofia_folder.glob("EinTzofia*.exe"))
        
        if not exe_files:
            logger.debug(f"No EinTzofia*.exe files found in: {eintzofia_folder}")
            return ""
        
        # Use the first matching exe file
        exe_path = exe_files[0]
        logger.info(f"Auto-detected EinTzofia executable: {exe_path}")
        
        if len(exe_files) > 1:
            logger.warning(f"Multiple EinTzofia exe files found, using: {exe_path}")
            logger.debug(f"Other files found: {[str(f) for f in exe_files[1:]]}")
        
        return str(exe_path)
        
    except Exception as e:
        logger.error(f"Error auto-detecting EinTzofia path: {e}")
        return ""


def create_thread_manager(config_service: ConfigService, alert_db, contact_db) -> ThreadManager:
    """Create and initialize the thread manager."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Creating thread manager")
    
    try:
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
        
        # Create thread manager with alert database and contact database
        thread_manager = ThreadManager(
            logs_directory=logs_directory,
            data_directory=data_directory,
            alert_db=alert_db,
            contact_db=contact_db
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
        
        # Create and setup thread manager
        thread_manager = create_thread_manager(config_service, alert_db, contact_db)
        
        # Create main window with all dependencies
        window = create_main_window(config_service, alert_db, contact_db, thread_manager)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(thread_manager)
        
        # Connect thread manager signals
        thread_manager.thread_error.connect(
            lambda msg: logger.error(f"Thread error: {msg}")
        )
        
        # Show window
        window.show()
        
        # Start worker threads
        if not thread_manager.start_threads():
            logger.error("Failed to start worker threads")
            return 1
        
        # TODO: REMOVE TEST CODE BEFORE PRODUCTION - Start
        # Start test alert generation if requested
        if args.test_alerts and hasattr(window, '_alert_db'):
            window._alert_db.start_threaded_test_alerts(args.test_interval)
            logger.info(f"Started test alert generation (interval: {args.test_interval}s)")
        # TODO: REMOVE TEST CODE BEFORE PRODUCTION - End
        
        logger.info("Application startup completed, entering main loop")
        
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
            import time
            start_time = time.time()
            while thread_manager.is_running and (time.time() - start_time) < 5:
                QApplication.processEvents()
                time.sleep(0.1)
            
            if thread_manager.is_running:
                logger.warning("Some threads did not stop gracefully")
        
        logger.info("=== Monitor Application Shutdown ===")


if __name__ == "__main__":
    sys.exit(main())

