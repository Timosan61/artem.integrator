#!/usr/bin/env python3
"""
Тестовый скрипт для отправки реальной команды /agent в бот
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = 229838448  # ID пользователя aaatema

def send_message(text):
    """Отправляет сообщение в чат"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    response = requests.post(url, json=data)
    if response.ok:
        print(f"✅ Сообщение отправлено: {text}")
        return response.json()
    else:
        print(f"❌ Ошибка отправки: {response.text}")
        return None

def main():
    print("=== Тестирование реальной команды /agent ===")
    
    # Отправляем команду /agent
    print("\n📤 Отправляем команду /agent...")
    result = send_message("/agent")
    
    if result:
        message_id = result.get('result', {}).get('message_id')
        print(f"📩 Сообщение отправлено, ID: {message_id}")
    
    print("\n=== Тест завершен ===")
    print("Проверьте Telegram на наличие ответа от бота")

if __name__ == "__main__":
    main()