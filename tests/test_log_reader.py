"""Tests for LogReader class"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from monitor.core.log_reader import LogReader


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test databases"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for state files"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_db(temp_dir):
    """Create a sample database with test data"""
    today = date.today()
    db_path = temp_dir / f"logs_{today.strftime('%Y-%m-%d')}.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create logs table
    cursor.execute("""
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            message TEXT
        )
    """)
    
    # Insert sample data
    sample_logs = [
        ("2025-08-24 10:00:00", "INFO", "Application started"),
        ("2025-08-24 10:01:00", "DEBUG", "Debug message"),
        ("2025-08-24 10:02:00", "ERROR", "An error occurred"),
        ("2025-08-24 10:03:00", "INFO", "Process completed"),
        ("2025-08-24 10:04:00", "WARNING", "Warning message"),
    ]
    
    cursor.executemany(
        "INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
        sample_logs
    )
    
    conn.commit()
    conn.close()
    
    return db_path


@pytest.fixture
def mock_state_file_path(temp_data_dir):
    """Mock the state file path to use temp directory"""
    state_file = temp_data_dir / "log_reader_state.json"
    
    with patch.object(LogReader, '_get_state_file_path', return_value=state_file):
        yield state_file


class TestLogReader:
    """Test cases for LogReader class"""
    
    def test_init_creates_reader(self, temp_dir, mock_state_file_path):
        """Test that LogReader initializes correctly"""
        reader = LogReader(temp_dir)
        
        assert reader._dir == temp_dir
        assert reader._table == "logs"
        assert reader._pattern == "logs_%Y-%m-%d.db"
        assert reader._state_file == mock_state_file_path
    
    def test_init_with_custom_parameters(self, temp_dir, mock_state_file_path):
        """Test LogReader initialization with custom parameters"""
        reader = LogReader(
            directory=temp_dir,
            table="custom_logs",
            pattern="custom_%Y_%m_%d.db"
        )
        
        assert reader._dir == temp_dir
        assert reader._table == "custom_logs"
        assert reader._pattern == "custom_%Y_%m_%d.db"
    
    def test_read_next_empty_when_no_db(self, temp_dir, mock_state_file_path):
        """Test that read_next returns empty DataFrame when database doesn't exist"""
        reader = LogReader(temp_dir)
        result = reader.read_next()
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    def test_read_next_all_data(self, temp_dir, sample_db, mock_state_file_path):
        """Test reading all data from database"""
        reader = LogReader(temp_dir)
        result = reader.read_next()
        
        assert not result.empty
        assert len(result) == 5
        assert list(result.columns) == ["id", "timestamp", "level", "message"]
        assert result.iloc[0]["message"] == "Application started"
        assert result.iloc[-1]["message"] == "Warning message"
        
        # Verify state was saved correctly
        with open(mock_state_file_path, 'r') as f:
            state = json.load(f)
            assert state['last_id'] == 5
    
    def test_read_next_with_limit(self, temp_dir, sample_db, mock_state_file_path):
        """Test reading data with limit"""
        reader = LogReader(temp_dir)
        result = reader.read_next(limit=3)
        
        assert not result.empty
        assert len(result) == 3
        assert result.iloc[0]["message"] == "Application started"
        assert result.iloc[-1]["message"] == "An error occurred"
        
        # Verify state was saved correctly
        with open(mock_state_file_path, 'r') as f:
            state = json.load(f)
            assert state['last_id'] == 3
    
    def test_read_next_incremental(self, temp_dir, sample_db, mock_state_file_path):
        """Test incremental reading (only new records)"""
        reader = LogReader(temp_dir)
        
        # First read - get first 2 records
        result1 = reader.read_next(limit=2)
        assert len(result1) == 2
        
        # Verify state was saved
        with open(mock_state_file_path, 'r') as f:
            state = json.load(f)
            assert state['last_id'] == 2
        
        # Second read - get next 2 records
        result2 = reader.read_next(limit=2)
        assert len(result2) == 2
        assert result2.iloc[0]["id"] == 3  # Should start from id 3
        
        # Verify state was updated
        with open(mock_state_file_path, 'r') as f:
            state = json.load(f)
            assert state['last_id'] == 4
        
        # Third read - get remaining record
        result3 = reader.read_next()
        assert len(result3) == 1
        assert result3.iloc[0]["id"] == 5
        
        # Verify final state
        with open(mock_state_file_path, 'r') as f:
            state = json.load(f)
            assert state['last_id'] == 5
        
        # Fourth read - no new data
        result4 = reader.read_next()
        assert result4.empty
    
    def test_state_persistence(self, temp_dir, sample_db, mock_state_file_path):
        """Test that state is saved and loaded correctly"""
        # First reader - read some data
        reader1 = LogReader(temp_dir)
        result1 = reader1.read_next(limit=3)
        
        # Check state file was created with correct data
        assert mock_state_file_path.exists()
        with open(mock_state_file_path, 'r') as f:
            state = json.load(f)
            assert state['last_id'] == 3
            assert state['day'] == date.today().isoformat()
        
        # Second reader - should resume from where first left off
        reader2 = LogReader(temp_dir)
        
        result2 = reader2.read_next()
        assert len(result2) == 2  # Should get remaining 2 records
        assert result2.iloc[0]["id"] == 4  # Should start from id 4
    
    def test_state_reset_on_new_day(self, temp_dir, sample_db, mock_state_file_path):
        """Test that state resets when date changes"""
        # Create state from yesterday
        yesterday_state = {
            'last_id': 10,
            'day': (date.today() - timedelta(days=1)).isoformat()
        }
        
        with open(mock_state_file_path, 'w') as f:
            json.dump(yesterday_state, f)
        
        # Reader should start fresh today
        reader = LogReader(temp_dir)
        result = reader.read_next()
        
        # Should read all 5 records since we started fresh
        assert len(result) == 5  # All records should be read
        assert result.iloc[0]["id"] == 1  # Should start from id 1
    
    def test_reset_state_static_method(self, temp_dir, mock_state_file_path):
        """Test the static reset_state method"""
        # Create a state file
        state = {'last_id': 5, 'day': date.today().isoformat()}
        with open(mock_state_file_path, 'w') as f:
            json.dump(state, f)
        
        assert mock_state_file_path.exists()
        
        # Reset state
        LogReader.reset_state()
        
        # State file should be deleted
        assert not mock_state_file_path.exists()
    
    def test_reset_state_no_file(self, mock_state_file_path, capsys):
        """Test reset_state when no state file exists"""
        assert not mock_state_file_path.exists()
        
        LogReader.reset_state()
        
        captured = capsys.readouterr()
        assert "No LogReader state file found to reset" in captured.out
    
    @patch('monitor.core.log_reader.date')
    def test_day_switching(self, mock_date, temp_dir, mock_state_file_path):
        """Test that LogReader switches to new database when day changes"""
        # Setup: Create databases for two different days
        day1 = date(2025, 8, 24)
        day2 = date(2025, 8, 25)
        
        # Create database for day 1
        db1_path = temp_dir / f"logs_{day1.strftime('%Y-%m-%d')}.db"
        conn1 = sqlite3.connect(db1_path)
        cursor1 = conn1.cursor()
        cursor1.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                message TEXT
            )
        """)
        cursor1.execute(
            "INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
            ("2025-08-24 10:00:00", "INFO", "Day 1 message")
        )
        conn1.commit()
        conn1.close()
        
        # Create database for day 2
        db2_path = temp_dir / f"logs_{day2.strftime('%Y-%m-%d')}.db"
        conn2 = sqlite3.connect(db2_path)
        cursor2 = conn2.cursor()
        cursor2.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                message TEXT
            )
        """)
        cursor2.execute(
            "INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
            ("2025-08-25 10:00:00", "INFO", "Day 2 message")
        )
        conn2.commit()
        conn2.close()
        
        # Test day switching
        # Start on day 1
        mock_date.today.return_value = day1
        reader = LogReader(temp_dir)
        
        result1 = reader.read_next()
        assert len(result1) == 1
        assert result1.iloc[0]["message"] == "Day 1 message"
        
        # Switch to day 2 - same reader instance should handle day change
        mock_date.today.return_value = day2
        
        result2 = reader.read_next()
        assert len(result2) == 1
        assert result2.iloc[0]["message"] == "Day 2 message"
    
    def test_connection_cleanup_on_error(self, temp_dir, mock_state_file_path):
        """Test that connections are properly closed even when errors occur"""
        # Create a database
        today = date.today()
        db_path = temp_dir / f"logs_{today.strftime('%Y-%m-%d')}.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO logs DEFAULT VALUES")
        conn.commit()
        conn.close()
        
        reader = LogReader(temp_dir)
        
        # Mock pandas to raise an exception
        with patch('pandas.read_sql_query', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                reader.read_next()
        
        # Connection should still be cleaned up - we can verify this by
        # successfully reading afterwards
        result = reader.read_next()
        assert len(result) == 1
    
    def test_custom_table_name(self, temp_dir, mock_state_file_path):
        """Test LogReader with custom table name"""
        # Create database with custom table
        today = date.today()
        db_path = temp_dir / f"logs_{today.strftime('%Y-%m-%d')}.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE custom_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT
            )
        """)
        cursor.execute("INSERT INTO custom_logs (data) VALUES (?)", ("test data",))
        conn.commit()
        conn.close()
        
        reader = LogReader(temp_dir, table="custom_logs")
        result = reader.read_next()
        
        assert len(result) == 1
        assert result.iloc[0]["data"] == "test data"
    
    def test_readonly_connection(self, temp_dir, mock_state_file_path):
        """Test that LogReader opens database in read-only mode"""
        # Create database
        today = date.today()
        db_path = temp_dir / f"logs_{today.strftime('%Y-%m-%d')}.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO logs DEFAULT VALUES")
        conn.commit()
        conn.close()
        
        reader = LogReader(temp_dir)
        
        # Verify the connection uses read-only mode by checking the URI
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            reader._get_db_connection()
            
            # Check that sqlite3.connect was called with read-only URI
            call_args = mock_connect.call_args
            assert call_args[0][0].startswith("file:")
            assert "mode=ro" in call_args[0][0]
            assert call_args[1]["uri"] is True
