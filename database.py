import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Tuple, List


class AsyncMediaStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize_db(self):
        """تهيئة قاعدة البيانات وإنشاء الجدول"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    user_id INTEGER,
                    meta_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()

    async def asave_file(self, file_id: str, file_type: str, user_id: Optional[int] = None, meta_data: Optional[dict] = None):
        """حفظ ملف في قاعدة البيانات"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO media_files (file_id, file_type, user_id, meta_data)
                VALUES (?, ?, ?, ?)
            ''', (file_id, file_type, user_id, str(meta_data) if meta_data else None))
            await db.commit()

    async def aget_latest_file(self) -> Optional[Tuple[str, str]]:
        """إرجاع آخر ملف مخزن"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT file_id, file_type 
                FROM media_files 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            return await cursor.fetchone()

    async def asearch_files(self, query: str) -> List[Tuple[str, str, str]]:
        """البحث عن الملفات"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT file_id, file_type, meta_data FROM media_files
                WHERE meta_data LIKE ? OR file_type LIKE ?
            ''', (f"%{query}%", f"%{query}%"))
            return await cursor.fetchall()

    async def adelete_old_files(self, days: int):
        """حذف الملفات الأقدم من عدد معين من الأيام"""
        threshold_date = datetime.utcnow() - timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM media_files WHERE created_at < ?
            ''', (threshold_date.strftime('%Y-%m-%d %H:%M:%S'),))
            await db.commit()


class DatabaseError(Exception):
    """استثناء خاص بأخطاء قاعدة البيانات"""
    pass