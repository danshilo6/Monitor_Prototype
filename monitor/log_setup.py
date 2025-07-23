"""
log_setup.py  –  Central‑logging helper for the *monitor* project
===============================================================

• Single public API  →  init_logging(), reset_logging(), get_logger()
• Two rotating UTF‑8 files: app.log (INFO+) and errors.log (ERROR+)
• Optional console output (env‑controlled)
• Async mode via QueueListener with daemon thread
• Captures warnings and uncaught exceptions
• Thread‑safe re‑initialisation for unit tests
"""

from __future__ import annotations

import atexit
import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path
from queue import Queue
from typing import Literal, Optional

# ────────────────────────────────────────────────────────────────────────────
# Globals
# ────────────────────────────────────────────────────────────────────────────
_INITIALISED = False
_LOCK = threading.Lock()
_QUEUE_LISTENER: Optional[logging.handlers.QueueListener] = None

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def _env(name: str, default: str) -> str:
    """
    Return environment variable with MONITOR_ prefix.
    
    Args:
        name: The variable name (e.g., "LOG_LEVEL" becomes "MONITOR_LOG_LEVEL")
        default: Default value if environment variable is not set
        
    Returns:
        The environment variable value or default
    """
    return os.getenv(f"MONITOR_{name}", default)


def _log_level_from_env() -> int:
    """
    Get the logging level from environment variable MONITOR_LOG_LEVEL.
    
    Supports standard Python logging levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    Defaults to INFO if environment variable is not set or invalid.
    
    Returns:
        Integer constant from the logging module (e.g., logging.INFO = 20)
    """
    level_str = _env("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def _log_dir_from_env() -> Path:
    """
    Get the log directory from environment variable MONITOR_LOG_DIR.
    
    Defaults to "logs" directory in current working directory.
    Expands user home directory (~) if used in path.
    
    Returns:
        Path object representing the log directory
    """
    return Path(_env("LOG_DIR", "logs")).expanduser()


def _enable_console_logging(level: int) -> bool:
    """
    Determine if console logging should be enabled.
    
    Console logging is enabled in two cases:
    1. User explicitly requests it via MONITOR_LOG_CONSOLE=1
    2. Debug mode is active (level is DEBUG or more verbose)
    
    Args:
        level: Current log level (DEBUG=10, INFO=20, WARNING=30, etc.)
        
    Returns:
        True if console output should be enabled
    """
    explicitly_requested = _env("LOG_CONSOLE", "") == "1"
    debug_mode_active = level <= logging.DEBUG
    
    return explicitly_requested or debug_mode_active


def _formatter() -> logging.Formatter:
    """
    Create a consistent log formatter for all handlers.
    
    Format: "2025-01-23 14:30:15  INFO     monitor.gui.app  Application started"
    
    Returns:
        Configured logging.Formatter instance
    """
    # Simple timestamp format that works on all platforms
    return logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _file_handler(
    path: Path,
    level: int,
    when: str = "midnight",
    backups: int = 14,
) -> logging.handlers.TimedRotatingFileHandler:
    """
    Create a rotating file handler with UTF-8 encoding.
    
    Args:
        path: File path for the log file
        level: Minimum log level for this handler (e.g., logging.INFO)
        when: When to rotate - "midnight" rotates daily at 00:00
        backups: Number of backup files to keep (14 = 2 weeks of daily logs)
        
    Returns:
        Configured TimedRotatingFileHandler
    """
    h = logging.handlers.TimedRotatingFileHandler(
        str(path),
        when=when,
        backupCount=backups,
        encoding="utf-8",  # Ensure proper Unicode handling
        delay=True,        # Create file only when first log record is written
    )
    h.setLevel(level)
    h.setFormatter(_formatter())
    return h


def _console_handler(level: int) -> logging.Handler:
    """
    Create a console handler for terminal output.
    
    Args:
        level: Minimum log level for console output
        
    Returns:
        StreamHandler configured to write to stdout
    """
    h = logging.StreamHandler(sys.stdout)
    h.setLevel(level)
    h.setFormatter(_formatter())
    return h


def _make_listener(queue: Queue, *handlers: logging.Handler) -> logging.handlers.QueueListener:
    """
    Create and start a QueueListener for asynchronous logging.
    
    The QueueListener runs in a background thread and processes log records
    from a queue, allowing the main application to continue without blocking
    on I/O operations like writing to files.
    
    Args:
        queue: Queue to receive log records from QueueHandler
        *handlers: File and console handlers to process the log records
        
    Returns:
        Started QueueListener instance
    """
    listener = logging.handlers.QueueListener(queue, *handlers, respect_handler_level=True)
    listener.start()
    return listener


def _setup_excepthook() -> None:
    """
    Configure sys.excepthook to log uncaught exceptions.
    
    This ensures that any unhandled exceptions in the application
    are logged to the error log file for debugging purposes.
    KeyboardInterrupt (Ctrl+C) is ignored to allow clean shutdown.
    """
    def _log_uncaught(exc_type, exc_val, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts - they're intentional
            sys.__excepthook__(exc_type, exc_val, exc_tb)
            return
        logging.getLogger("monitor.uncaught").error(
            "Uncaught exception", exc_info=(exc_type, exc_val, exc_tb)
        )
        # Still print the traceback to stderr to aid debugging
        sys.__excepthook__(exc_type, exc_val, exc_tb)

    sys.excepthook = _log_uncaught


def _silence_third_party() -> None:
    """
    Reduce log verbosity of noisy third-party libraries.
    
    Some libraries generate excessive debug/info messages that clutter logs.
    This sets them to INFO level to reduce noise while preserving warnings/errors.
    """
    for name in (
        "urllib3",  # HTTP library - covers connectionpool, retry, etc.
        "PIL",      # Python Imaging Library
    ):
        logging.getLogger(name).setLevel(logging.INFO)


def _shutdown() -> None:
    """
    Clean shutdown of logging system.
    
    Stops the async queue listener (if running) and flushes all handlers.
    This is called automatically via atexit and manually in reset_logging().
    """
    global _QUEUE_LISTENER
    if _QUEUE_LISTENER:
        _QUEUE_LISTENER.stop()
        _QUEUE_LISTENER = None
    logging.shutdown()  # Closes and flushes every handler


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────
def init_logging(
    mode: Literal["sync", "async"] = "sync",
    *,
    level: int | None = None,
    log_dir: str | Path | None = None,
) -> None:
    """
    Configure the global logging system.
    
    This function sets up rotating log files, optional console output,
    and exception handling. It's thread-safe and can only be called once
    per process (use reset_logging() to reinitialize).
    
    Args:
        mode: "sync" for direct logging, "async" for queue-based non-blocking
        level: Minimum log level (overridden by MONITOR_LOG_LEVEL env var)
        log_dir: Directory for log files (overridden by MONITOR_LOG_DIR env var)
        
    Environment Variables:
        MONITOR_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL
        MONITOR_LOG_DIR: Path to log directory (default: "logs")
        MONITOR_LOG_CONSOLE: Set to "1" to enable console output
    """
    global _INITIALISED, _QUEUE_LISTENER

    with _LOCK:
        if _INITIALISED:
            return

        # Resolve configuration - environment variables take precedence
        effective_level = _log_level_from_env() if "MONITOR_LOG_LEVEL" in os.environ else (level or logging.INFO)
        log_directory = _log_dir_from_env() if log_dir is None else Path(log_dir).expanduser()
        log_directory.mkdir(parents=True, exist_ok=True)

        # Create handlers for different log levels and outputs
        app_handler = _file_handler(log_directory / "app.log", logging.INFO)      # All INFO+ messages
        error_handler = _file_handler(log_directory / "errors.log", logging.ERROR)  # Only ERROR+ messages
        handlers: list[logging.Handler] = [app_handler, error_handler]

        # Add console output if requested or running in debug mode
        if _enable_console_logging(effective_level):
            handlers.append(_console_handler(effective_level))

        # Configure root logger
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)  # Accept all levels - let handlers filter
        root.handlers[:] = []         # Remove any existing handlers

        if mode == "async":
            # Use queue-based logging for non-blocking I/O
            q: Queue = Queue(-1)  # Unlimited queue size
            root.addHandler(logging.handlers.QueueHandler(q))
            _QUEUE_LISTENER = _make_listener(q, *handlers)
        else:
            # Direct logging (synchronous)
            for h in handlers:
                root.addHandler(h)

        # Additional setup
        logging.captureWarnings(True)  # Route warnings module to logging
        _setup_excepthook()            # Log uncaught exceptions
        _silence_third_party()         # Reduce noise from libraries
        atexit.register(_shutdown)     # Clean shutdown on exit

        _INITIALISED = True


def reset_logging() -> None:
    """
    Reset the logging system to allow re-initialization.
    
    This function is primarily for testing purposes. It tears down
    all logging configuration and allows init_logging() to be called again.
    
    WARNING: This should not be called in production code.
    """
    global _INITIALISED
    with _LOCK:
        if not _INITIALISED:
            return
        _shutdown()
        # Remove any lingering handlers
        logging.getLogger().handlers[:] = []
        logging.captureWarnings(False)  # Disable warnings capture
        sys.excepthook = sys.__excepthook__  # Restore original exception hook
        _INITIALISED = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    If logging hasn't been initialized yet, this will automatically
    call init_logging() with default settings.
    
    Args:
        name: Logger name, typically the module name (e.g., "monitor.gui.app")
        
    Returns:
        Logger instance configured with the global logging settings
        
    Example:
        logger = get_logger("monitor.services.config")
        logger.info("Service initialized")
    """
    if not _INITIALISED:
        init_logging()
    return logging.getLogger(name)
