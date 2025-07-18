#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обработки команды /start
"""

import asyncio
import json
from datetime import datetime
from bot.webhook.handlers import webhook_handler
from bot.auth import is_admin, format_admin_welcome_message, format_user_welcome_message

# Тестовые данные пользователей
test_admin_update = {
    "update_id": 123456789,
    "message": {
        "message_id": 1,
        "from": {
            "id": 390912977,  # Admin ID из переменных окружения
            "username": "Artem",
            "first_name": "Artem",
            "last_name": "Aleynikov"
        },
        "chat": {
            "id": 390912977,
            "type": "private"
        },
        "date": int(datetime.now().timestamp()),
        "text": "/start"
    }
}

test_user_update = {
    "update_id": 123456790,
    "message": {
        "message_id": 2,
        "from": {
            "id": 987654321,  # Обычный пользователь
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User"
        },
        "chat": {
            "id": 987654321,
            "type": "private"
        },
        "date": int(datetime.now().timestamp()),
        "text": "/start"
    }
}

async def test_start_command():
    """Тестирует обработку команды /start"""
    print("🧪 Тестирование команды /start\n")
    
    # Проверяем права доступа
    admin_id = test_admin_update["message"]["from"]["id"]
    admin_username = test_admin_update["message"]["from"]["username"]
    user_id = test_user_update["message"]["from"]["id"]
    user_username = test_user_update["message"]["from"]["username"]
    
    print(f"👮 Проверка прав доступа:")
    print(f"  Admin {admin_id} (@{admin_username}): {is_admin(admin_id, admin_username)}")
    print(f"  User {user_id} (@{user_username}): {is_admin(user_id, user_username)}")
    print()
    
    # Проверяем приветственные сообщения
    print("📋 Приветственные сообщения:")
    print("\n--- Admin Welcome ---")
    print(format_admin_welcome_message(admin_id, admin_username))
    print("\n--- User Welcome ---") 
    print(format_user_welcome_message("Test", user_id))
    print()
    
    # Тестируем обработку админской команды /start
    print("🔧 Обработка /start от админа:")
    try:
        result = await webhook_handler.handle_update(test_admin_update)
        print(f"  Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # Проверяем детали обработки
        if 'command' in result and result['command'] == 'start':
            print("  ✅ Команда /start обработана правильно")
        else:
            print("  ❌ Команда /start не была обработана как специальная команда")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
    print()
    
    # Тестируем обработку пользовательской команды /start
    print("👤 Обработка /start от обычного пользователя:")
    try:
        result = await webhook_handler.handle_update(test_user_update)
        print(f"  Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # Проверяем детали обработки
        if 'command' in result and result['command'] == 'start':
            print("  ✅ Команда /start обработана правильно")
        else:
            print("  ❌ Команда /start не была обработана как специальная команда")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_start_command())