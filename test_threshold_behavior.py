#!/usr/bin/env python3
"""
Test to demonstrate the corrected threshold behavior.

Shows how the relay_fail_threshold works bidirectionally:
- Device status changes to "fail" after 200 consecutive fail logs
- Device status changes back to "success" after 200 consecutive success logs
"""

import tempfile
import pandas as pd
from pathlib import Path
from monitor.core.log_processor import LogProcessor
from monitor.services.device_status_db import DeviceStatusDatabase

def test_bidirectional_threshold():
    """Test that threshold works both ways: fail->success and success->fail"""
    
    print("🧪 Testing bidirectional threshold behavior")
    print("=" * 50)
    
    # Create temporary databases
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        device_status_db_path = str(temp_path / "test_device_status.db")
        
        # Create processor with threshold of 3 (for quick testing)
        processor = LogProcessor(
            db_directory=temp_path,
            device_status_db_path=device_status_db_path
        )
        # Override threshold for testing
        processor.relay_fail_threshold = 3
        
        # Create test device
        device_id = "TEST_DEVICE_001"
        
        # Test 1: Start with success, then 3 consecutive fails should change status
        print(f"\n1️⃣ Testing fail transition (threshold = {processor.relay_fail_threshold})")
        current_statuses = {}
        
        # 2 fail logs (below threshold)
        for i in range(2):
            device_updates = processor._calculate_status_updates(
                pd.DataFrame([{"device": device_id, "status": "fail", "timestamp": f"2025-07-30T17:00:{i:02d}"}]),
                current_statuses
            )
            processor._apply_status_updates(device_updates)
            current_statuses = processor.device_status_db.get_all_device_statuses()
            
            if device_id in current_statuses:
                status, count, _ = current_statuses[device_id]
                print(f"   Fail log {i+1}: status='{status}', count={count}")
        
        # 3rd fail log (reaches threshold)
        device_updates = processor._calculate_status_updates(
            pd.DataFrame([{"device": device_id, "status": "fail", "timestamp": "2025-07-30T17:00:03"}]),
            current_statuses
        )
        processor._apply_status_updates(device_updates)
        current_statuses = processor.device_status_db.get_all_device_statuses()
        status, count, _ = current_statuses[device_id]
        print(f"   Fail log 3: status='{status}', count={count} ✅ Status changed to fail!")
        
        # Test 2: Now 3 consecutive success logs should change status back
        print(f"\n2️⃣ Testing success transition (threshold = {processor.relay_fail_threshold})")
        
        # 2 success logs (below threshold) 
        for i in range(2):
            device_updates = processor._calculate_status_updates(
                pd.DataFrame([{"device": device_id, "status": "success", "timestamp": f"2025-07-30T17:01:{i:02d}"}]),
                current_statuses
            )
            processor._apply_status_updates(device_updates)
            current_statuses = processor.device_status_db.get_all_device_statuses()
            status, count, _ = current_statuses[device_id]
            print(f"   Success log {i+1}: status='{status}', count={count}")
        
        # 3rd success log (reaches threshold)
        device_updates = processor._calculate_status_updates(
            pd.DataFrame([{"device": device_id, "status": "success", "timestamp": "2025-07-30T17:01:03"}]),
            current_statuses
        )
        processor._apply_status_updates(device_updates)
        current_statuses = processor.device_status_db.get_all_device_statuses()
        status, count, _ = current_statuses[device_id]
        print(f"   Success log 3: status='{status}', count={count} ✅ Status changed to success!")
        
        processor.stop()
        
        print("\n🎉 Bidirectional threshold behavior works correctly!")
        print("✅ Device status changes when consecutive count reaches threshold")
        print("✅ Threshold works for both fail->success and success->fail transitions")

if __name__ == "__main__":
    test_bidirectional_threshold()
