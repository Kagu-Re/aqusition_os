"""Test helpers for Windows file locking issues."""
import gc
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Windows-specific cleanup helper
def force_close_db_connections(db_path: str) -> None:
    """Force close all SQLite connections to a database file.
    
    On Windows, SQLite keeps file handles open even after connections are closed.
    This function forces garbage collection and waits for handles to be released.
    """
    if sys.platform == "win32":
        # Force garbage collection to close any lingering connections
        gc.collect()
        # Small delay to allow Windows to release file handles
        time.sleep(0.1)
        
        # Try to open and immediately close the database to ensure it's unlocked
        try:
            import sqlite3
            con = sqlite3.connect(db_path, timeout=1.0)
            con.close()
        except Exception:
            pass
        
        # Another garbage collection pass
        gc.collect()
        time.sleep(0.05)


def cleanup_temp_db(db_path: str, max_retries: int = 3) -> None:
    """Clean up a temporary database file with retry logic for Windows.
    
    Args:
        db_path: Path to the database file
        max_retries: Maximum number of retry attempts
    """
    if not os.path.exists(db_path):
        return
    
    force_close_db_connections(db_path)
    
    # Try to delete with retries
    for attempt in range(max_retries):
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            # Also try to remove WAL and SHM files
            wal_path = db_path + "-wal"
            shm_path = db_path + "-shm"
            if os.path.exists(wal_path):
                try:
                    os.remove(wal_path)
                except Exception:
                    pass
            if os.path.exists(shm_path):
                try:
                    os.remove(shm_path)
                except Exception:
                    pass
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.2 * (attempt + 1))  # Exponential backoff
                force_close_db_connections(db_path)
            else:
                # Last attempt failed, but don't raise - Windows cleanup is best-effort
                pass
