from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import date
import pandas as pd


class LogReader:
    """
    Incrementally reads from a daily‑rotated SQLite DB named logs_YYYY_MM_DD.db.

    • Keeps track of the last `id` already returned.
    • On every `read_next()` call, if the calendar day changed *and* today’s DB
      file exists, the reader switches to it automatically.
    • Results are returned as a pandas DataFrame.
    """

    def __init__(self, directory: Path, table: str = "logs", pattern: str = "logs_%Y_%m_%d.db",
    ) -> None:
        self._dir = Path(directory)
        self._table = table
        self._pattern = pattern
        self._conn: sqlite3.Connection | None = None
        self._current_day: date | None = None
        self._last_id: int = 0
        self._open_db_for(date.today())  # open today’s DB (if present)

    # ---------- public API -------------------------------------------------
    def read_next(self, limit: int = None) -> pd.DataFrame:
        """
        Return all new rows (id > last_id) that haven't been read yet.
        If limit is specified, return up to that many rows.
        Empty DataFrame => nothing new.
        """
        self._maybe_switch_db()

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

        return df

    def close(self) -> None:
        if self._conn:
            self._conn.close()

    # ---------- internal helpers ------------------------------------------
    def _maybe_switch_db(self) -> None:
        today = date.today()
        if today != self._current_day:
            self._open_db_for(today)

    def _open_db_for(self, day: date) -> None:
        db_path = self._dir / day.strftime(self._pattern)

        # If today’s file doesn’t exist yet, keep current connection (if any)
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
        self._last_id = 0  # reset for the new file
