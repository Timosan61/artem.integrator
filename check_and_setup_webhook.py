#!/usr/bin/env python3
"""
Скрипт для проверки и настройки webhook с Business API поддержкой
"""

import sys
import os
import asyncio
import json
from typing import Dict, Any

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bot.webhook.services import WebhookService
    from bot.core.config import config
    from bot.telegram_bot import bot
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь что переменные окружения настроены правильно")
    sys.exit(1)

def print_colored(text: str, color: str = "white"):
    """Печать с цветами"""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m", 
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "white": "\033[0m"
    }
    reset = "\033[0m"
    print(f"{colors.get(color, colors['white'])}{text}{reset}")

async def check_current_webhook():
    """Проверяет текущую конфигуracию webhook"""
    print_colored("🔍 Проверка текущего webhook...", "blue")
    
    webhook_service = WebhookService()
    info = await webhook_service.get_webhook_info()
    
    if "error" in info:
        print_colored(f"❌ Ошибка получения информации о webhook: {info['error']}", "red")
        return False
    
    print_colored("📊 Текущая конфигурация webhook:", "blue")
    print(f"   🔗 URL: {info.get('webhook_url', 'Не установлен')}")
    print(f"   📨 Ожидающие обновления: {info.get('pending_updates', 0)}")
    print(f"   ❌ Последняя ошибка: {info.get('last_error', 'Нет')}")
    print(f"   🔄 Разрешенные события: {info.get('allowed_updates', 'Все')}")
    print(f"   🔢 Максимум соединений: {info.get('max_connections', 'По умолчанию')}")
    print()
    
    # Проверяем наличие Business API событий
    allowed_updates = info.get('allowed_updates', [])
    business_events = ['business_message', 'business_connection']
    
    has_business_support = False
    if isinstance(allowed_updates, list):
        has_business_support = all(event in allowed_updates for event in business_events)
    elif allowed_updates == "all" or not allowed_updates:
        has_business_support = True  # Если "all", то Business API поддерживается
    
    if has_business_support:
        print_colored("✅ Business API события поддерживаются", "green")
    else:
        print_colored("❌ Business API события НЕ настроены!", "red")
        missing_events = [event for event in business_events if event not in allowed_updates]
        print(f"   Отсутствуют события: {missing_events}")
    
    return has_business_support

async def setup_webhook_with_business():
    """Устанавливает webhook с поддержкой Business API"""
    print_colored("🔧 Настройка webhook с Business API поддержкой...", "blue")
    
    webhook_service = WebhookService()
    
    # Убеждаемся что Business события включены
    business_allowed_updates = [
        "message", 
        "callback_query",
        "business_message", 
        "business_connection",
        "edited_business_message",
        "deleted_business_messages"
    ]
    
    print(f"📋 Устанавливаем события: {business_allowed_updates}")
    
    result = await webhook_service.setup_webhook(
        allowed_updates=business_allowed_updates,
        drop_pending_updates=True  # Очищаем старые обновления
    )
    
    if result.get("success"):
        print_colored(f"✅ Webhook установлен: {result.get('webhook_url')}", "green")
        return True
    else:
        print_colored(f"❌ Ошибка установки webhook: {result.get('error')}", "red")
        return False

def test_business_message_structure():
    """Тестирует структуру Business сообщения"""
    print_colored("🧪 Тест структуры Business сообщения...", "blue")
    
    # Импортируем функцию тестирования
    try:
        from bot.webhook.services import TestService
        test_service = TestService()
        
        # Создаем тестовое Business сообщение
        business_update = test_service.create_test_business_update(
            chat_id=123456,
            text="Тестовое Business сообщение",
            business_connection_id="test_connection_123",
            user_id=987654321
        )
        
        print("📨 Структура Business сообщения:")
        print(json.dumps(business_update, indent=2, ensure_ascii=False))
        
        # Проверяем обязательные поля
        business_msg = business_update.get("business_message", {})
        required_fields = ["business_connection_id", "from", "chat", "text"]
        
        missing_fields = []
        for field in required_fields:
            if field not in business_msg:
                missing_fields.append(field)
        
        if not missing_fields:
            print_colored("✅ Структура Business сообщения корректна", "green")
        else:
            print_colored(f"❌ Отсутствуют поля: {missing_fields}", "red")
            
    except Exception as e:
        print_colored(f"❌ Ошибка тестирования: {e}", "red")

