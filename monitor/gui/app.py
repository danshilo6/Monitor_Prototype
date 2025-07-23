import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDir, QFile
from PySide6.QtGui import QIcon
from monitor.gui.main_window import MainWindow
from monitor.services.config_service import ConfigService
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


def create_main_window(config_service: ConfigService) -> MainWindow:
    """Create and configure the main application window."""
    logger = get_logger("monitor.gui.app")
    logger.debug("Creating main window")
    
    try:
        window = MainWindow(config_service)
        logger.info("Main window created successfully")
        return window
    except Exception as e:
        logger.error("Failed to create main window", exc_info=True)
        raise


def main() -> int:
    """Main application entry point."""
    # Initialize logging first
    init_logging(mode="sync")  # Simple synchronous logging
    logger = get_logger("monitor.gui.app")
    
    logger.info("=== Monitor Application Starting ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PySide6 available: {QApplication is not None}")
    
    try:
        # Initialize Qt application
        app = setup_application()
        
        # Initialize services
        config_service = create_services()
        
        # Create main window
        window = create_main_window(config_service)
        window.show()
        
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
        logger.info("=== Monitor Application Shutdown ===")


if __name__ == "__main__":
    sys.exit(main())

