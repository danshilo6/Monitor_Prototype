"""Tests for LogReader functionality"""

import unittest
import tempfile
import sqlite3
import os
import shutil
import subprocess
import sys
import time
import signal
from pathlib import Path
from datetime import date, datetime, timedelta
import pandas as pd
from monitor.core.log_reader import LogReader


class TestLogReader(unittest.TestCase):
    """Test cases for LogReader"""

    def setUp(self):
        """Set up test environment with temporary directory and test databases"""
        # Clean up any existing LogReader state before tests
        LogReader.reset_state()
        
        # Create temporary directory for test databases
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Test data for logs
        self.sample_logs = [
            (1, 'device1', 'ok', 'normal', '2025-07-30 10:00:00'),
            (2, 'device2', 'error', 'critical', '2025-07-30 10:01:00'),
            (3, 'device1', 'warning', 'minor', '2025-07-30 10:02:00'),
            (4, 'device3', 'ok', 'normal', '2025-07-30 10:03:00'),
        ]

    def tearDown(self):
        """Clean up test directory and LogReader state"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        # Clean up LogReader state after tests
        LogReader.reset_state()

    def _create_test_db(self, db_date: date, logs_data=None):
        """
        Create a test database with sample log data.
        
        Args:
            db_date: The date for the database filename
            logs_data: List of tuples with log data, defaults to self.sample_logs
        """
        if logs_data is None:
            logs_data = self.sample_logs
            
        db_filename = db_date.strftime("logs_%Y-%m-%d.db")
        db_path = self.test_path / db_filename
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create logs table
        cursor.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Insert test data
        cursor.executemany(
            "INSERT INTO logs (id, device, status, priority, timestamp) VALUES (?, ?, ?, ?, ?)",
            logs_data
        )
        
        conn.commit()
        conn.close()
        
        return db_path

    def test_initialization(self):
        """Test LogReader initialization"""
        # Create a test database for today
        today = date.today()
        self._create_test_db(today)
        
        # Initialize LogReader
        reader = LogReader(self.test_path)
        
        self.assertEqual(reader._dir, self.test_path)
        self.assertEqual(reader._table, "logs")
        self.assertEqual(reader._pattern, "logs_%Y-%m-%d.db")
        self.assertEqual(reader._last_id, 0)
        self.assertEqual(reader._current_day, today)
        
        reader.close()

    def test_initialization_no_db_file(self):
        """Test LogReader initialization when today's DB file doesn't exist"""
        # Don't create any database files
        reader = LogReader(self.test_path)
        
        # Should initialize but not connect to any database
        self.assertEqual(reader._dir, self.test_path)
        self.assertIsNone(reader._conn)
        self.assertIsNone(reader._current_day)
        self.assertEqual(reader._last_id, 0)
        
        reader.close()

    def test_read_next_basic(self):
        """Test basic read_next functionality"""
        # Create test database for today
        today = date.today()
        self._create_test_db(today)
        
        reader = LogReader(self.test_path)
        
        # First read should return all logs
        df = reader.read_next()
        
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 4)
        self.assertEqual(reader._last_id, 4)
        
        # Verify data content
        self.assertEqual(df.iloc[0]['device'], 'device1')
        self.assertEqual(df.iloc[0]['status'], 'ok')
        self.assertEqual(df.iloc[1]['device'], 'device2')
        self.assertEqual(df.iloc[1]['status'], 'error')
        
        reader.close()

    def test_read_next_with_limit(self):
        """Test read_next with limit parameter"""
        # Create test database for today
        today = date.today()
        self._create_test_db(today)
        
        reader = LogReader(self.test_path)
        
        # Read with limit of 2
        df = reader.read_next(limit=2)
        
        self.assertEqual(len(df), 2)
        self.assertEqual(reader._last_id, 2)
        self.assertEqual(df.iloc[0]['device'], 'device1')
        self.assertEqual(df.iloc[1]['device'], 'device2')
        
        # Read remaining logs
        df2 = reader.read_next(limit=2)
        
        self.assertEqual(len(df2), 2)
        self.assertEqual(reader._last_id, 4)
        self.assertEqual(df2.iloc[0]['device'], 'device1')
        self.assertEqual(df2.iloc[1]['device'], 'device3')
        
        reader.close()

    def test_read_next_incremental(self):
        """Test that read_next only returns new logs on subsequent calls"""
        # Create test database for today
        today = date.today()
        self._create_test_db(today)
        
        reader = LogReader(self.test_path)
        
        # First read - get all logs
        df1 = reader.read_next()
        self.assertEqual(len(df1), 4)
        self.assertEqual(reader._last_id, 4)
        
        # Second read - should be empty (no new logs)
        df2 = reader.read_next()
        self.assertTrue(df2.empty)
        self.assertEqual(reader._last_id, 4)
        
        # Add more data to the database
        db_filename = today.strftime("logs_%Y-%m-%d.db")
        db_path = self.test_path / db_filename
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (device, status, priority, timestamp) VALUES (?, ?, ?, ?)",
            ('device4', 'ok', 'normal', '2025-07-30 10:04:00')
        )
        conn.commit()
        conn.close()
        
        # Third read - should get the new log
        df3 = reader.read_next()
        self.assertEqual(len(df3), 1)
        self.assertEqual(df3.iloc[0]['device'], 'device4')
        self.assertEqual(reader._last_id, 5)
        
        reader.close()

    def test_read_next_empty_database(self):
        """Test read_next with empty database"""
        # Create empty database
        today = date.today()
        self._create_test_db(today, logs_data=[])
        
        reader = LogReader(self.test_path)
        
        # Should return empty DataFrame
        df = reader.read_next()
        self.assertTrue(df.empty)
        self.assertEqual(reader._last_id, 0)
        
        reader.close()

    def test_read_next_no_database(self):
        """Test read_next when no database file exists"""
        reader = LogReader(self.test_path)
        
        # Should handle gracefully when no database exists by returning empty DataFrame
        df = reader.read_next()
        self.assertTrue(df.empty, "Should return empty DataFrame when no database exists")
        self.assertIsInstance(df, pd.DataFrame, "Should return a DataFrame even when no database exists")
        
        reader.close()

    def test_day_switching(self):
        """Test automatic switching between database files for different days"""
        # Create databases for yesterday and today
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        yesterday_logs = [
            (1, 'device1', 'ok', 'normal', '2025-07-29 23:59:00'),
            (2, 'device2', 'error', 'critical', '2025-07-29 23:59:30'),
        ]
        
        today_logs = [
            (1, 'device1', 'warning', 'minor', '2025-07-30 00:00:00'),
            (2, 'device3', 'ok', 'normal', '2025-07-30 00:01:00'),
        ]
        
        self._create_test_db(yesterday, yesterday_logs)
        self._create_test_db(today, today_logs)
        
        reader = LogReader(self.test_path)
        
        # Should read from today's database
        df = reader.read_next()
        self.assertEqual(len(df), 2)
        self.assertEqual(reader._current_day, today)
        self.assertEqual(reader._last_id, 2)
        
        reader.close()

    def test_custom_table_name(self):
        """Test LogReader with custom table name"""
        # Create database with custom table name
        today = date.today()
        db_filename = today.strftime("logs_%Y-%m-%d.db")
        db_path = self.test_path / db_filename
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create table with custom name
        cursor.execute("""
            CREATE TABLE custom_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.executemany(
            "INSERT INTO custom_logs (id, device, status, priority, timestamp) VALUES (?, ?, ?, ?, ?)",
            self.sample_logs
        )
        
        conn.commit()
        conn.close()
        
        # Initialize LogReader with custom table name
        reader = LogReader(self.test_path, table="custom_logs")
        
        df = reader.read_next()
        self.assertEqual(len(df), 4)
        self.assertEqual(df.iloc[0]['device'], 'device1')
        
        reader.close()

    def test_custom_pattern(self):
        """Test LogReader with custom filename pattern"""
        # Create database with custom pattern
        today = date.today()
        custom_filename = today.strftime("system_logs_%Y%m%d.db")
        db_path = self.test_path / custom_filename
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.executemany(
            "INSERT INTO logs (id, device, status, priority, timestamp) VALUES (?, ?, ?, ?, ?)",
            self.sample_logs
        )
        
        conn.commit()
        conn.close()
        
        # Initialize LogReader with custom pattern
        reader = LogReader(self.test_path, pattern="system_logs_%Y%m%d.db")
        
        df = reader.read_next()
        self.assertEqual(len(df), 4)
        
        reader.close()

    def test_close(self):
        """Test proper cleanup when closing LogReader"""
        today = date.today()
        self._create_test_db(today)
        
        reader = LogReader(self.test_path)
        
        # Verify connection exists
        self.assertIsNotNone(reader._conn)
        
        # Close should cleanup connection
        reader.close()
        
        # Connection should be closed (attempting to use it should fail)
        with self.assertRaises(sqlite3.ProgrammingError):
            reader._conn.execute("SELECT 1")

    def test_dataframe_columns(self):
        """Test that returned DataFrame has expected columns"""
        today = date.today()
        self._create_test_db(today)
        
        reader = LogReader(self.test_path)
        df = reader.read_next()
        
        expected_columns = ['id', 'device', 'status', 'priority', 'timestamp']
        self.assertListEqual(list(df.columns), expected_columns)
        
        reader.close()

    def test_data_types(self):
        """Test that data types are preserved correctly"""
        today = date.today()
        self._create_test_db(today)
        
        reader = LogReader(self.test_path)
        df = reader.read_next()
        
        # Check that id is numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(df['id']))
        
        # Check that text fields are strings
        self.assertTrue(pd.api.types.is_object_dtype(df['device']))
        self.assertTrue(pd.api.types.is_object_dtype(df['status']))
        
        reader.close()

    def test_integration_with_log_simulator(self):
        """Integration test: Run log simulator as separate process and verify LogReader can read logs"""
        # Create a temporary directory for this test
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        try:
            # Get the path to the log simulator script
            project_root = Path(__file__).parent.parent
            simulator_script = project_root / "scripts" / "log_simulator.py"
            
            # Verify the simulator script exists
            self.assertTrue(simulator_script.exists(), f"Log simulator not found at {simulator_script}")
            
            # Run the log simulator in test mode as a separate process
            simulator_process = subprocess.Popen([
                sys.executable, str(simulator_script),
                '--test-mode',                    # Enable test mode
                '--duration', '8',               # Run for 8 seconds
                '--interval', '1',               # Log every 1 second (slower for reliability)
                '--logs-per-cycle', '5',         # More logs per cycle
                '--db-dir', str(temp_path),      # Use our temp directory
                '--logs-csv', str(project_root / 'logs_2025-07-07.csv'),  # Explicit CSV path
                '--reset-db'                     # Reset database
            ], cwd=str(project_root),            # Run from project root
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy())               # Copy current environment
            
            try:
                # Give the simulator more time to start and create some logs
                time.sleep(6)  # Wait longer for simulator to create logs
                
                # Check if simulator is still running and capture output
                if simulator_process.poll() is None:
                    # Still running - let it complete
                    print("Simulator process still running, waiting for completion...")
                    try:
                        stdout, stderr = simulator_process.communicate(timeout=5)
                        print(f"Simulator completed. Exit code: {simulator_process.returncode}")
                    except subprocess.TimeoutExpired:
                        print("Simulator taking too long, terminating...")
                        simulator_process.terminate()
                        stdout, stderr = simulator_process.communicate()
                else:
                    # Already finished
                    stdout, stderr = simulator_process.communicate()
                    print(f"Simulator finished early. Exit code: {simulator_process.returncode}")
                
                # Always show simulator output for debugging
                if stdout:
                    print(f"Simulator stdout:\n{stdout}")
                if stderr:
                    print(f"Simulator stderr:\n{stderr}")
                
                # Verify that the database file was created
                today = date.today()
                expected_db_file = temp_path / f"logs_{today.strftime('%Y-%m-%d')}.db"
                
                # Wait up to 10 seconds for the database file to be created
                timeout = 10
                start_time = time.time()
                while not expected_db_file.exists() and (time.time() - start_time) < timeout:
                    time.sleep(0.5)
                
                print(f"Expected database file: {expected_db_file}")
                print(f"Database file exists: {expected_db_file.exists()}")
                
                # List all files in temp directory for debugging
                print(f"Files in temp directory: {list(temp_path.iterdir())}")
                
                self.assertTrue(expected_db_file.exists(), 
                               f"Database file should be created by simulator at {expected_db_file}")
                
                # Check if database has any data
                if expected_db_file.exists():
                    import sqlite3
                    conn = sqlite3.connect(expected_db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM logs")
                    count = cursor.fetchone()[0]
                    print(f"Number of logs in database: {count}")
                    
                    if count > 0:
                        cursor.execute("SELECT * FROM logs LIMIT 3")
                        sample_logs = cursor.fetchall()
                        print(f"Sample logs: {sample_logs}")
                    conn.close()
                
                # Verify the simulator created logs
                self.assertGreater(count, 0, f"Log simulator should have created logs in database. Check simulator output above for errors.")
                
                # Initialize LogReader in the same directory
                reader = LogReader(temp_path)
                
                # Verify LogReader connected to the database
                self.assertIsNotNone(reader._conn, "LogReader should have a database connection")
                
                # Read logs - should find some entries created by the simulator
                logs_df = reader.read_next()
                
                print(f"Logs found: {len(logs_df) if not logs_df.empty else 0}")
                if not logs_df.empty:
                    print(f"First few logs:\n{logs_df.head()}")
                
                # Verify we got some logs
                self.assertFalse(logs_df.empty, "LogReader should have found logs created by simulator")
                self.assertGreater(len(logs_df), 0, "Should have at least one log entry")
                
                # Verify log structure is correct (real simulator structure)
                expected_columns = ['id', 'timestamp', 'device', 'status', 'details', 'raw_log', 'created_at']
                for col in expected_columns:
                    self.assertIn(col, logs_df.columns, f"Column '{col}' should be present in logs")
                
                # Verify data content looks reasonable
                first_log = logs_df.iloc[0]
                self.assertIsNotNone(first_log['device'], "Device should not be None")
                self.assertIsNotNone(first_log['status'], "Status should not be None")
                
                # Test incremental reading - let simulator create more logs
                time.sleep(2)
                
                # Read again - should get new logs
                new_logs_df = reader.read_next()
                
                if not new_logs_df.empty:
                    # Verify incremental IDs
                    last_old_id = logs_df['id'].max()
                    first_new_id = new_logs_df['id'].min()
                    self.assertGreater(first_new_id, last_old_id, 
                                     "New logs should have higher IDs than previous logs")
                
                reader.close()
                
                print(f"✅ Integration test completed: Found {len(logs_df)} initial logs")
                if not new_logs_df.empty:
                    print(f"✅ Incremental reading: Found {len(new_logs_df)} additional logs")
                
            finally:
                # Clean up: wait for simulator to finish or terminate it
                try:
                    stdout, stderr = simulator_process.communicate(timeout=3)
                    if stdout:
                        print("Simulator output:", stdout.strip())
                    if stderr:
                        print("Simulator errors:", stderr.strip())
                except subprocess.TimeoutExpired:
                    simulator_process.terminate()
                    try:
                        simulator_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        simulator_process.kill()
                        simulator_process.wait()
                
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_integration_with_real_log_simulator(self):
        """Integration test: Verify LogReader can handle realistic log data structure"""
        # Create a temporary directory for this test
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        try:
            # Create a database with the same structure as the real log simulator
            today = date.today()
            db_filename = today.strftime("logs_%Y-%m-%d.db")
            db_path = temp_path / db_filename
            
            # Create realistic test data similar to what the real simulator would create
            realistic_logs = [
                (1, '2025-07-30 10:00:00', 'sprinkler_1', 'success', 'Normal operation', 'sprinkler_1,success,Normal operation', '2025-07-30 10:00:00'),
                (2, '2025-07-30 10:00:30', 'camera_outdoor_1', 'fail', 'Connection timeout', 'camera_outdoor_1,fail,Connection timeout', '2025-07-30 10:00:30'),
                (3, '2025-07-30 10:01:00', 'fan_exhaust_2', 'success', 'Operating normally', 'fan_exhaust_2,success,Operating normally', '2025-07-30 10:01:00'),
                (4, '2025-07-30 10:01:30', 'sprinkler_3', 'error', 'Low pressure detected', 'sprinkler_3,error,Low pressure detected', '2025-07-30 10:01:30'),
                (5, '2025-07-30 10:02:00', 'camera_indoor_2', 'success', 'Recording active', 'camera_indoor_2,success,Recording active', '2025-07-30 10:02:00'),
            ]
            
            # Create database with real simulator structure
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    device TEXT,
                    status TEXT,
                    details TEXT,
                    raw_log TEXT,
                    created_at TEXT
                )
            """)
            
            cursor.executemany(
                "INSERT INTO logs (id, timestamp, device, status, details, raw_log, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                realistic_logs
            )
            
            conn.commit()
            conn.close()
            
            # Test LogReader with realistic data
            reader = LogReader(temp_path)
            self.assertIsNotNone(reader._conn, "LogReader should connect to database")
            
            # Read all logs
            logs_df = reader.read_next()
            
            # Verify we got the expected data
            self.assertFalse(logs_df.empty, "Should read logs from database")
            self.assertEqual(len(logs_df), 5, "Should read all 5 log entries")
            
            # Verify realistic device names
            devices = set(logs_df['device'].unique())
            expected_devices = {'sprinkler_1', 'camera_outdoor_1', 'fan_exhaust_2', 'sprinkler_3', 'camera_indoor_2'}
            self.assertEqual(devices, expected_devices, "Should have expected device names")
            
            # Verify realistic statuses
            statuses = set(logs_df['status'].unique())
            expected_statuses = {'success', 'fail', 'error'}
            self.assertEqual(statuses, expected_statuses, "Should have expected status values")
            
            # Verify incremental reading works
            self.assertEqual(reader._last_id, 5, "Should track last read ID")
            
            # Add more logs to test incremental reading
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO logs (timestamp, device, status, details, raw_log, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ('2025-07-30 10:03:00', 'pump_main', 'success', 'Pressure normal', 'pump_main,success,Pressure normal', '2025-07-30 10:03:00')
            )
            conn.commit()
            conn.close()
            
            # Read incremental logs
            new_logs_df = reader.read_next()
            self.assertEqual(len(new_logs_df), 1, "Should read one new log")
            self.assertEqual(new_logs_df.iloc[0]['device'], 'pump_main', "Should read the new device log")
            self.assertEqual(reader._last_id, 6, "Should update last read ID")
            
            reader.close()
            
            print("✅ Integration test with realistic log simulator data completed successfully")
            
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
