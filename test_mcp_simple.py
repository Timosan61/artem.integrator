#!/usr/bin/env python3
"""
Простой тест MCP через webhook
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_mcp_webhook():
    """Простой тест MCP команд через webhook"""
    
    print("\n🔍 Простой тест MCP через webhook")
    print("=" * 60)
    
    webhook_url = "http://localhost:8000/webhook"
    
    # Проверяем доступность
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"✅ Webhook доступен: {status}")
                else:
                    print("❌ Webhook не доступен")
                    return
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    # Тестовая команда
    update = {
        "update_id": 10000,
        "message": {
            "message_id": 1000,
            "from": {
                "id": 229838448,
                "is_bot": False,
                "first_name": "Admin",
                "username": "admin"
            },
            "chat": {
                "id": 229838448,
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": "/mcp status"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": "test-secret"
    }
    
    print(f"\n📮 Отправка команды: /mcp status")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=update, headers=headers) as resp:
                print(f"📬 Статус: {resp.status}")
                
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Ответ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ Ошибка: {await resp.text()}")
                    
    except Exception as e:
        print(f"❌ Исключение: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mcp_webhook())