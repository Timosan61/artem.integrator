#!/usr/bin/env python3
"""
Добавление пользователя в админы
"""
from bot.core.auto_admin import auto_admin_manager

# Добавляем пользователя
user_id = 229838448
username = "aaatema"
first_name = "Artem"

success = auto_admin_manager.add_admin(user_id, username, first_name)

if success:
    print(f"✅ Пользователь {username} ({user_id}) добавлен в админы")
else:
    print(f"❌ Не удалось добавить пользователя в админы")

# Проверяем
admins = auto_admin_manager.get_all_admins()
print(f"\n📋 Список админов: {admins}")