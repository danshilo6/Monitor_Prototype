"""
Path utilities for MonitorApp

Provides functions to get correct file paths that work both in development
and in PyInstaller one-file builds.
"""

import sys
import os
from pathlib import Path


def get_app_root() -> Path:
    """
    Get the application root directory (where the executable is located).
    
    Returns:
        Path: The directory containing the executable in PyInstaller builds,
              or the project root in development mode.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return Path(sys.executable).parent
    else:
        # Development mode - return project root
        # This file is in monitor/utils/, so go up 2 levels to get project root
        return Path(__file__).parent.parent.parent


def get_data_path(filename: str) -> str:
    """
    Get full path for a data file.
    
    Args:
        filename: Name of the file in the data directory
        
    Returns:
        str: Full path to the data file
    """
    data_dir = get_app_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir / filename)


def get_config_path() -> str:
    """
    Get full path for config.json.
    
    Returns:
        str: Full path to config.json
    """
    return str(get_app_root() / "config.json")


def ensure_data_dir() -> Path:
    """
    Ensure data directory exists and return its path.
    
    Returns:
        Path: Path to the data directory
    """
    data_dir = get_app_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """
    Get the logs directory path.
    
    Returns:
        Path: Path to the logs directory
    """
    logs_dir = get_app_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def get_temp_test_logs_dir() -> Path:
    """
    Get the temp_test_logs directory path.
    
    Returns:
        Path: Path to the temp_test_logs directory
    """
    temp_logs_dir = get_app_root() / "temp_test_logs"
    temp_logs_dir.mkdir(exist_ok=True)
    return temp_logs_dir
