#!/usr/bin/env python3
"""
Простой тест для Business API отправки
"""

import requests
import json
import os

def test_business_api_send():
    """Тестирует отправку через Business API"""
    
    # ВАЖНО: Это только тест структуры запроса!
    # Для реального теста нужны настоящие токен и connection_id
    
    bot_token = "YOUR_BOT_TOKEN"  # Замените на настоящий
    business_connection_id = "YOUR_CONNECTION_ID"  # Замените на настоящий
    chat_id = 123456  # Замените на настоящий
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": "Тест Business API отправки",
        "business_connection_id": business_connection_id
    }
    
    print("📤 Тестовый запрос к Telegram Business API:")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    # НЕ отправляем реальный запрос в тесте
    print("⚠️ Реальный запрос НЕ отправляется (это только структура)")
    print("Для реального теста замените токены и раскомментируйте код ниже:")
    print()
    print("# response = requests.post(url, json=data)")
    print("# result = response.json()")
    print("# print(f'Результат: {result}')")

if __name__ == "__main__":
    test_business_api_send()
