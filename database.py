import aiosqlite
from datetime import datetime
from typing import Optional, Tuple


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
        try:
            print(f"📥 إدخال ملف إلى قاعدة البيانات: {file_id} - {file_type} - {user_id} - {meta_data}")
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO media_files (file_id, file_type, user_id, meta_data)
                    VALUES (?, ?, ?, ?)
                ''', (file_id, file_type, user_id, str(meta_data) if meta_data else None))
                await db.commit()
            print("✅ تم حفظ الملف في قاعدة البيانات بنجاح!")
        except aiosqlite.Error as e:
            print(f"❌ خطأ أثناء إدخال البيانات: {e}")
            raise DatabaseError(f"فشل حفظ الملف: {str(e)}") from e


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
                result = await cursor.fetchone()
                print(f"🔍 استرجاع الملف الأخير: {result}")
                return result
        except aiosqlite.Error as e:
            print(f"❌ خطأ أثناء جلب الملف: {e}")
            raise DatabaseError(f"فشل جلب الملف: {str(e)}") from e

class DatabaseError(Exception):
    """استثناء خاص بأخطاء قاعدة البيانات"""
    pass