async def test_send_business_message():
    """Тестирует отправку Business сообщения"""
    print_colored("📤 Тест отправки Business сообщения...", "blue")
    
    try:
        from bot.webhook.handlers import send_business_message
        
        # Тестируем валидацию
        print("🔍 Тест валидации параметров...")
        
        # Тест с невалидными параметрами
        result = send_business_message(None, "test", "conn_123")
        if not result.get("success"):
            print_colored("✅ Валидация chat_id работает", "green")
        else:
            print_colored("❌ Валидация chat_id НЕ работает", "red")
        
        result = send_business_message(123, "", "conn_123")
        if not result.get("success"):
            print_colored("✅ Валидация text работает", "green")
        else:
            print_colored("❌ Валидация text НЕ работает", "red")
        
        result = send_business_message(123, "test", "")
        if not result.get("success"):
            print_colored("✅ Валидация business_connection_id работает", "green")
        else:
            print_colored("❌ Валидация business_connection_id НЕ работает", "red")
            
        print_colored("✅ Функция send_business_message() валидируется корректно", "green")
        
    except Exception as e:
        print_colored(f"❌ Ошибка тестирования send_business_message: {e}", "red")

async def check_business_connections():
    """Проверяет Business подключения"""
    print_colored("🔗 Проверка Business подключений...", "blue")
    
    try:
        from bot.webhook.handlers import get_business_connections_info
        
        connections_info = get_business_connections_info()
        
        if connections_info.get("success"):
            count = connections_info.get("connections_count", 0)
            print(f"📊 Найдено Business подключений: {count}")
            
            if count > 0:
                print("📋 Активные подключения:")
                for conn in connections_info.get("connections", []):
                    user_info = conn.get("user", {})
                    username = user_info.get("username", "Unknown")
                    is_enabled = conn.get("is_enabled", False)
                    status_emoji = "✅" if is_enabled else "❌"
                    print(f"   {status_emoji} @{username}")
            else:
                print_colored("⚠️ Нет активных Business подключений", "yellow")
                print("💡 Для настройки Business API:")
                print("   1. Убедитесь что у вас есть Telegram Premium")
                print("   2. Перейдите в Settings → Business → Chatbots")
                print("   3. Подключите вашего бота")
        else:
            error_details = connections_info.get("details", "Unknown error")
            print_colored(f"❌ Ошибка получения подключений: {error_details}", "red")
            
    except Exception as e:
        print_colored(f"❌ Ошибка проверки подключений: {e}", "red")

async def main():
    """Главная функция"""
    print_colored("🚀 Проверка и настройка Business API webhook", "blue")
    print("=" * 60)
    
    try:
        # Шаг 1: Проверяем текущий webhook
        business_supported = await check_current_webhook()
        
        # Шаг 2: Если Business API не поддерживается, настраиваем
        if not business_supported:
            print_colored("🔧 Business API не настроен, выполняем настройку...", "yellow")
            success = await setup_webhook_with_business()
            if not success:
                print_colored("❌ Не удалось настроить webhook", "red")
                return 1
        else:
            print_colored("✅ Business API уже настроен", "green")
        
        # Шаг 3: Тестируем структуры данных
        test_business_message_structure()
        print()
        
        # Шаг 4: Тестируем функцию отправки
        await test_send_business_message()
        print()
        
        # Шаг 5: Проверяем подключения
        await check_business_connections()
        print()
        
        print_colored("🎉 Диагностика завершена!", "green")
        print()
        print_colored("📋 Рекомендации:", "blue")
        print("1. Если нет Business подключений - настройте их в Telegram")
        print("2. Протестируйте отправку сообщения от клиента")
        print("3. Проверьте логи DigitalOcean с помощью ./get_digitalocean_logs.sh")
        print("4. Используйте команду /business_status в боте для диагностики")
        
        return 0
        
    except Exception as e:
        print_colored(f"❌ Критическая ошибка: {e}", "red")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)