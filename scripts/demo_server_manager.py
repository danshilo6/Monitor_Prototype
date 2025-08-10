#!/usr/bin/env python3
"""
Example usage of the ServerManager wrapper class.

This script demonstrates how to integrate the legacy server functionality
into the modern project structure.
"""

from monitor.core.os_manager import OSManager
from monitor.core.server_manager import ServerManager
import asyncio


class MockConfigService:
    """
    Simple mock config service for demonstration.
    In your actual implementation, use your real ConfigService.
    """
    def __init__(self):
        self.config = {
            "device": {
                "location": "Office_A"
            },
            "general": {
                "eintzofia_path": r"C:\EinTzofia\EinTzofia.exe",
                "version": "2.1.0",
                "enable_pc_restart": True
            },
            "notifications": {
                "phone_number": "+1234567890"
            }
        }
    
    def get(self, section, key, default=None):
        """Get configuration value."""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        """Set configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def save(self):
        """Save configuration (mock implementation)."""
        print("Config saved successfully")


async def main():
    """Main demonstration function."""
    print("ServerManager Wrapper Demo")
    print("=" * 50)
    
    # Initialize dependencies
    config_service = MockConfigService()
    os_manager = OSManager(config_service)
    server_manager = ServerManager(config_service, os_manager)
    
    print("✓ Initialized ServerManager with dependencies")
    
    # Example 1: Check device ID status
    print("\n1. Checking device ID status...")
    try:
        exists, approved = server_manager.check_id_exists_and_approved()
        print(f"   Device exists: {exists}, Approved: {approved}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 2: Send pulse to server
    print("\n2. Sending pulse to server...")
    try:
        correct_password, download_files, transformed_id = server_manager.pulse_to_server("test_password")
        print(f"   Password correct: {correct_password}")
        print(f"   Download files: {download_files}")
        print(f"   Transformed ID: {transformed_id}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 3: Get configuration options
    print("\n3. Getting configuration options...")
    try:
        options = server_manager.get_configuration_options()
        print(f"   Available configurations: {options}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 4: Send email notification
    print("\n4. Sending email notification...")
    try:
        server_manager.send_email(
            subject="Test Alert",
            message="This is a test message from the monitor system.",
            emails=["admin@example.com"]
        )
        print("   ✓ Email sent successfully")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 5: Send SMS notification
    print("\n5. Sending SMS notification...")
    try:
        server_manager.send_sms("Monitor system test message")
        print("   ✓ SMS sent successfully")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 6: Get server state (requires admin password)
    print("\n6. Getting server state...")
    try:
        state = server_manager.get_server_state("admin_password")
        if state is not None:
            print(f"   ✓ Retrieved server state with {len(state)} devices")
        else:
            print("   No state data received")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    # Run the async demo
    asyncio.run(main())
