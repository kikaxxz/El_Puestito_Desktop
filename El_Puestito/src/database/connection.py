import sqlite3
import threading
from logger_setup import setup_logger
from src.path_manager import get_persistent_path

logger = setup_logger()

class DatabaseManager:
    def __init__(self, db_path=None):
        import os
        self.db_path = db_path or os.environ.get('PUESTITO_DB_PATH') or get_persistent_path("puestito.db")
        self.local = threading.local()
        logger.info(f"DatabaseManager inicializado. Conectando a: {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")

    def get_conn(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
            self.local.conn.execute("PRAGMA busy_timeout = 30000;") 
            self.local.conn.execute("PRAGMA foreign_keys = ON;")
        return self.local.conn

    def close_conn_for_thread(self):
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn

    def execute(self, query, params=()):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        if query.strip().upper().startswith("INSERT"):
            return cursor.lastrowid
        return cursor.rowcount

    def fetchone(self, query, params=()):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, query, params=()):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# Singleton instance
db_manager = DatabaseManager()
