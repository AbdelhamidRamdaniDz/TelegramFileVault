from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message
import logging


class LoggingMiddleware(BaseMiddleware):
    def __init__(self, logger: logging.Logger):
        super().__init__()
        self.logger = logger

    async def on_process_message(self, message: Message, data: dict):
        """تسجيل كل رسالة يتم استقبالها"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "غير معروف"
            content_type = message.content_type
            text = message.text or message.caption or "📎 [محتوى غير نصي]"

            self.logger.info(f"📩 رسالة جديدة من {user_id} (@{username}) - النوع: {content_type} - المحتوى: {text}")

        except Exception as e:
            self.logger.error(f"⚠️ خطأ أثناء تسجيل الرسالة: {e}")
