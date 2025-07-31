import sqlite3
import time
import random
import csv
import os
import argparse
import sys
from datetime import datetime
from typing import List, Dict
from pathlib import Path

class LogSimulator:
    """Simulates Ein Tzofia's device logging behavior"""
    
    def __init__(self, db_directory: str = ".", custom_db_name: str = None):
        # Generate the database file name based on the current date or use custom name
        if custom_db_name:
            self.db_path = Path(db_directory) / custom_db_name
        else:
            current_date = datetime.now().strftime("%Y_%m_%d")
            self.db_path = Path(db_directory) / f"logs_{current_date}.db"
        
        # Load device status dictionary from devices CSV  
        self.devices = self.load_devices_from_csv()
        
        # Load actual log entries from logs CSV
        self.log_entries = self.load_log_entries_from_csv()
        self.current_position = 0  # Track current position in log entries
        
        self.setup_database()
    
    def load_devices_from_csv(self) -> Dict[str, str]:
        """
        Load devices from devices_list_for_sim.csv in the main project folder.
        
        Returns:
            Dictionary with device names as keys and 'success' as values
        """
        # Get the path to the CSV file in the main project folder
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        csv_file = project_root / "devices_list_for_sim.csv"
        
        devices_dict = {}
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as file:
                csv_reader = csv.reader(file)
                for row in csv_reader:
                    if row and row[0].strip():  # Skip empty rows
                        device_name = row[0].strip()
                        devices_dict[device_name] = "success"
            
            print(f"Loaded {len(devices_dict)} devices from {csv_file}")
            
        except FileNotFoundError:
            print(f"Warning: Could not find {csv_file}")
            print("Using default generated devices instead")
            
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
            print("Using default generated devices instead")
            
        return devices_dict
    
    def load_log_entries_from_csv(self) -> List[Dict]:
        """
        Load actual log entries from logs_2025-07-27.csv file.
        
        Returns:
            List of log entry dictionaries
        """
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        csv_file = project_root / "logs_2025-07-27.csv"
        
        log_entries = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                next(csv_reader, None)  # Skip the header row
                for row in csv_reader:
                    if row and len(row) >= 4:  # Ensure we have enough columns
                        log_entry = {
                            'timestamp': row[1].strip(),
                            'device': row[2].strip(), 
                            'original_status': row[3].strip(),  # Keep original for reference
                            'details': row[4].strip()
                        }
                        log_entries.append(log_entry)
            
            print(f"Loaded {len(log_entries)} log entries from {csv_file}")
            
        except FileNotFoundError:
            print(f"Warning: Could not find {csv_file}")
            return []
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
            return []
        
        return log_entries
    
    def set_random_devices_to_fail(self):
        """
        Randomly select 1-5 devices and set their status to 'fail'.
        Prints each device that was set to fail.
        """
        if not self.devices:
            print("No devices loaded. Cannot set devices to fail.")
            return
        
        # Choose random number of devices to fail (1-5)
        num_devices_to_fail = random.randint(7, min(10, len(self.devices)))
        
        # Randomly select devices to fail
        device_names = list(self.devices.keys())
        devices_to_fail = random.sample(device_names, num_devices_to_fail)
        
        print()
        print(f"Setting {num_devices_to_fail} device(s) to fail:")
        for device in devices_to_fail:
            self.devices[device] = "fail"
            print(f"{device}")
        print()  # Extra newline for spacing
    
    def _reset_database_and_position(self):
        """
        Delete the current database file and reset position to 0.
        This allows starting fresh with a clean database.
        """
        import os
        
        # Reset position to start from beginning of log entries
        self.current_position = 0
        
        # Delete existing database file if it exists
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
                print(f"Deleted existing database: {self.db_path}")
            except Exception as e:
                print(f"Warning: Could not delete database {self.db_path}: {e}")
        
        # Recreate the database with fresh tables
        self.setup_database()
        print("Created fresh database and reset position to 0")
    
    def setup_database(self):
        """Create the logs table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    device TEXT,
                    status TEXT,
                    details TEXT,
                    raw_log TEXT,
                    created_at TEXT
                )
            """)
    
    def create_log_entry(self, device: str, status: str, details: str) -> dict:
        """Create a single log entry"""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        
        raw_log = f"{timestamp},{device},{status},{details}"
        
        return {
            'timestamp': timestamp,
            'device': device,
            'status': status,
            'details': details,
            'raw_log': raw_log,
            'created_at': created_at
        }
    
    def insert_log(self, log_entry: dict):
        """Insert a log entry into the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO logs (timestamp, device, status, details, raw_log, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log_entry['timestamp'],
                log_entry['device'],
                log_entry['status'],
                log_entry['details'],
                log_entry['raw_log'],
                log_entry['created_at']
            ))
    
    def run_simulation_cycle(self, num_logs: int = 100):
        """
        Run one simulation cycle reading log entries sequentially and applying device statuses.
        
        Args:
            num_logs: Number of log entries to process from current position
        """
        if not self.log_entries:
            print("No log entries loaded. Cannot run simulation.")
            return
        
        # Read the next X log entries sequentially
        entries_to_process = []
        for i in range(num_logs):
            if self.current_position >= len(self.log_entries):
                # If we've reached the end, start over from the beginning
                self.current_position = 0
                print("Reached end of log entries, starting over from beginning")
            
            log_entry = self.log_entries[self.current_position]
            entries_to_process.append(log_entry)
            self.current_position += 1
        
        # Process each log entry with device status override
        for entry in entries_to_process:
            device_name = entry['device']
            
            # Use status from device dictionary if available, otherwise use original
            if device_name in self.devices:
                status = self.devices[device_name]
            else:
                status = entry['original_status']  # Fallback to original
                print(f"Warning: Device {device_name} not found in device list, using original status")
            
            # Create log entry with overridden status
            log_entry = self.create_log_entry(
                device=device_name,
                status=status,
                details=entry['details']
            )
            
            self.insert_log(log_entry)
            print(f"Logged: {device_name} - {status}")
        
        print(f"Next cycle will start from position {self.current_position}")
    
    def run_simulation(self, interval: int = 1, logs_per_cycle: int = 100, reset_db: bool = False, max_duration: int = None):
        """
        Run continuous simulation with specified interval (seconds)
        
        Args:
            interval: Time between simulation cycles in seconds
            logs_per_cycle: Number of log entries to process in each cycle
            reset_db: If True, delete existing database and start from position 0
            max_duration: If set, run for only this many seconds (useful for testing)
        """
        if reset_db:
            self._reset_database_and_position()

        print(f"Starting log simulation...")
        print(f"Total log entries loaded: {len(self.log_entries)}")
        print(f"Device status dictionary size: {len(self.devices)}")
        print(f"Logs per cycle: {logs_per_cycle}")
        print(f"Interval: {interval} seconds")
        print(f"Starting from position: {self.current_position}")
        if max_duration:
            print(f"Max duration: {max_duration} seconds")
        print("Press Ctrl+C to stop")
        
        try:
            self.set_random_devices_to_fail()
            start_time = time.time()
            while True:
                # Check if we've reached max duration
                if max_duration and (time.time() - start_time) >= max_duration:
                    print(f"\nSimulation completed after {max_duration} seconds")
                    break
                    
                self.run_simulation_cycle(logs_per_cycle)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nSimulation stopped by user")

def main():
    """Main function to run the log simulator"""
    parser = argparse.ArgumentParser(description='Run log simulator for Ein Tzofia monitoring system')
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run in test mode with shorter duration and more frequent cycles')
    parser.add_argument('--duration', type=int, default=None,
                       help='Run for specific duration in seconds (useful for testing)')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='Interval between simulation cycles in seconds')
    parser.add_argument('--logs-per-cycle', type=int, default=100,
                       help='Number of log entries to process per cycle')
    parser.add_argument('--db-dir', type=str, default=".",
                       help='Directory where database files should be created')
    parser.add_argument('--reset-db', action='store_true',
                       help='Start with a fresh database (delete existing)')
    
    args = parser.parse_args()
    
    # Create simulator with specified directory
    simulator = LogSimulator(db_directory=args.db_dir)
    print(f"Database will be created at: {simulator.db_path}")
    print(f"Loaded device statuses: {len(simulator.devices)}")
    print(f"Loaded log entries: {len(simulator.log_entries)}")

    # Show first few log entries as example
    if simulator.log_entries:
        print("Sample log entries:")
        for i, entry in enumerate(simulator.log_entries[:3]):
            print(f"  {entry['device']} - {entry['original_status']} -> will be {simulator.devices.get(entry['device'], 'UNKNOWN')}")
        if len(simulator.log_entries) > 3:
            print(f"  ... and {len(simulator.log_entries) - 3} more log entries")
    
    # Set test mode defaults
    if args.test_mode:
        interval = args.interval if args.interval != 2.0 else 0.5  # Faster for testing
        logs_per_cycle = args.logs_per_cycle if args.logs_per_cycle != 100 else 5  # Fewer logs for testing
        duration = args.duration if args.duration else 10  # Default 10 seconds for tests
        reset_db = True  # Always reset for clean tests
        
        print("\n[TEST MODE ENABLED]")
        print(f"   Duration: {duration} seconds")
        print(f"   Interval: {interval} seconds") 
        print(f"   Logs per cycle: {logs_per_cycle}")
        print(f"   Reset DB: {reset_db}")
    else:
        # Production mode settings
        interval = args.interval
        logs_per_cycle = args.logs_per_cycle  
        duration = args.duration
        reset_db = args.reset_db
    
    # Run simulation
    simulator.run_simulation(
        interval=interval,
        logs_per_cycle=logs_per_cycle,
        reset_db=reset_db,
        max_duration=duration
    )

if __name__ == "__main__":
    main()