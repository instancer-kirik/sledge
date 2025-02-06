import sqlite3
import os
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QDateTime

class HistoryManager(QObject):
    """Manages browser history"""
    
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        
        # Set up history database
        self.db_path = os.path.expanduser('~/.sledge/history.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_db()
        
    def _init_db(self):
        """Initialize the history database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    visit_count INTEGER DEFAULT 1
                )
            ''')
            conn.commit()
            
    def add_visit(self, url, title=None):
        """Add a URL visit to history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if URL exists
            cursor.execute('SELECT id, visit_count FROM history WHERE url = ?', (url,))
            result = cursor.fetchone()
            
            if result:
                # Update existing entry
                cursor.execute('''
                    UPDATE history 
                    SET visit_count = ?, visit_time = CURRENT_TIMESTAMP, title = ?
                    WHERE id = ?
                ''', (result[1] + 1, title, result[0]))
            else:
                # Add new entry
                cursor.execute('''
                    INSERT INTO history (url, title)
                    VALUES (?, ?)
                ''', (url, title))
                
            conn.commit()
            
    def get_history(self, limit=100):
        """Get recent history entries"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, title, visit_time, visit_count
                FROM history
                ORDER BY visit_time DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
            
    def search_history(self, query, limit=50):
        """Search history entries"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, title, visit_time, visit_count
                FROM history
                WHERE url LIKE ? OR title LIKE ?
                ORDER BY visit_time DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            return cursor.fetchall()
            
    def clear_history(self):
        """Clear all history entries"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM history')
            conn.commit() 