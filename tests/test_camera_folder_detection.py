"""
Tests for OSManager configuration change detection logic.

Tests the check_configuration_changed() method which monitors IP-named
camera subdirectories and configfile.json inside EinTzofia's temp directory for changes.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from monitor.core.os_manager import OSManager


@pytest.fixture
def mock_config_service():
    config = MagicMock()
    config.get.return_value = ""
    return config


@pytest.fixture
def os_manager(mock_config_service):
    """OSManager with legacy internals fully mocked out."""
    with patch("monitor.core.os_manager.LegacyOSManager"):
        manager = OSManager(mock_config_service)
    return manager


@pytest.fixture
def temp_dirs(tmp_path):
    """Return (eintzofia_temp_dir, monitor_dir) as real tmp directories."""
    eintzofia_temp = tmp_path / "eintzofia" / "_internal" / "temp"
    eintzofia_temp.mkdir(parents=True)
    monitor_dir = tmp_path / "monitor"
    monitor_dir.mkdir()
    return eintzofia_temp, monitor_dir


def _setup_dirs(os_manager, eintzofia_temp, monitor_dir):
    """Patch the path-returning methods on os_manager."""
    os_manager.get_temp_dir_path = lambda: str(eintzofia_temp)
    os_manager.get_monitor_dir_path = lambda: str(monitor_dir)


def _create_ip_folder(parent: Path, ip: str, mtime: float | None = None) -> Path:
    """Create a directory named after an IP address and optionally set its mtime."""
    folder = parent / ip
    folder.mkdir(exist_ok=True)
    if mtime is not None:
        import os
        os.utime(folder, (mtime, mtime))
    return folder


def _write_timestamps(monitor_dir: Path, timestamps: dict) -> None:
    """Write a camera_folder_timestamps.json into the monitor data directory."""
    data_dir = monitor_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    timestamps_file = data_dir / "eintzofia_timestamps.json"
    timestamps_file.write_text(json.dumps(timestamps))


def _read_timestamps(monitor_dir: Path) -> dict:
    """Read back the saved timestamps file."""
    timestamps_file = monitor_dir / "data" / "eintzofia_timestamps.json"
    return json.loads(timestamps_file.read_text())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckConfigurationChangedTempDirMissing:
    def test_returns_false_when_temp_dir_does_not_exist(self, os_manager, tmp_path):
        missing = tmp_path / "nonexistent"
        monitor_dir = tmp_path / "monitor"
        monitor_dir.mkdir()
        _setup_dirs(os_manager, missing, monitor_dir)

        result = os_manager.check_configuration_changed()

        assert result is False


class TestCheckConfigurationChangedFirstRun:
    def test_first_run_returns_false(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)
        _create_ip_folder(eintzofia_temp, "192.168.1.10")

        result = os_manager.check_configuration_changed()

        assert result is False

    def test_first_run_saves_timestamps_file(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)
        _create_ip_folder(eintzofia_temp, "192.168.1.10")

        os_manager.check_configuration_changed()

        saved = _read_timestamps(monitor_dir)
        assert "192.168.1.10" in saved

    def test_first_run_with_no_folders_returns_false(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        result = os_manager.check_configuration_changed()

        assert result is False


class TestCheckConfigurationChangedNoChange:
    def test_no_change_returns_false(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        folder = _create_ip_folder(eintzofia_temp, "10.0.0.1")
        mtime = folder.stat().st_mtime
        _write_timestamps(monitor_dir, {"10.0.0.1": mtime})

        result = os_manager.check_configuration_changed()

        assert result is False


class TestCheckConfigurationChangedWithChanges:
    def test_updated_mtime_returns_true(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        old_mtime = 1_000_000.0
        _create_ip_folder(eintzofia_temp, "10.0.0.2", mtime=old_mtime + 100)
        _write_timestamps(monitor_dir, {"10.0.0.2": old_mtime})

        result = os_manager.check_configuration_changed()

        assert result is True

    def test_updated_mtime_saves_new_timestamps(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        old_mtime = 1_000_000.0
        _create_ip_folder(eintzofia_temp, "10.0.0.2", mtime=old_mtime + 100)
        _write_timestamps(monitor_dir, {"10.0.0.2": old_mtime})

        os_manager.check_configuration_changed()

        saved = _read_timestamps(monitor_dir)
        assert saved["10.0.0.2"] > old_mtime

    def test_file_modified_inside_folder_returns_true(self, os_manager, temp_dirs):
        import os as _os
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        old_mtime = 1_000_000.0
        folder = _create_ip_folder(eintzofia_temp, "10.0.0.3", mtime=old_mtime)

        # Create a file inside the folder with a newer mtime
        image_file = folder / "snapshot.jpg"
        image_file.write_bytes(b"fake image data")
        _os.utime(image_file, (old_mtime + 500, old_mtime + 500))

        # Saved timestamp is old — folder dir itself wasn't touched
        _write_timestamps(monitor_dir, {"10.0.0.3": old_mtime})

        result = os_manager.check_configuration_changed()

        assert result is True

    def test_file_inside_folder_unchanged_returns_false(self, os_manager, temp_dirs):
        import os as _os
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        fixed_mtime = 1_000_000.0
        folder = _create_ip_folder(eintzofia_temp, "10.0.0.4")

        image_file = folder / "snapshot.jpg"
        image_file.write_bytes(b"fake image data")
        # Set both file and folder to the same fixed mtime (creating the file updated folder's mtime)
        _os.utime(image_file, (fixed_mtime, fixed_mtime))
        _os.utime(folder, (fixed_mtime, fixed_mtime))

        _write_timestamps(monitor_dir, {"10.0.0.4": fixed_mtime})

        result = os_manager.check_configuration_changed()

        assert result is False

    def test_new_folder_added_returns_true(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        _create_ip_folder(eintzofia_temp, "192.168.1.1")
        _create_ip_folder(eintzofia_temp, "192.168.1.2")  # newly added
        _write_timestamps(monitor_dir, {"192.168.1.1": 1_000_000.0})

        result = os_manager.check_configuration_changed()

        assert result is True

    def test_folder_removed_returns_true(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        # Only one folder on disk, but timestamps has two
        _create_ip_folder(eintzofia_temp, "192.168.1.1")
        _write_timestamps(monitor_dir, {
            "192.168.1.1": 1_000_000.0,
            "192.168.1.99": 1_000_000.0,  # this one was removed
        })

        result = os_manager.check_configuration_changed()

        assert result is True


class TestCheckConfigurationChangedNonIpFolders:
    def test_non_ip_folder_is_ignored(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        # Create a non-IP-named folder that should be ignored
        (eintzofia_temp / "images").mkdir()
        (eintzofia_temp / "logs").mkdir()

        # Valid IP folder with known timestamp (no change)
        folder = _create_ip_folder(eintzofia_temp, "10.0.0.1")
        mtime = folder.stat().st_mtime
        _write_timestamps(monitor_dir, {"10.0.0.1": mtime})

        result = os_manager.check_configuration_changed()

        assert result is False

    def test_only_non_ip_folders_first_run_saves_empty_timestamps(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        (eintzofia_temp / "some_folder").mkdir()

        os_manager.check_configuration_changed()

        saved = _read_timestamps(monitor_dir)
        assert saved == {}


class TestCheckConfigurationChangedCorruptedTimestamps:
    def test_corrupted_timestamps_file_is_treated_as_first_run(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        data_dir = monitor_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "camera_folder_timestamps.json").write_text("not valid json {{{{")

        _create_ip_folder(eintzofia_temp, "10.1.1.1")

        result = os_manager.check_configuration_changed()

        # Treated as empty saved state → first run → returns False
        assert result is False


class TestCheckConfigurationChangedConfigfile:
    def test_configfile_modified_returns_true(self, os_manager, temp_dirs):
        import os as _os
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        old_mtime = 1_000_000.0
        configfile = eintzofia_temp / "configfile.json"
        configfile.write_text('{"key": "value"}')
        _os.utime(configfile, (old_mtime + 100, old_mtime + 100))
        _write_timestamps(monitor_dir, {"_configfile": old_mtime})

        result = os_manager.check_configuration_changed()

        assert result is True

    def test_configfile_unchanged_returns_false(self, os_manager, temp_dirs):
        import os as _os
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        fixed_mtime = 1_000_000.0
        configfile = eintzofia_temp / "configfile.json"
        configfile.write_text('{"key": "value"}')
        _os.utime(configfile, (fixed_mtime, fixed_mtime))
        _write_timestamps(monitor_dir, {"_configfile": fixed_mtime})

        result = os_manager.check_configuration_changed()

        assert result is False

    def test_configfile_absent_not_tracked(self, os_manager, temp_dirs):
        eintzofia_temp, monitor_dir = temp_dirs
        _setup_dirs(os_manager, eintzofia_temp, monitor_dir)

        # No configfile.json on disk, saved state also has no entry
        folder = _create_ip_folder(eintzofia_temp, "10.0.0.1")
        mtime = folder.stat().st_mtime
        _write_timestamps(monitor_dir, {"10.0.0.1": mtime})

        result = os_manager.check_configuration_changed()

        assert result is False
