import os
import logging
import sys
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from database import AsyncMediaStorage
from dotenv import load_dotenv

# دعم اللغة العربية في Windows
if sys.platform.startswith("win"):
    os.system("chcp 65001")
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# تحميل متغيرات البيئة
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("🚨 خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")

# إعداد البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
storage = AsyncMediaStorage("media.db")

# تسجيل الأخطاء
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

dp.middleware.setup(LoggingMiddleware(logger))

# --- دوال مساعدة ---
def _get_send_method(file_type: str):
    """إرجاع الدالة المناسبة لإرسال الملفات"""
    methods = {
        types.ContentType.PHOTO: bot.send_photo,
        types.ContentType.VIDEO: bot.send_video,
        types.ContentType.DOCUMENT: bot.send_document,
        types.ContentType.AUDIO: bot.send_audio,
        types.ContentType.ANIMATION: bot.send_animation
    }
    return methods.get(file_type, bot.send_document)


# --- استقبال الملفات وحفظها ---
@dp.message_handler(content_types=[
    types.ContentType.PHOTO, types.ContentType.VIDEO, types.ContentType.DOCUMENT,
    types.ContentType.AUDIO, types.ContentType.ANIMATION
])
async def handle_media(message: Message):
    try:
        content_type = message.content_type
        file_id = None
        file_meta = {}

        if content_type == types.ContentType.DOCUMENT:
            file_id = message.document.file_id
            file_meta = {"file_name": message.document.file_name, "mime_type": message.document.mime_type}

        if file_id:
            await storage.asave_file(file_id=file_id, file_type=content_type, user_id=message.from_user.id, meta_data=file_meta)
            await message.reply("✅ **تم حفظ الملف بنجاح!**")
        else:
            await message.reply("⚠️ **لم يتم العثور على ملف!**")
    except Exception as e:
        logger.error(f"خطأ في معالجة الملف: {str(e)}", exc_info=True)
        await message.reply("❌ **حدث خطأ أثناء حفظ الملف، يرجى المحاولة لاحقًا**")


# --- استرجاع آخر ملف مخزن ---
@dp.message_handler(commands=['play', 'latest'])
async def send_latest_file(message: Message):
    try:
        media = await storage.aget_latest_file()
        if not media:
            await message.reply("📭 **لا يوجد ملفات مخزنة بعد!**\n📝 **أرسل ملفًا وسأحفظه لك**")
            return

        file_id, file_type = media
        send_method = _get_send_method(file_type)
        await send_method(message.chat.id, file_id)
        await message.reply("✅ **تم إرسال آخر ملف مخزن!**")
    except Exception as e:
        logger.error(f"خطأ أثناء الإرسال: {str(e)}", exc_info=True)
        await message.reply("⏳ **حدثت مشكلة، يرجى المحاولة مرة أخرى لاحقًا**")


# --- البحث عن الملفات ---
@dp.message_handler(commands=['search'])
async def search_files(message: Message):
    query = message.get_args().strip()
    if not query:
        await message.reply("🔎 **يرجى إدخال الكلمة المراد البحث عنها**\nمثال: `/search pdf`")
        return

    results = await storage.asearch_files(query)
    if not results:
        await message.reply(f"❌ **لم يتم العثور على ملفات تحتوي على: `{query}`**")
        return

    response = "🔍 **نتائج البحث:**\n\n"
    for file_id, file_type, meta_data in results:
        response += f"📂 `{meta_data}` - {file_type}\n"

    await message.reply(response)


# --- حذف الملفات القديمة ---
@dp.message_handler(commands=['clear_old'])
async def clear_old_files(message: Message):
    args = message.get_args().strip()
    if not args.isdigit():
        await message.reply("⚠️ **يرجى إدخال عدد الأيام بشكل صحيح**\nمثال: `/clear_old 30`")
        return

    days = int(args)
    await storage.adelete_old_files(days)
    await message.reply(f"✅ **تم حذف الملفات الأقدم من {days} يومًا بنجاح!**")


# --- تشغيل البوت ---
async def main():
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
