#!/usr/bin/env python3
"""
Тест команды /mcp apps через webhook
"""
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_mcp_apps():
    """Тест команды /mcp apps"""
    
    webhook_url = "http://localhost:8000/webhook"
    
    # Создаем сообщение от админа
    update = {
        "update_id": 574085201,
        "message": {
            "message_id": 672,
            "from": {
                "id": 229838448,
                "is_bot": False,
                "first_name": "Artem",
                "last_name": "Aleynikov", 
                "username": "aaatema",
                "language_code": "ru",
                "is_premium": True
            },
            "chat": {
                "id": 229838448,
                "first_name": "Artem",
                "last_name": "Aleynikov",
                "username": "aaatema",
                "type": "private"
            },
            "date": 1753244300,
            "text": "/mcp apps",
            "entities": [{"offset": 0, "length": 4, "type": "bot_command"}]
        }
    }
    
    print("📨 Отправляем команду /mcp apps от админа")
    print("-" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                webhook_url,
                json=update,
                headers={
                    "Content-Type": "application/json",
                    "X-Telegram-Bot-Api-Secret-Token": os.getenv("WEBHOOK_SECRET_TOKEN", "79c08d0ee7c19026653b6aa365b731cc2c23699f3a52aec8fc89be28990af77e")
                }
            ) as response:
                print(f"📊 Статус: {response.status}")
                result = await response.json()
                print(f"📝 Результат: {result}")
                
                # Ждем немного чтобы увидеть логи
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_apps())