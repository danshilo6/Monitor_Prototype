"""Logging configuration for the Monitor Prototype application"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_application_logging(log_level: int = logging.INFO, log_dir: Optional[Path] = None) -> None:
    """
    Configure logging for the entire application.
    
    This should be called once at application startup to set up all logging handlers.
    After this, components can use logging.getLogger("component.name") anywhere.
    
    Args:
        log_level: Minimum log level (default: INFO)
        log_dir: Directory for log files (default: ./logs)
    """
    
    # Create logs directory
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers (useful for testing)
    root_logger.handlers.clear()
    
    # 1. Main application handler - all logs
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", 
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(simple_formatter)
    root_logger.addHandler(app_handler)
    
    # 2. Error handler - errors only (separate file for critical issues)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # 3. Console handler for development (optional)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
    root_logger.addHandler(console_handler)


def setup_separate_component_logging(log_level: int = logging.INFO, log_dir: Optional[Path] = None) -> None:
    """
    Alternative setup with separate log files for different components.
    
    Creates separate log files for:
    - GUI components (ui.log)
    - Logic components (logic.log) 
    - Configuration changes (config.log)
    - Errors from all components (errors.log)
    
    Args:
        log_level: Minimum log level (default: INFO)
        log_dir: Directory for log files (default: ./logs)
    """
    
    # Create logs directory
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    
    # 1. GUI components logger
    gui_handler = logging.handlers.RotatingFileHandler(
        log_dir / "ui.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    gui_handler.setLevel(log_level)
    gui_handler.setFormatter(simple_formatter)
    
    gui_logger = logging.getLogger("gui")
    gui_logger.addHandler(gui_handler)
    gui_logger.setLevel(log_level)
    gui_logger.propagate = False  # Don't propagate to root logger
    
    # 2. Logic components logger
    logic_handler = logging.handlers.RotatingFileHandler(
        log_dir / "logic.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    logic_handler.setLevel(log_level)
    logic_handler.setFormatter(simple_formatter)
    
    logic_logger = logging.getLogger("logic")
    logic_logger.addHandler(logic_handler)
    logic_logger.setLevel(log_level)
    logic_logger.propagate = False
    
    # 3. Configuration changes logger
    config_handler = logging.handlers.RotatingFileHandler(
        log_dir / "config.log",
        maxBytes=5 * 1024 * 1024,  # Smaller file for config changes
        backupCount=3
    )
    config_handler.setLevel(log_level)
    config_handler.setFormatter(simple_formatter)
    
    config_logger = logging.getLogger("config")
    config_logger.addHandler(config_handler)
    config_logger.setLevel(log_level)
    config_logger.propagate = False
    
    # 4. Global error handler - catches errors from ALL loggers
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # 5. Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger with consistent naming.
    
    Usage examples:
    - get_logger("gui.main_window")
    - get_logger("gui.settings.general")  
    - get_logger("logic.monitoring")
    - get_logger("config.service")
    
    Args:
        name: Logger name, preferably hierarchical (e.g., "gui.main_window")
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience functions for common logging patterns
def log_startup_event(component_name: str, message: str) -> None:
    """Log application startup events"""
    logger = logging.getLogger(f"startup.{component_name}")
    logger.info(f"[STARTUP] {message}")


def log_user_action(component_name: str, action: str, details: str = "") -> None:
    """Log user interface interactions"""
    logger = logging.getLogger(f"gui.{component_name}")
    full_message = f"[USER ACTION] {action}"
    if details:
        full_message += f" - {details}"
    logger.info(full_message)


def log_config_change(setting_name: str, old_value: str, new_value: str) -> None:
    """Log configuration changes"""
    logger = logging.getLogger("config.changes")
    logger.info(f"[CONFIG] {setting_name}: '{old_value}' → '{new_value}'")


def log_error_with_context(component_name: str, error_message: str, exception: Exception = None) -> None:
    """Log errors with additional context"""
    logger = logging.getLogger(f"error.{component_name}")
    if exception:
        logger.error(f"[ERROR] {error_message}: {str(exception)}", exc_info=True)
    else:
        logger.error(f"[ERROR] {error_message}")
