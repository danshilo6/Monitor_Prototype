import asyncio
import io
import os
import re
import requests
import tempfile
import time
import zipfile
from pathlib import Path
from monitor.log_setup import get_logger

# Import legacy ServerManager via package so PyInstaller discovers it
from monitor.legacy_code.server_class import ServerManager as LegacyServerManager


class MockParentForServer:
    """
    Mock parent object that provides everything ServerManager needs.
    """
    
    def __init__(self, config_service, os_manager):
        self.config_service = config_service
        self.osManager = os_manager
        self.logger = get_logger("monitor.core.server_manager")
        
        # Legacy settings dictionary that server_class expects
        self.settings = {
            'Location': self._get_location(),
            'File_Path': self._get_eintzofia_path(),
            'Phone_Number': self._get_phone_number()
        }
        
        # Provide both versions separately for server pulse
        self.MONITOR_VERSION = self._get_monitor_version()
        self.EINTZOFIA_VERSION = self._get_eintzofia_version()
        
        # Legacy VERSION field (keeping for backwards compatibility)
        self.VERSION = self.MONITOR_VERSION
        
        # Legacy restart setting
        self.restart_enabled = self._get_restart_setting()
    

    def _get_location(self):
        """Get device location from config."""
        if self.config_service:
            return self.config_service.get("general", "location_name", "unknown")
        return "unknown"
    
    def _get_eintzofia_path(self):
        """Get EinTzofia executable path from config."""
        if self.config_service:
            return self.config_service.get("general", "eintzofia_path", "")
        return ""
    
    def _get_phone_number(self):
        """Get phone number from config."""
        if self.config_service:
            return self.config_service.get("notifications", "phone_number", "")
        return ""
    
    def _get_monitor_version(self):
        """Get monitor version from config service method."""
        if self.config_service:
            return self.config_service._get_monitor_version()
        return "1.0.0"
    
    def _get_eintzofia_version(self):
        """Get eintzofia version from config."""
        if self.config_service:
            return self.config_service.get("versions", "eintzofia_version", "1.0.0")
        return "1.0.0"
    
    def _get_restart_setting(self):
        """Get restart permission from config."""
        if self.config_service:
            return self.config_service.get("general", "enable_pc_restart", True)
        return True
    
    def write_state_to_file(self):
        """Persist current settings to file."""
        try:
            if self.config_service:
                pass
                # Update config with current settings
                # self.config_service.set("device", "location", self.settings['Location'])
                # self.config_service.set("general", "eintzofia_path", self.settings['File_Path'])
                # self.config_service.set("notifications", "phone_number", self.settings['Phone_Number'])
                # self.config_service.save()
                # self.logger.info("Settings saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")


