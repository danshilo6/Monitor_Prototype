
import json
from pathlib import Path
from typing import Any, Dict
import threading
from monitor.log_setup import get_logger
from monitor.utils.path_utils import get_config_path


class ConfigService:
    """Thread-safe service for loading and saving application settings to a JSON config file."""

    def __init__(self, config_path: str = None):
        self.logger = get_logger("monitor.services.config_service")
        self.MONITOR_VERSION = "27_01_26"
        
        # Use absolute path relative to executable
        if config_path is None:
            config_path = get_config_path()
        elif not Path(config_path).is_absolute():
            # Convert relative path to absolute path relative to executable
            config_path = get_config_path()
        
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
                        loaded_config = json.load(f)
                    
                    # Merge with defaults to ensure all sections exist
                    self._config = self._merge_with_defaults(loaded_config)
                    self.logger.debug("Config loaded and merged with defaults")
                else:
                    self.logger.info("Config file not found, using default configuration")
                    self._config = self._default_config()
            except Exception as e:
                self.logger.error(f"Failed to load config file: {e}")
                self._config = self._default_config()
            finally:
                self._release_lock()

    def _merge_with_defaults(self, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with defaults to ensure all sections and keys exist."""
        defaults = self._default_config()
        merged_config = {}
        
        for section_name, default_section in defaults.items():
            if section_name not in loaded_config:
                # Section is completely missing, use defaults
                merged_config[section_name] = default_section.copy()
                self.logger.info(f"Missing section '{section_name}' - using defaults")
            else:
                # Section exists, merge individual keys
                merged_config[section_name] = {}
                loaded_section = loaded_config[section_name]
                
                for key, default_value in default_section.items():
                    if key not in loaded_section:
                        # Key is missing, use default
                        merged_config[section_name][key] = default_value
                        self.logger.debug(f"Missing key '{section_name}.{key}' - using default: {default_value}")
                    else:
                        # Key exists, use loaded value
                        merged_config[section_name][key] = loaded_section[key]
        
        # Preserve any extra sections/keys that aren't in defaults
        for section_name, section_data in loaded_config.items():
            if section_name not in merged_config:
                merged_config[section_name] = section_data
            else:
                for key, value in section_data.items():
                    if key not in defaults.get(section_name, {}):
                        merged_config[section_name][key] = value
        
        return merged_config

    def _get_monitor_version(self) -> str:
        return self.MONITOR_VERSION

    def _default_config(self) -> Dict[str, Any]:
        return {
            "general": {
                "location_name": "",
                "eintzofia_path": "",
                "server_url": "http://ec2-13-49-189-10.eu-north-1.compute.amazonaws.com:5001"
            },
            "versions": {
                "monitor_version": self._get_monitor_version(),
                "eintzofia_version": ""
            },
            "system": {
                "enable_restart": True,
                "minutes_to_restart": "5",
                "restart_cooldown_minutes": "10",
                "startup_snooze_time": "10",
                "check_eintzofia_running": True,
                "enable_eintzofia_auto_reopen": True,
                "decision_cycle_seconds": "300",
                "enable_device_failure_emails": True,
                "enable_restart_emails": True
            },
            "devices": {
                "relay_fail_threshold": "30",
                "camera_fail_threshold": "0.2",
                "camera_log_minutes": "20",
                "history_length": "50"
            },
            "device": {
                "signed_id": ""
            },
            "downloads": {
                "eintzofia_flag": False,
                "monitor_flag": False,
                "model_flag": False,
                "model_password": ""
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
