"""Path utilities for the Monitor Prototype application"""

from pathlib import Path

def get_icons_dir() -> Path:
    """Get the icons directory path"""
    return Path(__file__).parent.parent / "icons"

def get_icon_path(icon_name: str) -> str | None:
    """Get icon file path, returns None if file doesn't exist"""
    icon_path = get_icons_dir() / icon_name
    return str(icon_path) if icon_path.exists() else None