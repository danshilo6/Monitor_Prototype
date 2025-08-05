#!/usr/bin/env python3
"""
Debug script to check devices database and DecisionEngine functionality.
"""

from pathlib import Path
from monitor.services.devices_db import DevicesDatabase
from monitor.core.decision_engine import DecisionEngine
import sqlite3

def main():
    print("=== Checking Devices Database ===")
    
    # Check if devices.db exists in data folder
    data_dir = Path("data")
    devices_db_path = data_dir / "devices.db"
    
    print(f"Looking for devices.db at: {devices_db_path}")
    print(f"File exists: {devices_db_path.exists()}")
    
    if devices_db_path.exists():
        print(f"File size: {devices_db_path.stat().st_size} bytes")
        
        # Try to connect and check contents
        try:
            conn = sqlite3.connect(str(devices_db_path))
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"Tables in database: {[t[0] for t in tables]}")
            
            # Check device count
            cursor.execute("SELECT COUNT(*) FROM devices;")
            count = cursor.fetchone()[0]
            print(f"Number of devices: {count}")
            
            if count > 0:
                # Show some devices
                cursor.execute("SELECT device_id, status, last_updated FROM devices LIMIT 5;")
                devices = cursor.fetchall()
                print("Sample devices:")
                for device in devices:
                    print(f"  {device[0]}: {device[1]} (last: {device[2]})")
            
            conn.close()
            
        except Exception as e:
            print(f"Error reading database: {e}")
    
    print("\n=== Testing DecisionEngine ===")
    try:
        # Test DecisionEngine creation
        decision_engine = DecisionEngine(data_directory=data_dir)
        print("DecisionEngine created successfully")
        print(f"DecisionEngine data_directory: {decision_engine.data_directory}")
        print(f"DevicesDatabase path: {decision_engine.devices_db.db_path}")
        
        # Try to get device statuses
        statuses = decision_engine._device_statuses
        print(f"Loaded device statuses: {len(statuses)} devices")
        
        if statuses:
            print("Sample statuses:")
            for device_id, status in list(statuses.items())[:3]:
                print(f"  {device_id}: {status}")
        
    except Exception as e:
        print(f"Error creating DecisionEngine: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
