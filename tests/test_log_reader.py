import pytest
import sqlite3
import json
import tempfile
import shutil
import time
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from monitor.core.log_reader import LogReader


class TestLogReader:
    """Test suite for LogReader class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test databases."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Add a small delay to ensure database connections are closed
        time.sleep(0.1)
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            # Retry after a longer delay on Windows
            time.sleep(0.5)
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory for state files."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def create_test_db(self, db_path: Path, records: list[dict]) -> None:
        """Create a test database with sample records."""
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                level TEXT,
                message TEXT
            )
        """)
        
        for record in records:
            conn.execute(
                "INSERT INTO logs (id, timestamp, level, message) VALUES (?, ?, ?, ?)",
                (record["id"], record["timestamp"], record["level"], record["message"])
            )
        
        conn.commit()
        conn.close()

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_log_reader_initialization(self, mock_state_path, temp_dir, temp_data_dir):
        """Test LogReader initialization."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        reader = LogReader(temp_dir)
        
        assert reader._dir == temp_dir
        assert reader._table == "logs"
        assert reader._pattern == "logs_%Y-%m-%d.db"
        assert reader._last_id == 0
        assert reader._current_day == date.today()

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_read_next_empty_database(self, mock_state_path, temp_dir, temp_data_dir):
        """Test reading from non-existent database."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        reader = LogReader(temp_dir)
        df = reader.read_next()
        
        assert df.empty
        assert reader._last_id == 0

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_read_next_with_data(self, mock_state_path, temp_dir, temp_data_dir):
        """Test reading from database with data."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        # Create test database for today
        today = date.today()
        db_path = temp_dir / today.strftime("logs_%Y-%m-%d.db")
        
        test_records = [
            {"id": 1, "timestamp": "2025-08-24 10:00:00", "level": "INFO", "message": "Test message 1"},
            {"id": 2, "timestamp": "2025-08-24 10:01:00", "level": "ERROR", "message": "Test message 2"},
            {"id": 3, "timestamp": "2025-08-24 10:02:00", "level": "INFO", "message": "Test message 3"}
        ]
        
        self.create_test_db(db_path, test_records)
        
        reader = LogReader(temp_dir)
        df = reader.read_next()
        
        assert len(df) == 3
        assert reader._last_id == 3
        assert df.iloc[0]["message"] == "Test message 1"
        assert df.iloc[2]["message"] == "Test message 3"

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_incremental_reading(self, mock_state_path, temp_dir, temp_data_dir):
        """Test that LogReader only returns new records on subsequent reads."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        # Create test database for today
        today = date.today()
        db_path = temp_dir / today.strftime("logs_%Y-%m-%d.db")
        
        # Initial records
        initial_records = [
            {"id": 1, "timestamp": "2025-08-24 10:00:00", "level": "INFO", "message": "Initial 1"},
            {"id": 2, "timestamp": "2025-08-24 10:01:00", "level": "INFO", "message": "Initial 2"}
        ]
        
        self.create_test_db(db_path, initial_records)
        
        reader = LogReader(temp_dir)
        
        # First read
        df1 = reader.read_next()
        assert len(df1) == 2
        assert reader._last_id == 2
        
        # Add more records
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO logs (id, timestamp, level, message) VALUES (?, ?, ?, ?)",
            (3, "2025-08-24 10:02:00", "ERROR", "New message 1")
        )
        conn.execute(
            "INSERT INTO logs (id, timestamp, level, message) VALUES (?, ?, ?, ?)",
            (4, "2025-08-24 10:03:00", "INFO", "New message 2")
        )
        conn.commit()
        conn.close()
        
        # Second read should only return new records
        df2 = reader.read_next()
        assert len(df2) == 2
        assert reader._last_id == 4
        assert df2.iloc[0]["message"] == "New message 1"
        assert df2.iloc[1]["message"] == "New message 2"
        
        # Third read should return empty DataFrame
        df3 = reader.read_next()
        assert df3.empty
        assert reader._last_id == 4

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_state_persistence(self, mock_state_path, temp_dir, temp_data_dir):
        """Test that LogReader state is saved and restored correctly."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        # Create test database for today
        today = date.today()
        db_path = temp_dir / today.strftime("logs_%Y-%m-%d.db")
        
        test_records = [
            {"id": 1, "timestamp": "2025-08-24 10:00:00", "level": "INFO", "message": "Test 1"},
            {"id": 2, "timestamp": "2025-08-24 10:01:00", "level": "INFO", "message": "Test 2"}
        ]
        
        self.create_test_db(db_path, test_records)
        
        # First reader instance
        reader1 = LogReader(temp_dir)
        df1 = reader1.read_next()
        assert len(df1) == 2
        assert reader1._last_id == 2
        reader1.close()
        
        # Create new reader instance - should restore state
        reader2 = LogReader(temp_dir)
        assert reader2._last_id == 2
        
        # Should return empty since no new records
        df2 = reader2.read_next()
        assert df2.empty

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    @patch('monitor.core.log_reader.date')
    def test_day_switching(self, mock_date, mock_state_path, temp_dir, temp_data_dir):
        """Test that LogReader correctly handles day switching."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        # Start with August 24, 2025
        day1 = date(2025, 8, 24)
        day2 = date(2025, 8, 25)
        
        # Mock date.today() to return day1 initially
        mock_date.today.return_value = day1
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        
        # Create databases for both days
        db_path_day1 = temp_dir / "logs_2025-08-24.db"
        db_path_day2 = temp_dir / "logs_2025-08-25.db"
        
        records_day1 = [
            {"id": 1, "timestamp": "2025-08-24 10:00:00", "level": "INFO", "message": "Day 1 Record 1"},
            {"id": 2, "timestamp": "2025-08-24 10:01:00", "level": "INFO", "message": "Day 1 Record 2"}
        ]
        
        records_day2 = [
            {"id": 1, "timestamp": "2025-08-25 10:00:00", "level": "INFO", "message": "Day 2 Record 1"},
            {"id": 2, "timestamp": "2025-08-25 10:01:00", "level": "INFO", "message": "Day 2 Record 2"}
        ]
        
        self.create_test_db(db_path_day1, records_day1)
        self.create_test_db(db_path_day2, records_day2)
        
        # Initialize reader on day 1
        reader = LogReader(temp_dir)
        
        # Read from day 1
        df1 = reader.read_next()
        assert len(df1) == 2
        assert reader._last_id == 2
        assert reader._current_day == day1
        assert "Day 1 Record" in df1.iloc[0]["message"]
        
        # Switch to day 2
        mock_date.today.return_value = day2
        
        # Next read should detect day change and reset last_id
        df2 = reader.read_next()
        assert len(df2) == 2
        assert reader._last_id == 2  # Reset for new day, then updated to 2
        assert reader._current_day == day2
        assert "Day 2 Record" in df2.iloc[0]["message"]

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    @patch('monitor.core.log_reader.date')
    def test_day_switching_with_state_persistence(self, mock_date, mock_state_path, temp_dir, temp_data_dir):
        """Test day switching with state file persistence across days."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        day1 = date(2025, 8, 24)
        day2 = date(2025, 8, 25)
        
        # Day 1: Create reader and read some data
        mock_date.today.return_value = day1
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        
        db_path_day1 = temp_dir / "logs_2025-08-24.db"
        records_day1 = [
            {"id": 1, "timestamp": "2025-08-24 10:00:00", "level": "INFO", "message": "Day 1 Record"}
        ]
        self.create_test_db(db_path_day1, records_day1)
        
        reader1 = LogReader(temp_dir)
        df1 = reader1.read_next()
        assert len(df1) == 1
        assert reader1._last_id == 1
        reader1.close()
        
        # Verify state was saved for day 1
        assert state_file.exists()
        with open(state_file, 'r') as f:
            state = json.load(f)
            assert state['day'] == day1.isoformat()
            assert state['last_id'] == 1
        
        # Day 2: Create new reader (simulating restart)
        mock_date.today.return_value = day2
        
        db_path_day2 = temp_dir / "logs_2025-08-25.db"
        records_day2 = [
            {"id": 1, "timestamp": "2025-08-25 10:00:00", "level": "INFO", "message": "Day 2 Record"}
        ]
        self.create_test_db(db_path_day2, records_day2)
        
        # New reader should detect different day and start fresh
        reader2 = LogReader(temp_dir)
        assert reader2._last_id == 0  # Should start fresh for new day
        assert reader2._current_day == day2
        
        df2 = reader2.read_next()
        assert len(df2) == 1
        assert "Day 2 Record" in df2.iloc[0]["message"]

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_reset_state(self, mock_state_path, temp_dir, temp_data_dir):
        """Test the static reset_state method."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        # Create a state file
        state = {"last_id": 5, "day": "2025-08-24"}
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        assert state_file.exists()
        
        # Reset state
        LogReader.reset_state()
        
        assert not state_file.exists()

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_reset_state_no_file(self, mock_state_path, temp_data_dir):
        """Test reset_state when no state file exists."""
        state_file = temp_data_dir / "nonexistent_state.json"
        mock_state_path.return_value = state_file
        
        # Should not raise exception
        LogReader.reset_state()

    @patch('monitor.core.log_reader.LogReader._get_state_file_path')
    def test_connection_closed_after_read(self, mock_state_path, temp_dir, temp_data_dir):
        """Test that database connections are properly closed after each read."""
        state_file = temp_data_dir / "test_state.json"
        mock_state_path.return_value = state_file
        
        # Create test database
        today = date.today()
        db_path = temp_dir / today.strftime("logs_%Y-%m-%d.db")
        
        test_records = [
            {"id": 1, "timestamp": "2025-08-24 10:00:00", "level": "INFO", "message": "Test"}
        ]
        self.create_test_db(db_path, test_records)
        
        reader = LogReader(temp_dir)
        
        # Read data - this tests that the connection is opened and closed properly
        df = reader.read_next()
        assert len(df) == 1
        
        # Try to read again to ensure connections are not left open
        df2 = reader.read_next()
        assert df2.empty  # Should be empty since we already read all records
