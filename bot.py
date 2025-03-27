import os
import logging
import sys
import asyncio
import aiosqlite
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN or len(BOT_TOKEN) < 20:
    raise ValueError("🚨 خطأ: لم يتم العثور على BOT_TOKEN صالح في ملف .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware(logger))


class AsyncMediaStorage:
    def __init__(self, db_path="media.db"):
        self.db_path = db_path

    async def initialize_db(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS media_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        meta_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await db.commit()
        except Exception as e:
            logger.error(f"🚨 خطأ أثناء تهيئة قاعدة البيانات: {e}")

    async def asave_file(self, file_id, file_type, user_id, meta_data):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO media_files (file_id, file_type, user_id, meta_data) 
                    VALUES (?, ?, ?, ?)
                ''', (file_id, file_type, user_id, json.dumps(meta_data)))
                await db.commit()
        except Exception as e:
            logger.error(f"🚨 خطأ أثناء حفظ الملف: {e}")

    async def alist_files(self, limit=10):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    SELECT id, file_type, meta_data 
                    FROM media_files 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"🚨 خطأ أثناء جلب قائمة الملفات: {e}")
            return []

    async def adelete_old_files(self, days):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM media_files 
                    WHERE created_at < datetime('now', ? || ' days')
                ''', (-days,))
                await db.commit()
        except Exception as e:
            logger.error(f"🚨 خطأ أثناء حذف الملفات القديمة: {e}")


storage = AsyncMediaStorage()


@dp.message_handler(content_types=[
    types.ContentType.PHOTO, types.ContentType.VIDEO, types.ContentType.DOCUMENT,
    types.ContentType.AUDIO, types.ContentType.ANIMATION
])
async def handle_media(message: Message):
    content_type = message.content_type
    file_id = None
    file_meta = {}

    if content_type == types.ContentType.DOCUMENT:
        file_id = message.document.file_id
        file_meta = {"file_name": message.document.file_name, "mime_type": message.document.mime_type}
    elif content_type == types.ContentType.PHOTO:
        file_id = message.photo[-1].file_id
        file_meta = {"mime_type": "image/jpeg"}
    elif content_type == types.ContentType.VIDEO:
        file_id = message.video.file_id
        file_meta = {"mime_type": message.video.mime_type}
    elif content_type == types.ContentType.AUDIO:
        file_id = message.audio.file_id
        file_meta = {"mime_type": message.audio.mime_type}
    elif content_type == types.ContentType.ANIMATION:
        file_id = message.animation.file_id
        file_meta = {"mime_type": "image/gif"}

    if file_id:
        await storage.asave_file(file_id=file_id, file_type=content_type, user_id=message.from_user.id, meta_data=file_meta)
        await message.reply("✅ **تم حفظ الملف بنجاح!**")

async def get_files_keyboard():
    files = await storage.alist_files(limit=10)

    keyboard = InlineKeyboardMarkup(row_width=1)
    for file in files:
        file_id, file_type, meta_data = file
        try:
            meta_data = json.loads(meta_data)
            file_name = meta_data.get("file_name", "ملف غير معروف")
        except json.JSONDecodeError:
            file_name = "ملف غير معروف"

        button = InlineKeyboardButton(text=file_name, callback_data=f"file_{file_id}")
        keyboard.add(button)

    return keyboard


@dp.message_handler(commands=['list_files'])
async def list_files(message: Message):
    keyboard = await get_files_keyboard()
    if not keyboard.inline_keyboard:
        await message.reply("📭 **لا يوجد ملفات مخزنة بعد!**")
        return
    await message.reply("📂 **الملفات المتاحة:**", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("file_"))
async def send_file_callback(callback_query: types.CallbackQuery):
    file_id = callback_query.data.split("_")[1]  
    try:
        async with aiosqlite.connect(storage.db_path) as db:
            cursor = await db.execute('SELECT file_id, file_type, meta_data FROM media_files WHERE id = ?', (file_id,))
            file = await cursor.fetchone()

        if file:
            file_id, file_type, meta_data = file
            meta_data = json.loads(meta_data)

            if file_type == types.ContentType.PHOTO:
                await bot.send_photo(callback_query.from_user.id, file_id)
            elif file_type == types.ContentType.VIDEO:
                await bot.send_video(callback_query.from_user.id, file_id)
            elif file_type == types.ContentType.DOCUMENT:
                await bot.send_document(callback_query.from_user.id, file_id)
            elif file_type == types.ContentType.AUDIO:
                await bot.send_audio(callback_query.from_user.id, file_id)
            elif file_type == types.ContentType.ANIMATION:
                await bot.send_animation(callback_query.from_user.id, file_id)
            else:
                await callback_query.message.answer("⚠️ نوع الملف غير مدعوم!")

            await callback_query.answer() 
        else:
            await callback_query.message.answer("⚠️ لم يتم العثور على الملف!")
    except Exception as e:
        logger.error(f"🚨 خطأ أثناء جلب الملف: {e}")
        await callback_query.message.answer("❌ حدث خطأ أثناء استرجاع الملف!")

@dp.message_handler(commands=['clear_old'])
async def clear_old_files(message: Message):
    args = message.get_args()
    if not args.isdigit():
        await message.reply("⚠️ **يرجى إدخال عدد الأيام!**\n📌 مثال: `/clear_old 30`")
        return

    days = int(args)
    await storage.adelete_old_files(days)
    await message.reply(f"🗑️ **تم حذف الملفات الأقدم من {days} يومًا!**")

@dp.message_handler(commands=['play'])
async def play_last_file(message: Message):
    try:
        async with aiosqlite.connect(storage.db_path) as db:
            cursor = await db.execute('''
                SELECT file_id, file_type FROM media_files 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            last_file = await cursor.fetchone()

        if last_file:
            file_id, file_type = last_file

            if file_type == types.ContentType.PHOTO:
                await bot.send_photo(message.chat.id, file_id)
            elif file_type == types.ContentType.VIDEO:
                await bot.send_video(message.chat.id, file_id)
            elif file_type == types.ContentType.DOCUMENT:
                await bot.send_document(message.chat.id, file_id)
            elif file_type == types.ContentType.AUDIO:
                await bot.send_audio(message.chat.id, file_id)
            elif file_type == types.ContentType.ANIMATION:
                await bot.send_animation(message.chat.id, file_id)
            else:
                await message.reply("⚠️ نوع الملف غير مدعوم!")

        else:
            await message.reply("📭 لا يوجد ملفات مخزنة بعد!")

    except Exception as e:
        logger.error(f"🚨 خطأ أثناء استرجاع الملف الأخير: {e}")
        await message.reply("❌ حدث خطأ أثناء استرجاع الملف!")

from datetime import datetime

@dp.message_handler(commands=['delete_by_date'])
async def delete_by_date(message: Message):
    args = message.get_args().strip()
    
    try:
        delete_date = datetime.strptime(args, "%Y-%m-%d").date()
    except ValueError:
        await message.reply("⚠️ **يرجى إدخال التاريخ بالتنسيق الصحيح (YYYY-MM-DD)**\n📌 مثال: `/delete_by_date 2024-03-01`")
        return

    try:
        async with aiosqlite.connect(storage.db_path) as db:
            await db.execute('''
                DELETE FROM media_files WHERE DATE(created_at) < ?
            ''', (delete_date,))
            await db.commit()

        await message.reply(f"🗑️ **تم حذف جميع الملفات قبل {delete_date}!**")

    except Exception as e:
        logger.error(f"🚨 خطأ أثناء حذف الملفات بتاريخ معين: {e}")
        await message.reply("❌ حدث خطأ أثناء حذف الملفات!")


@dp.message_handler(commands=['help'])
async def send_help(message: Message):
    help_text = """
    **🤖 قائمة الأوامر المتاحة:**
    
    📥 `/list_files` - عرض قائمة الملفات المخزنة.
    ▶️ `/play` - عرض آخر ملف تم رفعه.
    🗑️ `/clear_old <عدد الأيام>` - حذف الملفات الأقدم من عدد الأيام المحدد.
    🗓️ `/delete_by_date <YYYY-MM-DD>` - حذف الملفات قبل تاريخ معين.
    ℹ️ `/help` - عرض هذه القائمة للمساعدة.
    
    يمكنك إرسال أي ملف (📸 صورة، 🎥 فيديو، 📄 مستند...) وسيتم تخزينه تلقائيًا.
    """
    await message.reply(help_text, parse_mode="Markdown")

async def main():
    await storage.initialize_db()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
