#!/usr/bin/env python3
"""
Run Log Processor Script

Simple script to run the log processor that reads logs and updates device status.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.core.log_processor import LogProcessor

def main():
    # Create log processor for current directory (where the .db files are)
    processor = LogProcessor(Path('.'), check_interval=2.0)
    
    print("Starting log processor...")
    print("Reading logs and updating device statuses every 2 seconds")
    print("Press Ctrl+C to stop")
    
    processor.start()

if __name__ == "__main__":
    main()
