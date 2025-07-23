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
    """Return environment variable with MONITOR_ prefix."""
    return os.getenv(f"MONITOR_{name}", default)


def _log_level_from_env() -> int:
    level_str = _env("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def _log_dir_from_env() -> Path:
    return Path(_env("LOG_DIR", "logs")).expanduser()


def _want_console(level: int) -> bool:
    """Console if env flag set OR running at DEBUG level."""
    return _env("LOG_CONSOLE", "") == "1" or level <= logging.DEBUG


def _formatter() -> logging.Formatter:
    # ISO‑like timestamp with timezone offset
    return logging.Formatter(
        "%(asctime)s%(z)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _file_handler(
    path: Path,
    level: int,
    when: str = "midnight",
    backups: int = 14,
) -> logging.handlers.TimedRotatingFileHandler:
    h = logging.handlers.TimedRotatingFileHandler(
        str(path),
        when=when,
        backupCount=backups,
        encoding="utf-8",
        delay=True,                # create file on first record
    )
    h.setLevel(level)
    h.setFormatter(_formatter())
    return h


def _console_handler(level: int) -> logging.Handler:
    h = logging.StreamHandler(sys.stdout)
    h.setLevel(level)
    h.setFormatter(_formatter())
    return h


def _make_listener(queue: Queue, *handlers: logging.Handler) -> logging.handlers.QueueListener:
    listener = logging.handlers.QueueListener(queue, *handlers, respect_handler_level=True)
    # Make the internal worker thread a daemon so it won't block shutdown
    listener._thread.daemon = True  # type: ignore[attr-defined]
    return listener


def _setup_excepthook() -> None:
    def _log_uncaught(exc_type, exc_val, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_val, exc_tb)
            return
        logging.getLogger("monitor.uncaught").error(
            "Uncaught exception", exc_info=(exc_type, exc_val, exc_tb)
        )
        # Still print the traceback to stderr to aid debugging
        sys.__excepthook__(exc_type, exc_val, exc_tb)

    sys.excepthook = _log_uncaught


def _silence_third_party() -> None:
    for name in (
        "urllib3",  # parent covers connectionpool, retry, etc.
        "PIL",
    ):
        logging.getLogger(name).setLevel(logging.INFO)


def _shutdown() -> None:
    """Flush queues, close files. Runs via atexit and reset_logging()."""
    global _QUEUE_LISTENER
    if _QUEUE_LISTENER:
        _QUEUE_LISTENER.stop()
        _QUEUE_LISTENER = None
    logging.shutdown()             # closes & flushes every handler


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

    Call exactly once per process; thread‑safe.
    """
    global _INITIALISED, _QUEUE_LISTENER

    with _LOCK:
        if _INITIALISED:
            return

        # Resolve config (env overrides trump arguments)
        effective_level = _log_level_from_env() if "MONITOR_LOG_LEVEL" in os.environ else (level or logging.INFO)
        log_directory = _log_dir_from_env() if log_dir is None else Path(log_dir).expanduser()
        log_directory.mkdir(parents=True, exist_ok=True)

        # Create handlers
        app_handler    = _file_handler(log_directory / "app.log",    logging.INFO)
        error_handler  = _file_handler(log_directory / "errors.log", logging.ERROR)
        handlers: list[logging.Handler] = [app_handler, error_handler]

        if _want_console(effective_level):
            handlers.append(_console_handler(effective_level))

        # Prepare root logger
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)       # Never filter; let handlers decide
        root.handlers[:] = []              # purge default handlers

        if mode == "async":
            q: Queue = Queue()
            root.addHandler(logging.handlers.QueueHandler(q))
            _QUEUE_LISTENER = _make_listener(q, *handlers)
            _QUEUE_LISTENER.start()
        else:                              # sync
            for h in handlers:
                root.addHandler(h)

        # Extras
        logging.captureWarnings(True)
        _setup_excepthook()
        _silence_third_party()
        atexit.register(_shutdown)

        _INITIALISED = True


def reset_logging() -> None:
    """For unit tests: tear down and allow init_logging() again."""
    global _INITIALISED
    with _LOCK:
        if not _INITIALISED:
            return
        _shutdown()
        # Remove any lingering handlers
        logging.getLogger().handlers[:] = []
        logging.captureWarnings(False)
        sys.excepthook = sys.__excepthook__
        _INITIALISED = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger; auto‑initialise with defaults if needed."""
    if not _INITIALISED:
        init_logging()
    return logging.getLogger(name)
