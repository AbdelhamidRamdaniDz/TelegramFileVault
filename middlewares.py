from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message
import logging

class LoggingMiddleware(BaseMiddleware):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    async def on_process_message(self, message: Message, data: dict):
        """تسجيل كل رسالة يتم استقبالها"""
        self.logger.info(f"📩 رسالة جديدة من {message.from_user.id} - النوع: {message.content_type}")

