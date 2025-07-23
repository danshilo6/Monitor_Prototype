"""Contact database for persistent storage of contacts"""

import sqlite3
import os
from typing import List, Tuple
from monitor.log_setup import get_logger

class ContactDatabase:
    """SQLite database for contact storage"""
    
    def __init__(self, db_file: str = "data/contacts.db"):
        self.logger = get_logger("monitor.services.contact_db")
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self.logger.info(f"Initializing contact database: {db_file}")
        self._init_database()
        self.logger.debug("Contact database initialized successfully")
    
    def _init_database(self):
        """Initialize database tables"""
        self.logger.debug("Creating database tables if they don't exist")
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
            self.logger.info(f"Added email: {email}")
            return True
        except sqlite3.IntegrityError:
            self.logger.warning(f"Email already exists: {email}")
            return False  # Email already exists
        except Exception as e:
            self.logger.error(f"Failed to add email '{email}': {e}")
            return False
    
    def add_phone(self, phone: str) -> bool:
        """Add phone to database"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute("INSERT INTO phones (phone) VALUES (?)", (phone,))
            self.logger.info(f"Added phone: {phone}")
            return True
        except sqlite3.IntegrityError:
            self.logger.warning(f"Phone already exists: {phone}")
            return False  # Phone already exists
        except Exception as e:
            self.logger.error(f"Failed to add phone '{phone}': {e}")
            return False
    
    def get_emails(self) -> List[Tuple[int, str]]:
        """Get all emails (id, email)"""
        self.logger.debug("Retrieving all emails from database")
        with sqlite3.connect(self.db_file) as conn:
            results = conn.execute("SELECT id, email FROM emails ORDER BY email").fetchall()
            self.logger.debug(f"Retrieved {len(results)} emails")
            return results
    
    def get_phones(self) -> List[Tuple[int, str]]:
        """Get all phones (id, phone)"""
        self.logger.debug("Retrieving all phones from database")
        with sqlite3.connect(self.db_file) as conn:
            results = conn.execute("SELECT id, phone FROM phones ORDER BY phone").fetchall()
            self.logger.debug(f"Retrieved {len(results)} phones")
            return results
    
    def remove_email(self, email_id: int) -> bool:
        """Remove email by ID"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
                if cursor.rowcount > 0:
                    self.logger.info(f"Removed email with ID: {email_id}")
                    return True
                else:
                    self.logger.warning(f"Email with ID {email_id} not found")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to remove email with ID {email_id}: {e}")
            return False
    
    def remove_phone(self, phone_id: int) -> bool:
        """Remove phone by ID"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute("DELETE FROM phones WHERE id = ?", (phone_id,))
                if cursor.rowcount > 0:
                    self.logger.info(f"Removed phone with ID: {phone_id}")
                    return True
                else:
                    self.logger.warning(f"Phone with ID {phone_id} not found")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to remove phone with ID {phone_id}: {e}")
            return False
