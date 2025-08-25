from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import date
import pandas as pd


class LogReader:
    """
    Incrementally reads from a daily‑rotated SQLite DB named logs_YYYY_MM_DD.db.

    • Keeps track of the last `id` already returned.
    • On every `read_next()` call, if the calendar day changed *and* today's DB
      file exists, the reader switches to it automatically.
    • Results are returned as a pandas DataFrame.
    • Opens and closes DB connection for each read operation.
    """

    def __init__(self, directory: Path, table: str = "logs", pattern: str = "logs_%Y-%m-%d.db") -> None:
        self._dir = Path(directory)
        self._table = table
        self._pattern = pattern
        
        # State file always goes in project root's data folder
        self._state_file = self._get_state_file_path()
        
        self._last_id: int = 0
        self._current_day: date | None = None  # Track which day we're reading from
        
        self._load_state()

    def _load_state(self) -> None:
        """Load last_id only if it's from today, otherwise start fresh."""
        self._current_day = date.today()  # Always set current day
        
        try:
            if self._state_file.exists():
                with open(self._state_file, 'r') as f:
                    state = json.load(f)
                    
                saved_day = state.get('day')
                today = date.today().isoformat()
                
                # Only restore last_id if it's from today
                if saved_day == today:
                    self._last_id = state.get('last_id', 0)
                else:
                    self._last_id = 0  # New day = start fresh
                    
        except Exception:
            self._last_id = 0  # Safe fallback

    def _save_state(self) -> None:
        """Save current last_id with today's date."""
        try:
            state = {
                'last_id': self._last_id,
                'day': date.today().isoformat()
            }
            with open(self._state_file, 'w') as f:
                json.dump(state, f)
        except Exception:
            pass  # Don't crash if save fails

    def _check_day_change(self) -> None:
        """Check if day has changed and reset last_id if it has."""
        today = date.today()
        if self._current_day != today:
            self._last_id = 0  # Reset for new day
            self._current_day = today
            self._save_state()  # Save the reset state

    @staticmethod
    def _get_state_file_path() -> Path:
        """Get the path to the LogReader state file."""
        project_root = Path(__file__).parent.parent.parent  # From monitor/core/ to project root
        return project_root / "data" / "log_reader_state.json"

    def _get_db_path_for_day(self, day: date) -> Path:
        """Get the database file path for a specific day."""
        return self._dir / day.strftime(self._pattern)

    def _open_connection(self, db_path: Path) -> sqlite3.Connection | None:
        """Open a read-only connection to the database file."""
        if not db_path.is_file():
            return None
            
        conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        return conn

    # ---------- public API -------------------------------------------------
    def read_next(self, limit: int = None) -> pd.DataFrame:
        """
        Return all new rows (id > last_id) that haven't been read yet.
        If limit is specified, return up to that many rows.
        Empty DataFrame => nothing new.
        """
        # Check if day has changed and reset if needed
        self._check_day_change()
        
        today = date.today()
        db_path = self._get_db_path_for_day(today)
        
        # Open connection for this read operation
        conn = self._open_connection(db_path)
        if conn is None:
            return pd.DataFrame()

        try:
            print(f"trying to read from logs db file {db_path}")
            if limit is None:
                # Read all unread rows
                df = pd.read_sql_query(
                    f"""
                    SELECT *
                    FROM {self._table}
                    WHERE id > ?
                    ORDER BY id ASC
                    """,
                    conn,
                    params=(self._last_id,),
                )
            else:
                # Read up to limit rows (for backward compatibility)
                df = pd.read_sql_query(
                    f"""
                    SELECT *
                    FROM {self._table}
                    WHERE id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    conn,
                    params=(self._last_id, limit),
                )

            if not df.empty:
                print(f"successfuly read from logs db file {db_path}")
                self._last_id = int(df["id"].iloc[-1])
                self._save_state()  # Save state after reading new data

            return df
            
        finally:
            # Always close the connection after the read operation
            conn.close()

    def close(self) -> None:
        """Save state on close. No persistent connection to close."""
        self._save_state()

    @staticmethod
    def reset_state() -> None:
        """
        Reset the LogReader state file.
        
        This is useful for testing or when resetting the log database.
        Removes the state file so the next LogReader instance starts from scratch.
        """
        try:
            state_file = LogReader._get_state_file_path()
            
            if state_file.exists():
                state_file.unlink()  # Delete the file
                print(f"LogReader state reset: {state_file}")
            else:
                print("No LogReader state file found to reset")
                
        except Exception as e:
            print(f"Error resetting LogReader state: {e}")

