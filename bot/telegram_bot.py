"""
Telegram Bot instance
"""

import telebot
from .core.config import config

# Создаем экземпляр бота
bot = telebot.TeleBot(config.telegram.token)

# Экспортируем для обратной совместимости
__all__ = ['bot']