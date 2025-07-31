"""
Simple Database to CSV Export
============================

Quick and simple export of SQLite database table to CSV format.
"""

import sqlite3
import csv
from pathlib import Path


def export_db_to_csv(db_path: str, csv_path: str = None) -> None:
    """
    Export SQLite database table to CSV file.
    
    Args:
        db_path: Path to the SQLite database file
        csv_path: Output CSV file path (optional, defaults to db_name.csv)
    """
    if csv_path is None:
        csv_path = Path(db_path).stem + ".csv"
    
    with sqlite3.connect(db_path) as conn:
        # Get the first (and likely only) table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_name = cursor.fetchone()[0]
        
        # Get all data
        cursor = conn.execute(f"SELECT * FROM {table_name}")
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Write to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(column_names)  # Headers
            writer.writerows(cursor.fetchall())  # All rows
    
    print(f"Exported to {csv_path}")


export_db_to_csv('logs_2025-07-27.db')