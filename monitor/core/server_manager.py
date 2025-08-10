import sys
from pathlib import Path
from monitor.log_setup import get_logger

# Import legacy ServerManager
sys.path.append(str(Path(__file__).parent.parent.parent / "legacy_code"))
from server_class import ServerManager as LegacyServerManager


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
        
        # Version and restart settings
        self.VERSION = self._get_version()
        self.enable_pc_restart = self._get_restart_setting()
    
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
    
    def _get_version(self):
        """Get application version."""
        if self.config_service:
            return self.config_service.get("general", "version", "1.0.0")
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
                # Update config with current settings
                self.config_service.set("device", "location", self.settings['Location'])
                self.config_service.set("general", "eintzofia_path", self.settings['File_Path'])
                self.config_service.set("notifications", "phone_number", self.settings['Phone_Number'])
                self.config_service.save()
                self.logger.info("Settings saved successfully")
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
        
        self.logger.info("ServerManager initialized")
    
    # Core server communication methods
    def pulse_to_server(self, password='', return_id=False):
        """Send pulse to server using legacy implementation."""
        print("ServerManager: Sending pulse to server...")
        self.logger.info("Sending pulse to server")
        try:
            result = self.legacy_server.pulse_to_server(password, return_id)
            print(f"ServerManager: Pulse completed with result: {result}")
            self.logger.info(f"Pulse to server completed: {result}")
            return result
        except Exception as e:
            print(f"ServerManager: Pulse failed with error: {e}")
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
            print(f"📧 SERVER EMAIL SEND: {subject} to {len(emails)} recipients")
            
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
