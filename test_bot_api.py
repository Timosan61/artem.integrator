#!/usr/bin/env python3
"""
Тест API бота после рефакторинга
"""

import requests
import json

# URL webhook
WEBHOOK_URL = "https://web-production-84d8.up.railway.app/webhook"

# Тестовые данные
test_update = {
    "update_id": 123456789,
    "message": {
        "message_id": 1,
        "from": {
            "id": 123456,
            "is_bot": False,
            "first_name": "Test",
            "username": "test_user"
        },
        "chat": {
            "id": 123456,
            "first_name": "Test",
            "username": "test_user",
            "type": "private"
        },
        "date": 1643723793,
        "text": "Привет! Как дела?"
    }
}

print("🧪 Тестирование API бота после рефакторинга...")
print("=" * 50)

try:
    # Отправляем запрос
    response = requests.post(WEBHOOK_URL, json=test_update)
    
    print(f"📊 Статус код: {response.status_code}")
    print(f"📝 Ответ: {response.text}")
    
    if response.status_code == 200:
        print("✅ Тест пройден успешно!")
    else:
        print("❌ Тест не пройден")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("=" * 50)