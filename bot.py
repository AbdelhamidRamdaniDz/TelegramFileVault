import os
import logging
import sys
if sys.platform.startswith("win"):
    os.system("chcp 65001")
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from database import AsyncMediaStorage
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("🚨 خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
storage = AsyncMediaStorage("media.db")

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

dp.middleware.setup(LoggingMiddleware(logger))

def _format_size(size: int) -> str:
    """تحويل الحجم إلى صيغة سهلة القراءة"""
    units = ['B', 'KB', 'MB', 'GB']
    idx = 0
    while size >= 1024 and idx < 3:
        size /= 1024
        idx += 1
    return f"{size:.2f}{units[idx]}"


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


@dp.message_handler(content_types=[
    types.ContentType.PHOTO,
    types.ContentType.VIDEO,
    types.ContentType.DOCUMENT,
    types.ContentType.AUDIO,
    types.ContentType.ANIMATION
])
async def handle_media(message: Message):
    try:
        print(f"📩 استقبال ملف من {message.from_user.id} - النوع: {message.content_type}")
        
        content_type = message.content_type
        file_id = None
        file_meta = {}

        if content_type == types.ContentType.DOCUMENT:
            file_id = message.document.file_id
            file_meta = {"file_name": message.document.file_name, "mime_type": message.document.mime_type}

        if file_id:
            print(f"✅ محاولة حفظ الملف في قاعدة البيانات: {file_id}")
            await storage.asave_file(
                file_id=file_id,
                file_type=content_type,
                user_id=message.from_user.id,
                meta_data=file_meta
            )
            print("✅ تم الحفظ بنجاح!")
            await message.reply("📁 تم حفظ الملف بنجاح!")
        else:
            print("⚠️ لم يتم العثور على ملف!")
            await message.reply("⚠️ تعذر استخراج معلومات الملف")
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ الملف: {e}")
        logger.error(f"خطأ في معالجة الملف: {str(e)}", exc_info=True)
        await message.reply("❌ حدث خطأ فني أثناء معالجة الملف، يرجى المحاولة لاحقًا")


@dp.message_handler(commands=['play', 'latest'])
async def send_latest_file(message: Message):
    try:
        media = await storage.aget_latest_file()

        if not media:
            await message.reply("📭 لا يوجد ملفات مخزنة بعد\n"
                                "يمكنك إرسال أي ملف وسأحفظه لك!")
            return

        file_id, file_type = media
        send_method = _get_send_method(file_type)

        try:
            await send_method(message.chat.id, file_id)
            await message.reply("✅ تم إرسال آخر ملف مخزن")
        except Exception as e:
            logger.error(f"خطأ أثناء الإرسال: {str(e)}", exc_info=True)
            await message.reply("⏳ حدثت مشكلة في الخادم، يرجى المحاولة مرة أخرى بعد قليل")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
        await message.reply("❌ حدث خطأ غير متوقع أثناء الاسترجاع")


async def main():
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
0
