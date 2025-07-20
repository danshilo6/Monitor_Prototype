
import json
from pathlib import Path
from typing import Any, Dict
import threading

class ConfigService:
    """Thread-safe service for loading and saving application settings to a JSON config file."""

    _lock = threading.RLock()  # Re-entrant lock for thread safety

    def __init__(self, config_path: str = "config.json"):
        self._config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load()

    def _acquire_lock(self, timeout=5):
        acquired = self._lock.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError("Could not acquire config lock within timeout.")
        return True

    def _release_lock(self):
        self._lock.release()

    def _load(self):
        if self._acquire_lock():
            try:
                if self._config_path.exists():
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        self._config = json.load(f)
                else:
                    self._config = self._default_config()
            finally:
                self._release_lock()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "general": {"location_name": "", "monitor_program_path": ""},
            "system": {"enable_restart": False, "minutes_to_restart": "", "startup_snooze_time": ""},
            "devices": {"relay_fail_threshold": "", "camera_fail_threshold": "", "camera_log_minutes": ""}
        }

    def save(self):
        if self._acquire_lock():
            try:
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=2)
            finally:
                self._release_lock()

    def get(self, section: str, key: str, default: Any = None) -> Any:
        if self._acquire_lock():
            try:
                return self._config.get(section, {}).get(key, default)
            finally:
                self._release_lock()

    def set(self, section: str, key: str, value: Any):
        if self._acquire_lock():
            try:
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = value
                self.save()
            finally:
                self._release_lock()

    def all(self) -> Dict[str, Any]:
        if self._acquire_lock():
            try:
                return self._config.copy()
            finally:
                self._release_lock()
