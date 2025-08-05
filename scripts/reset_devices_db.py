#!/usr/bin/env python3
"""
Reset Devices Database Script

Simple script to reset the devices database for manual testing.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.services.devices_db import DevicesDatabase

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset devices database for clean testing')
    parser.add_argument('--db-dir', type=str, default='data',
                       help='Directory containing devices.db (default: data)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt and reset immediately')
    
    args = parser.parse_args()
    
    # Create database path
    db_path = Path(args.db_dir) / "devices.db"
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Nothing to reset.")
        return
    
    # Create devices database instance
    devices_db = DevicesDatabase(str(db_path))
    
    try:
        # Show current state
        current_devices = devices_db.get_all()
        print(f"Current database contains {len(current_devices)} devices")
        
        if len(current_devices) == 0:
            print("Database is already empty.")
            return
        
        # Confirmation (unless --confirm flag is used)
        if not args.confirm:
            response = input(f"Are you sure you want to reset the database and remove all {len(current_devices)} devices? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Reset cancelled.")
                return
        
        # Reset the database
        if devices_db.reset_database():
            print("✅ Database reset successfully!")
            print("All devices have been removed.")
        else:
            print("❌ Failed to reset database. Check logs for details.")
            
    finally:
        devices_db.close()

if __name__ == "__main__":
    main()
