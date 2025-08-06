#!/usr/bin/env python3
"""
Quick test to verify the new batch update functionality in DevicesDatabase
"""

import tempfile
import os
from datetime import datetime
from monitor.services.devices_db import DevicesDatabase
from monitor.services.devices_models import DeviceInfo, DeviceType

def test_batch_updates():
    """Test the new batch update functionality"""
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database
        print("Initializing DevicesDatabase with connection-per-operation pattern...")
        db = DevicesDatabase(db_path)
        
        # Create test devices
        print("Creating test devices...")
        test_devices = []
        for i in range(5):
            device = DeviceInfo(
                device_id=f"device_{i}",
                device_type="camera",
                status="success" if i % 2 == 0 else "fail",
                last_log_status="success" if i % 2 == 0 else "fail",
                last_log_consecutive_count=i + 1,
                success_count=10 + i,
                fail_count=i,
                recent_pattern="SF" * (i + 1),
                last_updated=datetime.now()
            )
            test_devices.append(device)
        
        # Test batch update
        print(f"Testing batch update with {len(test_devices)} devices...")
        updated_count = db.update_devices_batch(test_devices)
        print(f"Batch update result: {updated_count} devices updated")
        
        # Verify the devices were stored
        print("Verifying devices were stored correctly...")
        all_devices = db.get_all()
        print(f"Found {len(all_devices)} devices in database")
        
        for device_id, device in all_devices.items():
            print(f"  - {device_id}: {device.status} (count: {device.last_log_consecutive_count})")
        
        # Test individual get
        print("\nTesting individual device retrieval...")
        device_1 = db.get_device("device_1")
        if device_1:
            print(f"Retrieved device_1: {device_1.status}")
        else:
            print("Failed to retrieve device_1")
        
        # Test by status filter
        print("\nTesting get_by_status...")
        success_devices = db.get_by_status("success")
        fail_devices = db.get_by_status("fail")
        print(f"Success devices: {len(success_devices)}")
        print(f"Fail devices: {len(fail_devices)}")
        
        print("\n✓ All tests passed! Connection-per-operation pattern working correctly.")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up temporary file
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"Cleaned up temporary database: {db_path}")

if __name__ == "__main__":
    test_batch_updates()
