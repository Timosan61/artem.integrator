#!/usr/bin/env python3
"""
Тест команды /mcp apps через Telegram
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = "http://localhost:8000/webhook"  # Локальный сервер

async def send_telegram_message():
    """Отправить команду /mcp apps боту"""
    
    # Создаем тестовое сообщение от Telegram
    update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
                "language_code": "ru"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1234567890,
            "text": "/mcp apps"
        }
    }
    
    print("📨 Отправляем команду: /mcp apps")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URL,
                json=update,
                headers={
                    "Content-Type": "application/json",
                    "X-Telegram-Bot-Api-Secret-Token": os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
                }
            ) as response:
                print(f"📊 Статус: {response.status}")
                text = await response.text()
                print(f"📝 Ответ: {text}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\n💡 Убедитесь, что бот запущен локально!")

if __name__ == "__main__":
    asyncio.run(send_telegram_message())