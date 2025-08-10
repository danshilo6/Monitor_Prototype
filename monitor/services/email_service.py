"""
Email Service

Handles email notifications for device failures and recoveries.
Sends emails via the server manager which interfaces with the legacy server.
"""

from datetime import datetime
from typing import List
from monitor.log_setup import get_logger
from monitor.services.contact_db import ContactDatabase
from monitor.services.devices_models import DeviceInfo


class EmailService:
    """
    Service for handling email notifications about device status changes.
    
    Sends emails via the server manager which interfaces with the legacy server.
    """
    
    def __init__(self, contact_db: ContactDatabase, server_manager=None):
        """
        Initialize the email service.
        
        Args:
            contact_db: ContactDatabase instance for retrieving email addresses
            server_manager: ServerManager instance for sending emails (optional for backwards compatibility)
        """
        self.logger = get_logger("monitor.services.email_service")
        self.contact_db = contact_db
        self.server_manager = server_manager
        
        if server_manager:
            self.logger.info("EmailService initialized with server manager")
        else:
            self.logger.info("EmailService initialized in mock mode (no server manager)")
    
    
    def send_device_failure_notification(self, device: DeviceInfo) -> None:
        """
        Send email notification about device failure to all contacts.
        
        Args:
            device: DeviceInfo instance that has failed
        """
        try:
            # Get all email addresses from contacts database
            email_addresses = self._get_all_email_addresses()
            
            if not email_addresses:
                self.logger.warning("No email addresses found in contacts database")
                return
            
            # Format the failure message using device's timestamp
            device_name = device.device_id
            failure_time = device.last_updated.strftime("%Y-%m-%d %H:%M:%S")
            
            subject = f"Device Failure Alert: {device_name}"
            message = f"Device {device_name} is not working since {failure_time}"
            
            # Send email via server manager or mock
            if self.server_manager:
                success = self.server_manager.send_email(subject, message, email_addresses)
                
                if success:
                    self.logger.info(f"Device failure notification sent for {device_name} to {len(email_addresses)} recipients")
                else:
                    self.logger.error(f"Failed to send device failure notification for {device_name}")
            else:
                # Fall back to mock for backwards compatibility
                self._mock_send_email(email_addresses, subject, message)
                self.logger.info(f"Device failure notification (mock) sent for {device_name} to {len(email_addresses)} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send device failure notification for {device.device_id}: {e}")
    
    def send_device_recovery_notification(self, device: DeviceInfo) -> None:
        """
        Send email notification about device recovery to all contacts.
        
        Args:
            device: DeviceInfo instance that has recovered
        """
        try:
            # Get all email addresses from contacts database
            email_addresses = self._get_all_email_addresses()
            
            if not email_addresses:
                self.logger.warning("No email addresses found in contacts database")
                return
            
            # Format the recovery message using device's timestamp
            device_name = device.device_id
            recovery_time = device.last_updated.strftime("%Y-%m-%d %H:%M:%S")
            
            subject = f"Device Recovery: {device_name}"
            message = f"Device {device_name} has recovered and is working normally as of {recovery_time}"
            
            # Send email via server manager or mock
            if self.server_manager:
                success = self.server_manager.send_email(subject, message, email_addresses)
                
                if success:
                    self.logger.info(f"Device recovery notification sent for {device_name} to {len(email_addresses)} recipients")
                else:
                    self.logger.error(f"Failed to send device recovery notification for {device_name}")
            else:
                # Fall back to mock for backwards compatibility
                self._mock_send_email(email_addresses, subject, message)
                self.logger.info(f"Device recovery notification (mock) sent for {device_name} to {len(email_addresses)} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send device recovery notification for {device.device_id}: {e}")
    
    def _get_all_email_addresses(self) -> List[str]:
        """
        Retrieve all email addresses from the contacts database.
        
        Returns:
            List of email addresses
        """
        try:
            # Get emails returns list of tuples (id, email)
            email_tuples = self.contact_db.get_emails()
            email_addresses = []
            
            for email_id, email in email_tuples:
                if email and email.strip():
                    email_addresses.append(email.strip())
            
            self.logger.debug(f"Retrieved {len(email_addresses)} email addresses from contacts database")
            return email_addresses
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve email addresses from contacts database: {e}")
            return []
    
    def _mock_send_email(self, recipients: List[str], subject: str, message: str) -> None:
        """
        Mock email sending - logs the email details without actually sending.
        
        Args:
            recipients: List of email addresses
            subject: Email subject line
            message: Email message body
        """
        recipients_str = ", ".join(recipients)
        
        # Log the mock email send
        self.logger.info(f"MOCK EMAIL SEND:")
        self.logger.info(f"  To: {recipients_str}")
        self.logger.info(f"  Subject: {subject}")
        self.logger.info(f"  Message: {message}")
        
        # Also print to console for visibility during testing
        print(f"📧 MOCK EMAIL SEND:")
        print(f"   To: {recipients_str}")
        print(f"   Subject: {subject}")
        print(f"   Message: {message}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
