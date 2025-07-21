"""Contact database for persistent storage of contacts"""

import sqlite3
import os
from typing import List, Tuple

class ContactDatabase:
    """SQLite database for contact storage"""
    
    def __init__(self, db_file: str = "data/contacts.db"):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS phones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE NOT NULL
                )
            ''')
    
    def add_email(self, email: str) -> bool:
        """Add email to database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute("INSERT INTO emails (email) VALUES (?)", (email,))
            return True
        except sqlite3.IntegrityError:
            return False  # Email already exists
    
    def add_phone(self, phone: str) -> bool:
        """Add phone to database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute("INSERT INTO phones (phone) VALUES (?)", (phone,))
            return True
        except sqlite3.IntegrityError:
            return False  # Phone already exists
    
    def get_emails(self) -> List[Tuple[int, str]]:
        """Get all emails (id, email)"""
        with sqlite3.connect(self.db_file) as conn:
            return conn.execute("SELECT id, email FROM emails ORDER BY email").fetchall()
    
    def get_phones(self) -> List[Tuple[int, str]]:
        """Get all phones (id, phone)"""
        with sqlite3.connect(self.db_file) as conn:
            return conn.execute("SELECT id, phone FROM phones ORDER BY phone").fetchall()
    
    def remove_email(self, email_id: int) -> bool:
        """Remove email by ID"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
            return True
        except:
            return False
    
    def remove_phone(self, phone_id: int) -> bool:
        """Remove phone by ID"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute("DELETE FROM phones WHERE id = ?", (phone_id,))
            return True
        except:
            return False
