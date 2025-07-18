#!/usr/bin/env python3
"""
Тестовый скрипт для проверки конфигурации админов
"""

import os
from bot.core.config import config
from bot.auth import is_admin, get_user_mode, get_permission_info

def test_admin_config():
    """Тестирует конфигурацию админов"""
    print("🔍 Проверка конфигурации админов\n")
    
    # Проверяем переменные окружения
    print("📋 Переменные окружения:")
    print(f"  ADMIN_USER_ID: {os.getenv('ADMIN_USER_ID', 'NOT SET')}")
    print(f"  ADMIN_USERNAMES: {os.getenv('ADMIN_USERNAMES', 'NOT SET')}")
    print()
    
    # Проверяем загруженную конфигурацию
    print("🔧 Загруженная конфигурация:")
    print(f"  Admin User IDs: {config.admin.user_ids}")
    print(f"  Admin Usernames: {config.admin.usernames}")
    print()
    
    # Проверяем информацию о правах доступа
    print("🔐 Информация о правах доступа:")
    perm_info = get_permission_info()
    for key, value in perm_info.items():
        print(f"  {key}: {value}")
    print()
    
    # Тестируем конкретных пользователей
    test_users = [
        (390912977, "Artem", "Должен быть админом"),
        (390912977, None, "Проверка только по ID"),
        (None, "Artem", "Проверка только по username"),
        (987654321, "testuser", "Обычный пользователь")
    ]
    
    print("👤 Проверка конкретных пользователей:")
    for user_id, username, description in test_users:
        is_admin_result = is_admin(user_id, username)
        user_mode = get_user_mode(user_id, username)
        print(f"  {description}:")
        print(f"    ID: {user_id}, Username: {username}")
        print(f"    is_admin: {is_admin_result}")
        print(f"    user_mode: {user_mode}")
        
        # Детальная проверка через config
        if user_id:
            print(f"    ID в admin.user_ids: {user_id in config.admin.user_ids}")
        if username:
            print(f"    Username в admin.usernames: {username in config.admin.usernames}")
        print()

if __name__ == "__main__":
    test_admin_config()