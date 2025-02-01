import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

class ExtensionStorage:
    """Persistent storage for extensions using SQLite"""
    
    def __init__(self, extension_id: str):
        self.extension_id = extension_id
        self.db_path = Path.home() / '.sledge' / 'storage' / f'{extension_id}.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    storage_area TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create trigger to update timestamp
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_timestamp
                AFTER UPDATE ON storage
                BEGIN
                    UPDATE storage SET updated_at = CURRENT_TIMESTAMP
                    WHERE key = NEW.key;
                END
            """)

    @contextmanager
    def _get_connection(self):
        """Get a database connection with automatic closing"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string"""
        return json.dumps(value)

    def _deserialize_value(self, value_str: str) -> Any:
        """Deserialize value from JSON string"""
        return json.loads(value_str)

    def get(self, keys: Optional[List[str]] = None, area: str = 'local') -> Dict[str, Any]:
        """Get one or more items from storage"""
        with self._get_connection() as conn:
            if keys is None:
                # Get all items
                cursor = conn.execute(
                    "SELECT key, value FROM storage WHERE storage_area = ?",
                    (area,)
                )
            else:
                # Get specific keys
                placeholders = ','.join('?' * len(keys))
                cursor = conn.execute(
                    f"SELECT key, value FROM storage WHERE storage_area = ? AND key IN ({placeholders})",
                    (area, *keys)
                )
            
            return {
                row[0]: self._deserialize_value(row[1])
                for row in cursor.fetchall()
            }

    def set(self, items: Dict[str, Any], area: str = 'local'):
        """Set one or more items in storage"""
        with self._get_connection() as conn:
            for key, value in items.items():
                serialized = self._serialize_value(value)
                conn.execute("""
                    INSERT OR REPLACE INTO storage (key, value, storage_area)
                    VALUES (?, ?, ?)
                """, (key, serialized, area))
            conn.commit()

    def remove(self, keys: List[str], area: str = 'local'):
        """Remove one or more items from storage"""
        with self._get_connection() as conn:
            placeholders = ','.join('?' * len(keys))
            conn.execute(
                f"DELETE FROM storage WHERE storage_area = ? AND key IN ({placeholders})",
                (area, *keys)
            )
            conn.commit()

    def clear(self, area: str = 'local'):
        """Remove all items from storage"""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM storage WHERE storage_area = ?",
                (area,)
            )
            conn.commit()

    def get_quota(self) -> Dict[str, int]:
        """Get storage usage and quota information"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT storage_area, SUM(LENGTH(value)) as size FROM storage GROUP BY storage_area"
            )
            usage = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Default quota (5MB per area)
            quota = 5 * 1024 * 1024
            
            return {
                'usage': usage,
                'quota': quota,
                'remaining': {
                    area: quota - size
                    for area, size in usage.items()
                }
            }

class StorageManager:
    """Manages storage for all extensions"""
    
    def __init__(self):
        self.storages: Dict[str, ExtensionStorage] = {}
        
    def get_storage(self, extension_id: str) -> ExtensionStorage:
        """Get or create storage for an extension"""
        if extension_id not in self.storages:
            self.storages[extension_id] = ExtensionStorage(extension_id)
        return self.storages[extension_id]
        
    def cleanup_storage(self, extension_id: str):
        """Clean up storage when extension is uninstalled"""
        if extension_id in self.storages:
            storage = self.storages.pop(extension_id)
            try:
                storage.db_path.unlink()
            except Exception as e:
                print(f"Error cleaning up storage for {extension_id}: {e}")

    def get_total_usage(self) -> Dict[str, int]:
        """Get total storage usage across all extensions"""
        total = {}
        for storage in self.storages.values():
            quota = storage.get_quota()
            for area, size in quota['usage'].items():
                total[area] = total.get(area, 0) + size
        return total 