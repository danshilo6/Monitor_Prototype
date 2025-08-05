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
    """

    def __init__(self, directory: Path, table: str = "logs", pattern: str = "logs_%Y-%m-%d.db") -> None:
        self._dir = Path(directory)
        self._table = table
        self._pattern = pattern
        
        # State file always goes in project root's data folder
        self._state_file = self._get_state_file_path()
        
        self._conn: sqlite3.Connection | None = None
        self._current_day: date | None = None
        self._last_id: int = 0
        
        self._load_state()
        self._open_db_for(date.today())  # open today's DB (if present)

    def _load_state(self) -> None:
        """Load last_id only if it's from today, otherwise start fresh."""
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

    @staticmethod
    def _get_state_file_path() -> Path:
        """Get the path to the LogReader state file."""
        project_root = Path(__file__).parent.parent.parent  # From monitor/core/ to project root
        return project_root / "data" / "log_reader_state.json"

    # ---------- public API -------------------------------------------------
    def read_next(self, limit: int = None) -> pd.DataFrame:
        """
        Return all new rows (id > last_id) that haven't been read yet.
        If limit is specified, return up to that many rows.
        Empty DataFrame => nothing new.
        """
        self._maybe_switch_db()

        # If no connection is available (database doesn't exist yet), return empty DataFrame
        if self._conn is None:
            return pd.DataFrame()

        if limit is None:
            # Read all unread rows
            df = pd.read_sql_query(
                f"""
                SELECT *
                FROM {self._table}
                WHERE id > ?
                ORDER BY id ASC
                """,
                self._conn,
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
                self._conn,
                params=(self._last_id, limit),
            )

        if not df.empty:
            self._last_id = int(df["id"].iloc[-1])
            self._save_state()  # Save state after reading new data

        return df

    def close(self) -> None:
        self._save_state()  # Save state on close
        if self._conn:
            self._conn.close()

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

    # ---------- internal helpers ------------------------------------------
    def _maybe_switch_db(self) -> None:
        today = date.today()
        if today != self._current_day:
            self._open_db_for(today)

    def _open_db_for(self, day: date) -> None:
        db_path = self._dir / day.strftime(self._pattern)

        # If today's file doesn't exist yet, keep current connection (if any)
        if not db_path.is_file():
            return

        if self._conn:
            self._conn.close()

        self._conn = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row

        self._current_day = day
        
        # When switching to a new day, check if we should restore state or start fresh
        if day == date.today():
            # For today, we might have a saved last_id - it was loaded in _load_state()
            pass  # Keep the last_id from _load_state()
        else:
            # For any other day (shouldn't happen in normal operation), start from 0
            self._last_id = 0

