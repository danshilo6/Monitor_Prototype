#!/usr/bin/env python3
"""
Simple Log Reader Script

Runs the LogReader a few times with 2-second delays to show new log entries.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.core.log_reader import LogReader

def main():
    # Create log reader for current directory (where the .db files are)
    log_reader = LogReader(Path('.'))
    
    print("Reading logs 5 times with 2-second delays...")
    
    for i in range(20):
        print(f"\n--- Read #{i+1} ---")
        df = log_reader.read_next(500)
        
        if df.empty:
            print("No new logs found")
        else:
            print(f"Found {len(df)} new log entries:")
            for _, row in df.iterrows():
                print(f"ID: {row['id']} | {row['timestamp']} | {row['device']} | {row['status']}")
        
        if i < 4:  # Don't sleep after the last iteration
            time.sleep(0.1)
    
    log_reader.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
