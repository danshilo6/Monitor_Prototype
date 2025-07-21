"""Shared test fixtures and configuration"""

import pytest
import sys
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for the entire test session"""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    yield app
    
    # Don't quit the app during testing as it may cause issues


def pytest_configure():
    """Configure pytest"""
    # Suppress Qt warnings during testing if desired
    pass


def pytest_unconfigure():
    """Clean up after pytest"""
    pass
