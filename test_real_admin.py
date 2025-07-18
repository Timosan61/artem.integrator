#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обработки команды /start с реальными данными админа
"""

import asyncio
import json
from datetime import datetime
from bot.webhook.handlers import webhook_handler
from bot.auth import is_admin, get_user_mode

# Реальные данные админа из переменных окружения
real_admin_update = {
    "update_id": 123456789,
    "message": {
        "message_id": 1,
        "from": {
            "id": 229838448,  # Реальный Admin ID
            "username": "aaatema",  # Реальный admin username
            "first_name": "Admin",
            "last_name": "User"
        },
        "chat": {
            "id": 229838448,
            "type": "private"
        },
        "date": int(datetime.now().timestamp()),
        "text": "/start"
    }
}

async def test_real_admin():
    """Тестирует обработку команды /start с реальными данными админа"""
    print("🧪 Тестирование команды /start с реальным админом\n")
    
    # Проверяем права доступа
    admin_id = real_admin_update["message"]["from"]["id"]
    admin_username = real_admin_update["message"]["from"]["username"]
    
    print(f"👮 Проверка прав доступа:")
    print(f"  Admin {admin_id} (@{admin_username}): {is_admin(admin_id, admin_username)}")
    print(f"  User mode: {get_user_mode(admin_id, admin_username)}")
    print()
    
    # Создаем mock для bot.send_message чтобы избежать реальных API вызовов
    print("🔧 Создаем mock для Telegram API...")
    messages_sent = []
    
    # Сохраняем оригинальную функцию
    from bot import telegram_bot
    original_send_message = telegram_bot.bot.send_message
    
    # Создаем mock функцию
    def mock_send_message(chat_id, text, **kwargs):
        messages_sent.append({
            "chat_id": chat_id,
            "text": text,
            "kwargs": kwargs
        })
        print(f"  📤 Mock: отправка сообщения в чат {chat_id}")
        return {"message_id": 999, "chat": {"id": chat_id}}
    
    # Заменяем функцию на mock
    telegram_bot.bot.send_message = mock_send_message
    
    try:
        # Тестируем обработку команды /start
        print("\n📨 Обработка /start от админа:")
        result = await webhook_handler.handle_update(real_admin_update)
        print(f"  Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # Проверяем отправленные сообщения
        if messages_sent:
            print("\n📬 Отправленные сообщения:")
            for msg in messages_sent:
                print(f"  Chat ID: {msg['chat_id']}")
                print(f"  Parse mode: {msg['kwargs'].get('parse_mode', 'None')}")
                print(f"  Текст сообщения:")
                print("  " + "-" * 50)
                print(msg['text'])
                print("  " + "-" * 50)
        
        # Проверяем детали обработки
        if 'command' in result and result['command'] == 'start':
            print("\n  ✅ Команда /start обработана правильно как специальная команда")
        else:
            print("\n  ❌ Команда /start не была обработана как специальная команда")
            
    finally:
        # Восстанавливаем оригинальную функцию
        telegram_bot.bot.send_message = original_send_message
        print("\n✅ Mock удален, оригинальная функция восстановлена")

if __name__ == "__main__":
    asyncio.run(test_real_admin())