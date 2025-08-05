#!/usr/bin/env python3
"""
Simple script to print the current devices database content
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.services.devices_db import DevicesDatabase

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Print devices database content')
    parser.add_argument('--db-dir', type=str, default='data',
                       help='Directory containing devices.db (default: data)')
    parser.add_argument('--title', type=str, default='Current Devices Status',
                       help='Title for the output')
    
    args = parser.parse_args()
    
    # Create database path
    db_path = Path(args.db_dir) / "devices.db"
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Make sure the log processor has been run to create the devices database.")
        return
    
    # Create devices database instance
    devices_db = DevicesDatabase(str(db_path))
    
    try:
        # Print the devices
        devices_db.print_devices(args.title)
    finally:
        devices_db.close()

if __name__ == "__main__":
    main()
