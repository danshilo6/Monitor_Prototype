
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
        self._is_first_run = not self._config_path.exists()  # Track first run
        self.logger.info(f"Initializing config service: {config_path}")
        self._load()
        self._set_defaults_on_first_run()  # Set defaults after loading

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
            "general": {
                "location_name": "",
                "eintzofia_path": ""
            },
            "versions": {
                "monitor_version": "12-07-25",
                "ein_tzofia_version": "12-07-25"
            },
            "system": {
                "enable_restart": False,
                "minutes_to_restart": "5",
                "restart_cooldown_minutes": "2",
                "startup_snooze_time": "5",
                "check_eintzofia_running": False,
                "enable_eintzofia_auto_reopen": False,
                "decision_cycle_seconds": "180",
                "enable_device_failure_emails": False,
                "enable_restart_emails": False
            },
            "devices": {
                "relay_fail_threshold": "30",
                "camera_fail_threshold": "0.5",
                "camera_log_minutes": "20",
                "history_length": "50"
            },
            "device": {
                "signed_id": ""
            }
        }

    def _set_defaults_on_first_run(self):
        """Set default values only if this is the first time running the app."""
        if not self._is_first_run:
            return
        
        if self._acquire_lock():
            try:
                self.logger.info("First run detected - setting default configuration values")
                defaults = self._default_config()
                
                # Only set values that don't exist or are empty
                for section_name, section_data in defaults.items():
                    if section_name not in self._config:
                        self._config[section_name] = {}
                    
                    for key, default_value in section_data.items():
                        # Skip location_name and signed_id - user should set these
                        if key in ["location_name", "signed_id"]:
                            continue
                        
                        current_value = self._config[section_name].get(key, "")
                        if not current_value:  # Empty string, None, or missing
                            self._config[section_name][key] = default_value
                            self.logger.debug(f"Set default: {section_name}.{key} = {default_value}")
                
                self.save()  # Save the updated config
                self.logger.info("Default configuration values applied")
                
            finally:
                self._release_lock()

    def is_first_run(self) -> bool:
        """Check if this is the first time the application is running."""
        return self._is_first_run

    def set_eintzofia_path_if_first_run(self, detect_path_func):
        """Set EinTzofia path on first run using the provided detection function."""
        if not self._is_first_run:
            return
            
        current_path = self.get("general", "eintzofia_path", "")
        if not current_path:
            self.logger.info("First run: attempting to auto-detect EinTzofia path")
            detected_path = detect_path_func()
            if detected_path:
                self.set("general", "eintzofia_path", detected_path)
                self.logger.info(f"Auto-detected and set EinTzofia path: {detected_path}")
            else:
                self.logger.warning("Could not auto-detect EinTzofia path on first run")

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
