"""
База даних для зберігання статистики постів
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "bot_stats.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Ініціалізація бази даних"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблиця постів
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                threads_id TEXT,
                post_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                error_message TEXT
            )
        """)
        
        # Таблиця налаштувань
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("База даних ініціалізована")
    
    def add_post(self, telegram_id: int, threads_id: Optional[str], 
                 post_type: str, status: str, error_message: Optional[str] = None):
        """Додати пост у базу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO posts (telegram_id, threads_id, post_type, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (telegram_id, threads_id, post_type, status, error_message))
        
        conn.commit()
        conn.close()
    
    def get_stats(self, days: int = 1) -> Dict:
        """Отримати статистику за N днів"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_from = datetime.now() - timedelta(days=days)
        
        # Загальна кількість постів
        cursor.execute("""
            SELECT COUNT(*) FROM posts 
            WHERE created_at >= ? AND status = 'success'
        """, (date_from,))
        total_posts = cursor.fetchone()[0]
        
        # Кількість помилок
        cursor.execute("""
            SELECT COUNT(*) FROM posts 
            WHERE created_at >= ? AND status = 'error'
        """, (date_from,))
        total_errors = cursor.fetchone()[0]
        
        # По типах контенту
        cursor.execute("""
            SELECT post_type, COUNT(*) FROM posts 
            WHERE created_at >= ? AND status = 'success'
            GROUP BY post_type
        """, (date_from,))
        by_type = dict(cursor.fetchall())
        
        # Останній пост
        cursor.execute("""
            SELECT created_at, post_type FROM posts 
            WHERE status = 'success'
            ORDER BY created_at DESC LIMIT 1
        """)
        last_post = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_posts': total_posts,
            'total_errors': total_errors,
            'by_type': by_type,
            'last_post': last_post
        }
    
    def get_recent_logs(self, limit: int = 20, errors_only: bool = False) -> List[Dict]:
        """Отримати останні логи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if errors_only:
            cursor.execute("""
                SELECT telegram_id, post_type, status, error_message, created_at
                FROM posts 
                WHERE status = 'error'
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT telegram_id, post_type, status, error_message, created_at
                FROM posts 
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                'telegram_id': row[0],
                'post_type': row[1],
                'status': row[2],
                'error_message': row[3],
                'created_at': row[4]
            })
        
        return logs
    
    def set_setting(self, key: str, value: str):
        """Зберегти налаштування"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Отримати налаштування"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        conn.close()
        
        return row[0] if row else default

