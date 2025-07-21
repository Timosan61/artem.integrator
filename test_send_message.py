#!/usr/bin/env python3
"""
Тест отправки сообщения через Telegram Bot API
"""

import os
import telebot

# Токен бота
BOT_TOKEN = "6658269281:AAETA0vTXiRCMPcL1y_DzEeU_Fc6DiqdpFk"
CHAT_ID = 229838448  # Ваш chat_id

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

try:
    # Отправляем тестовое сообщение
    result = bot.send_message(CHAT_ID, "🤖 Тест отправки сообщения!\nБот работает корректно.")
    print(f"✅ Сообщение отправлено успешно! Message ID: {result.message_id}")
except Exception as e:
    print(f"❌ Ошибка отправки: {e}")