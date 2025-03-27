import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple, List


class DatabaseError(Exception):
    """استثناء خاص بأخطاء قاعدة البيانات"""
    pass


class AsyncMediaStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize_db(self):
        """تهيئة قاعدة البيانات وإنشاء الجدول"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS media_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        user_id INTEGER,
                        meta_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await db.commit()
        except Exception as e:
            raise DatabaseError(f"فشل في تهيئة قاعدة البيانات: {e}")

    async def asave_file(self, file_id: str, file_type: str, user_id: Optional[int] = None, meta_data: Optional[dict] = None):
        """حفظ ملف في قاعدة البيانات"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO media_files (file_id, file_type, user_id, meta_data)
                    VALUES (?, ?, ?, ?)
                ''', (file_id, file_type, user_id, json.dumps(meta_data) if meta_data else None))
                await db.commit()
        except Exception as e:
            raise DatabaseError(f"فشل في حفظ الملف: {e}")

    async def aget_latest_file(self) -> Optional[Tuple[str, str]]:
        """إرجاع آخر ملف مخزن"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT file_id, file_type 
                    FROM media_files 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''')
                return await cursor.fetchone()
        except Exception as e:
            raise DatabaseError(f"خطأ أثناء استرجاع آخر ملف: {e}")

    async def asearch_files(self, query: str) -> List[Tuple[str, str, dict]]:
        """البحث عن الملفات باستخدام `meta_data` أو `file_type`"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT file_id, file_type, meta_data 
                    FROM media_files 
                    WHERE meta_data LIKE ? OR file_type LIKE ?
                ''', (f"%{query}%", f"%{query}%"))
                results = await cursor.fetchall()
                return [(file_id, file_type, json.loads(meta_data) if meta_data else {}) for file_id, file_type, meta_data in results]
        except Exception as e:
            raise DatabaseError(f"خطأ أثناء البحث عن الملفات: {e}")

    async def adelete_old_files(self, days: int):
        """حذف الملفات الأقدم من عدد معين من الأيام"""
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM media_files WHERE created_at < ?
                ''', (threshold_date.strftime('%Y-%m-%d %H:%M:%S'),))
                await db.commit()
        except Exception as e:
            raise DatabaseError(f"خطأ أثناء حذف الملفات القديمة: {e}")
