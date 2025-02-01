import sqlite3
import os
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

class HistoryManager(QObject):
    history_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser('~/.sledge/history.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        """Initialize the history database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    visit_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_url ON history(url)
            """)

    def add_visit(self, url, title):
        """Add a new page visit to history"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if URL exists
            cursor = conn.execute(
                "SELECT id, visit_count FROM history WHERE url = ?", 
                (url,)
            )
            result = cursor.fetchone()

            if result:
                # Update existing entry
                conn.execute("""
                    UPDATE history 
                    SET visit_count = ?, visit_time = CURRENT_TIMESTAMP, title = ?
                    WHERE id = ?
                """, (result[1] + 1, title, result[0]))
            else:
                # Add new entry
                conn.execute(
                    "INSERT INTO history (url, title) VALUES (?, ?)",
                    (url, title)
                )

        self.history_updated.emit()

    def get_history(self, limit=100, search=None):
        """Get browsing history"""
        with sqlite3.connect(self.db_path) as conn:
            if search:
                cursor = conn.execute("""
                    SELECT url, title, visit_time, visit_count 
                    FROM history 
                    WHERE url LIKE ? OR title LIKE ?
                    ORDER BY visit_time DESC LIMIT ?
                """, (f"%{search}%", f"%{search}%", limit))
            else:
                cursor = conn.execute("""
                    SELECT url, title, visit_time, visit_count 
                    FROM history 
                    ORDER BY visit_time DESC LIMIT ?
                """, (limit,))
            
            return cursor.fetchall()

    def clear_history(self, days=None):
        """Clear browsing history"""
        with sqlite3.connect(self.db_path) as conn:
            if days:
                conn.execute("""
                    DELETE FROM history 
                    WHERE julianday('now') - julianday(visit_time) > ?
                """, (days,))
            else:
                conn.execute("DELETE FROM history")

        self.history_updated.emit() 