class ServerManager:
    """
    Modern server manager that wraps legacy ServerManager functionality.
    Provides a clean interface for server communication.
    """
    
    def __init__(self, config_service=None, os_manager=None):
        """
        Initialize the server manager.
        
        Args:
            config_service: Configuration service instance
            os_manager: OS manager instance
        """
        self.config_service = config_service
        self.os_manager = os_manager
        self.logger = get_logger("monitor.core.server_manager")
        
        # Create mock parent and initialize legacy ServerManager
        self.mock_parent = MockParentForServer(config_service, os_manager)
        self.legacy_server = LegacyServerManager(self.mock_parent)

        """ debugging tests
        print("\n--------------------- TEST: GET EINTZOFIA MANIFEST FROM SERVER ---------------------")
        server_eintzofia_manifest = self.legacy_server.get_eintzofia_manifest()
        print(server_eintzofia_manifest)
        print("------------------------------------------------------------------------------------\n")
        print("\n--------------------- TEST: CREATE LOCAL MANIFEST ---------------------")
        local_eintzofia_manifest = self.legacy_server.create_local_eintzofia_manifest()
        print(local_eintzofia_manifest)
        print("-----------------------------------------------------------------------\n")
        print("\n--------------------- TEST: COMPARE LOCAL MANIFEST ---------------------")
        print(self.legacy_server.compare_eintzofia_manifests(server_eintzofia_manifest, local_eintzofia_manifest))
        print("-----------------------------------------------------------------------\n")
        """

        self.logger.info("ServerManager initialized")
    
    def update_server_url(self, url):
        """
        Update the server URL directly.
        
        Args:
            url: Full server URL (e.g., 'http://ec2-16-171-143-39.eu-north-1.compute.amazonaws.com:5000')
        """
        self.legacy_server.base_url = url
        print(f"Connecting to server: {url}")
        self.logger.info(f"Server URL updated to: {url}")

    def update_location_name(self, name):
        self.legacy_server.parent.settings['Location'] = name

    def update_ein_tzofia_path(self, path):
        self.legacy_server.parent.settings['File_Path'] = path

    # Core server communication methods
    def pulse_to_server(self, password='', return_id=False, devices=None, restart_history=None):
        """
        Send pulse to server with optional device data and restart history.
        
        Args:
            password: Server password
            return_id: Whether to return device ID
            devices: List of all device dictionaries (optional)
            restart_history: List of restart history dictionaries (optional)
        """
        #print("ServerManager: Sending pulse to server...")
        self.logger.info("Sending pulse to server ")
        print(f"SERVER_MANAGER: Sending pulse to server {self.config_service.get('general', 'server_url','')}")
        try:
            result = self.legacy_server.pulse_to_server(password, return_id, devices, restart_history)
            print(f"SERVER_MANAGER: Pulse completed with result: {result}")
            self.logger.info(f"Pulse to server completed: {result}")
            return result
        except Exception as e:
            print(f"SERVER_MANAGER: Pulse failed with error: {e}")
            self.logger.error(f"Failed to send pulse to server: {e}")
            return "Fail", "Fail", False
    
    def send_email(self, subject, message, emails):
        """
        Send email via legacy server manager.
        
        Args:
            subject: Email subject line
            message: Email message body  
            emails: List of email addresses
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not emails:
                self.logger.warning("No email addresses provided")
                return False
                
            self.logger.info(f"Sending email to {len(emails)} recipients: {subject}")
            print(f"\nSERVER EMAIL SEND: {subject} to {len(emails)} recipients")
            
            result = self.legacy_server.send_email(subject, message, emails)
            
            if result:
                self.logger.info("Email sent successfully via server")
            else:
                self.logger.warning("Email sending failed via server")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending email via server: {e}")
            return False
    
    def send_sms(self, message):
        """Send SMS using legacy implementation."""
        try:
            return self.legacy_server.send_SMS(message)
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {e}")
    
    # Device management methods
    def check_id_exists_and_approved(self):
        """Check if device ID exists and is approved."""
        try:
            return self.legacy_server.check_id_exists_and_approved()
        except Exception as e:
            self.logger.error(f"Failed to check device ID: {e}")
            return False, False
    
    def remove_id_from_server(self, device_id, password):
        """Remove device ID from server."""
        try:
            return self.legacy_server.remove_id_from_server(device_id, password)
        except Exception as e:
            self.logger.error(f"Failed to remove device ID: {e}")
    
    def enable_alerts(self, device_id, password):
        """Enable alerts for device."""
        try:
            return self.legacy_server.enable_alerts(device_id, password)
        except Exception as e:
            self.logger.error(f"Failed to enable alerts: {e}")
    
    def disable_alerts(self, device_id, password):
        """Disable alerts for device."""
        try:
            return self.legacy_server.disable_alerts(device_id, password)
        except Exception as e:
            self.logger.error(f"Failed to disable alerts: {e}")

    def check_for_updates(self, download_files: dict) -> bool:
        """Check if there are updates pending by the server."""
        if not download_files:
            return False
        
        updates_pending = False
        if isinstance(download_files, dict):
            for key in download_files.keys():
                if download_files[key] == True or download_files[key] == "True":
                    updates_pending = True
                    print(f"Update pending for: {key}")
                    self.logger.info(f"Update pending for: {key}")
        return updates_pending  

    def handle_download_files(self, download_files: dict) -> None:
        """ check if need to download monitor, eintzofia or model """
        if not download_files:
                self.logger.info("No download files specified")
                return False
        
        update = False

        # Download eintzofia files
        if download_files.get('eintzofia', False):
            try:
                print("Downloading EinTzofia files...")
                success = asyncio.run(self.download_exefiles(delete_old_file=True))
                if success:
                    print("EinTzofia files downloaded successfully")
                    self.logger.info("EinTzofia files downloaded successfully")
                    update = True
                else:
                    self.logger.warning("EinTzofia files download failed")
            except Exception as e:
                self.logger.error(f"Error downloading EinTzofia files: {e}")

        # Download monitor files
        if download_files.get('monitor', False):
            try:
                print("Downloading monitor files...")
                success = asyncio.run(self.download_monitor_files())
                if success:
                    print("Monitor files downloaded successfully")
                    self.logger.info("Monitor files downloaded successfully")
                    update = True
                else:
                    self.logger.warning("Monitor files download failed")
            except Exception as e:
                self.logger.error(f"Error downloading monitor files: {e}")
        
        # Download model files
        if download_files.get('model', False):
            try:
                # get device id and password from somewhere
                device_id = self.os_manager.generate_device_id()
                model_password = download_files.get('model_password', '')
                if not model_password:
                    self.logger.warning("No model password provided for model download")
                    print("No model password provided for model download")
                    return False

                print("Downloading encrypted model...")
                success = asyncio.run(self.download_encrypted_model(device_id, model_password))
                if success:
                    self.logger.info("Encrypted model downloaded successfully")
                    print("Encrypted model downloaded successfully")
                    update = True
                else:
                    self.logger.warning("Encrypted model download failed")
            except Exception as e:
                self.logger.error(f"Error downloading encrypted model: {e}")

        return update

    # Download methods
    async def download_monitor_files(self):
        """Download monitor files using legacy implementation."""
        try:
            return await self.legacy_server.download_monitor_files()
        except Exception as e:
            self.logger.error(f"Failed to download monitor files: {e}")
            return False
    
    async def download_exefiles(self, delete_old_file=False):
        """Download executable files using legacy implementation."""
        try:
            return await self.legacy_server.download_exefiles(delete_old_file)
        except Exception as e:
            self.logger.error(f"Failed to download exe files: {e}")
    
    def download_logs_from_server(self, device_id):
        """Download logs for specific device."""
        try:
            return self.legacy_server.download_logs_from_server(device_id)
        except Exception as e:
            self.logger.error(f"Failed to download logs: {e}")
            return None
    
    def download_camera_images(self, save_path=None):
        """Download camera images from server."""
        try:
            return self.legacy_server.download_camera_images(save_path)
        except Exception as e:
            self.logger.error(f"Failed to download camera images: {e}")
            return None
    
    def download_encrypted_model(self, device_id, password):
        """Download encrypted model from server."""
        try:
            return self.legacy_server.download_encrypted_model(device_id, password)
        except Exception as e:
            self.logger.error(f"Failed to download encrypted model: {e}")
            return None
    
    # Configuration methods
    def get_configuration_options(self):
        """Get available configuration options from server."""
        try:
            return self.legacy_server.get_configuration_options()
        except Exception as e:
            self.logger.error(f"Failed to get configuration options: {e}")
            return None
    
    def download_configurations(self, folder_name):
        """Download specific configuration folder."""
        try:
            return self.legacy_server.download_configurations(folder_name)
        except Exception as e:
            self.logger.error(f"Failed to download configurations: {e}")
    
    def upload_configuration(self):
        """Upload current configuration to server."""
        try:
            return self.legacy_server.upload_configuration()
        except Exception as e:
            self.logger.error(f"Failed to upload configuration: {e}")
    
    def set_download_files(self, locations, eintzofia_download=False, monitor_download=False):
        """Set download flags for specified locations."""
        try:
            return self.legacy_server.set_download_files(locations, eintzofia_download, monitor_download)
        except Exception as e:
            self.logger.error(f"Failed to set download files: {e}")
    
    # Server state methods
    def get_server_state(self, password):
        """Get current server state."""
        try:
            return self.legacy_server.get_server_state(password)
        except Exception as e:
            self.logger.error(f"Failed to get server state: {e}")
            return None
    
    def get_signed_id(self, device_id):
        """Get signed device ID from server."""
        try:
            return self.legacy_server.get_signed_ID(device_id)
        except Exception as e:
            self.logger.error(f"Failed to get signed ID: {e}")
            return {'status': 'error', 'message': 'Failed to get signed ID'}
    
    # Utility methods
    def upload_zip_file(self, zip_path):
        """Upload zip file to server."""
        try:
            return self.legacy_server.upload_zip_file(zip_path)
        except Exception as e:
            self.logger.error(f"Failed to upload zip file: {e}")
            return None

    def upload_eintzofia_config(self) -> bool:
        """
        Zips all camera IP folders and configfile.json from the EinTzofia temp directory
        and uploads them to POST /upload_site_config on the server.
        Returns True on success, False on failure.
        """
        _IP_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        MAX_RETRIES = 2
        RETRY_DELAY = 5

        temp_dir = Path(self.os_manager.get_temp_dir_path())
        if not temp_dir.exists():
            self.logger.warning("EinTzofia temp directory does not exist, skipping upload")
            return False

        device_id = self.os_manager.generate_device_id()
        location = self.config_service.get("general", "location_name", "unknown")
        server_url = self.config_service.get("general", "server_url", "")
        endpoint = f"{server_url}/upload_site_config"

        # Check cooldown before sending large files
        try:
            cooldown_url = f"{server_url}/check_config_upload_cooldown"
            cooldown_response = requests.get(cooldown_url, params={"device_id": device_id}, timeout=10)
            if cooldown_response.status_code == 200:
                cooldown_data = cooldown_response.json()
                if cooldown_data.get("on_cooldown", False):
                    retry_after = cooldown_data.get("retry_after_hours")
                    print(f"DEBUG: Config upload skipped — on cooldown (retry after {retry_after}h)")
                    self.logger.info(f"Config upload skipped — on cooldown (retry after {retry_after}h)")
                    return False
            else:
                self.logger.warning(f"Cooldown check returned {cooldown_response.status_code}, proceeding with upload")
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Cooldown check failed: {e}, proceeding with upload")

        _IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png"]

        # Each entry: (zip_filename, list_of_(arcname, filepath))
        items_to_zip: list[tuple[str, list[tuple[str, Path]]]] = []

        for entry in temp_dir.iterdir():
            if not (entry.is_dir() and _IP_PATTERN.match(entry.name)):
                continue
            ip = entry.name
            specific_files: list[tuple[str, Path]] = []
            # Main image: {ip}.jpeg / {ip}.jpg / {ip}.png
            for ext in _IMAGE_EXTENSIONS:
                candidate = entry / f"{ip}{ext}"
                if candidate.is_file():
                    specific_files.append((f"{ip}/{candidate.name}", candidate))
                    break
            # Regions image: {ip}_regions.jpeg / {ip}_regions.jpg / {ip}_regions.png
            for ext in _IMAGE_EXTENSIONS:
                candidate = entry / f"{ip}_regions{ext}"
                if candidate.is_file():
                    specific_files.append((f"{ip}/{candidate.name}", candidate))
                    break
            if specific_files:
                items_to_zip.append((f"{ip}.zip", specific_files))

        configfile = temp_dir / "configfile.json"
        if configfile.exists():
            items_to_zip.append(("configfile.zip", [("configfile.json", configfile)]))

        if not items_to_zip:
            self.logger.warning("No camera image files or configfile found to upload")
            return False

        temp_zip_paths: list[str] = []
        # Read zip bytes into memory so they can be replayed on a 503 retry
        file_payloads: list[tuple[str, bytes]] = []

        try:
            for zip_name, file_entries in items_to_zip:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                    zip_path = tmp.name
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for arcname, source_path in file_entries:
                        zf.write(source_path, arcname)

                temp_zip_paths.append(zip_path)
                with open(zip_path, "rb") as f:
                    file_payloads.append((zip_name, f.read()))

            for attempt in range(MAX_RETRIES):
                files = [
                    ("file", (name, io.BytesIO(data), "application/zip"))
                    for name, data in file_payloads
                ]
                post_data = {"device_id": device_id, "location": location}

                try:
                    response = requests.post(endpoint, files=files, data=post_data, timeout=60)
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Upload request failed: {e}")
                    return False

                if response.status_code == 200:
                    self.logger.info(f"EinTzofia config uploaded successfully: {response.json()}")
                    return True
                elif response.status_code == 503 and attempt < MAX_RETRIES - 1:
                    self.logger.warning(f"Server busy (503), retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                elif response.status_code == 403:
                    self.logger.error("Upload rejected: device not approved (403)")
                    return False
                else:
                    self.logger.error(f"Upload failed with status {response.status_code}: {response.text}")
                    return False

            return False

        finally:
            for path in temp_zip_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def get_eintzofia_manifest(self):
        """Get EinTzofia manifest from legacy server manager."""
        try:
            return self.legacy_server.get_eintzofia_manifest()
        except Exception as e:
            self.logger.error(f"Failed to get EinTzofia manifest: {e}")
            return None
    
    def process_manifest_updates(self):
        """Process manifest updates using legacy implementation."""
        try:
            return self.legacy_server.process_manifest_updates()
        except Exception as e:
            self.logger.error(f"Failed to process manifest updates: {e}")
            return False    
    def download_monitor_downloader(self) -> str:
        """
        Download monitor downloader from server.
        
        Returns:
            str: Path to downloaded downloader executable, or None if failed
        """
        try:
            self.logger.info("Downloading monitor downloader from server")
            
            # Get download path (save to monitor directory)
            monitor_dir = self.os_manager.get_monitor_dir_path()
            downloader_filename = "monitor_downloader.exe" if self.os_manager.current_os == "Windows" else "monitor_downloader"
            downloader_path = os.path.join(monitor_dir, downloader_filename)
            
            # Download from server using the legacy implementation
            success = self.legacy_server.download_monitor_downloader(downloader_path)
            
            if success and os.path.exists(downloader_path):
                self.logger.info(f"Monitor downloader downloaded successfully: {downloader_path}")
                return downloader_path
            else:
                self.logger.error("Monitor downloader download failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading monitor downloader: {e}")
            return None    

