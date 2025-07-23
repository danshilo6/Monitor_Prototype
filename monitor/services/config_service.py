
import json
from pathlib import Path
from typing import Any, Dict
import threading
from monitor.log_setup import get_logger

class ConfigService:
    """Thread-safe service for loading and saving application settings to a JSON config file."""

    def __init__(self, config_path: str = "config.json"):
        self.logger = get_logger("monitor.services.config_service")
        self._config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Re-entrant lock for thread safety
        self.logger.info(f"Initializing config service: {config_path}")
        self._load()
        self.logger.debug("Config service initialized successfully")

    def _acquire_lock(self, timeout=5):
        acquired = self._lock.acquire(timeout=timeout)
        if not acquired:
            self.logger.error("Could not acquire config lock within timeout")
            raise TimeoutError("Could not acquire config lock within timeout.")
        return True

    def _release_lock(self):
        self._lock.release()

    def _load(self):
        if self._acquire_lock():
            try:
                if self._config_path.exists():
                    self.logger.debug(f"Loading config from: {self._config_path}")
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        self._config = json.load(f)
                    self.logger.debug("Config file loaded successfully")
                else:
                    self.logger.info("Config file not found, using default configuration")
                    self._config = self._default_config()
            except Exception as e:
                self.logger.error(f"Failed to load config file: {e}")
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
                self.logger.debug(f"Saving config to: {self._config_path}")
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=2)
                self.logger.debug("Config file saved successfully")
            except Exception as e:
                self.logger.error(f"Failed to save config file: {e}")
            finally:
                self._release_lock()

    def get(self, section: str, key: str, default: Any = None) -> Any:
        if self._acquire_lock():
            try:
                value = self._config.get(section, {}).get(key, default)
                self.logger.debug(f"Retrieved config value: {section}.{key} = {value}")
                return value
            finally:
                self._release_lock()

    def set(self, section: str, key: str, value: Any):
        if self._acquire_lock():
            try:
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = value
                self.logger.info(f"Updated config: {section}.{key} = {value}")
                self.save()
            finally:
                self._release_lock()

    def all(self) -> Dict[str, Any]:
        if self._acquire_lock():
            try:
                return self._config.copy()
            finally:
                self._release_lock()
