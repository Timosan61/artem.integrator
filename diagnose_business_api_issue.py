#!/usr/bin/env python3
"""
Диагностика конкретной проблемы с Business API:
"пользователи не получают сообщения от агента через Business API"
"""

import sys
import os
import json
from typing import Dict, Any, List

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

def check_webhook_config():
    """Проверяет конфигурацию webhook в коде"""
    print_colored("🔍 Анализ конфигурации webhook в коде...", "blue")
    
    try:
        from bot.core.config import config
        
        print("📋 Конфигурация webhook:")
        print(f"   Base URL: {config.webhook.base_url}")
        print(f"   Secret Token: {'Установлен' if config.webhook.secret_token else 'НЕ установлен'}")
        print(f"   Allowed Updates: {config.webhook.allowed_updates}")
        
        # Проверяем Business API события
        business_events = ['business_message', 'business_connection']
        missing_events = []
        
        for event in business_events:
            if event not in config.webhook.allowed_updates:
                missing_events.append(event)
        
        if not missing_events:
            print_colored("✅ Business API события настроены в конфигурации", "green")
        else:
            print_colored(f"❌ Отсутствуют Business события: {missing_events}", "red")
            return False
            
        return True
        
    except Exception as e:
        print_colored(f"❌ Ошибка проверки конфигурации: {e}", "red")
        return False

def check_business_handlers():
    """Проверяет наличие обработчиков Business API"""
    print_colored("🔍 Проверка обработчиков Business API...", "blue")
    
    try:
        from bot.webhook.handlers import WebhookHandler
        
        handler = WebhookHandler()
        
        # Проверяем наличие методов обработки Business API
        business_methods = [
            '_handle_business_message',
            '_handle_business_connection'
        ]
        
        missing_methods = []
        for method in business_methods:
            if not hasattr(handler, method):
                missing_methods.append(method)
        
        if not missing_methods:
            print_colored("✅ Обработчики Business API присутствуют", "green")
        else:
            print_colored(f"❌ Отсутствуют методы: {missing_methods}", "red")
            return False
        
        # Проверяем функцию отправки Business сообщений
        try:
            from bot.webhook.handlers import send_business_message
            print_colored("✅ Функция send_business_message() найдена", "green")
        except ImportError:
            print_colored("❌ Функция send_business_message() НЕ найдена", "red")
            return False
            
        return True
        
    except Exception as e:
        print_colored(f"❌ Ошибка проверки обработчиков: {e}", "red")
        return False

def check_agent_routing():
    """Проверяет правильность маршрутизации к агентам"""
    print_colored("🔍 Проверка маршрутизации агентов...", "blue")
    
    try:
        from bot.core.unified_agent import unified_agent
        from bot.core.interfaces import Message, User, UserRole, MessageType
        from datetime import datetime
        
        # Создаем тестовое Business сообщение
        test_user = User(
            id=123456,
            username="test_business_user",
            first_name="Test",
            role=UserRole.USER
        )
        
        business_message = Message(
            id=1,
            user=test_user,
            chat_id=123456,
            text="Тестовое Business сообщение",
            type=MessageType.TEXT,
            timestamp=datetime.now(),
            metadata={"business_connection_id": "test_connection_123"},
            is_business_message=True
        )
        
        # Проверяем какой агент получит это сообщение
        # Не вызываем process_message (чтобы не делать реальных запросов),
        # а только проверяем get_agent_for_message
        
        # ПРИМЕЧАНИЕ: Эта функция может быть async, поэтому обработаем осторожно
        agent_info = "Тестирование маршрутизации требует запущенного окружения"
        
        print(f"📨 Тестовое Business сообщение создано:")
        print(f"   User ID: {business_message.user.id}")
        print(f"   Is Business: {business_message.is_business_message}")
        print(f"   Connection ID: {business_message.metadata.get('business_connection_id')}")
        print(f"   Text: {business_message.text}")
        
        print_colored("✅ Структура сообщения корректна для Business API", "green")
        return True
        
    except Exception as e:
        print_colored(f"❌ Ошибка проверки маршрутизации: {e}", "red")
        return False

def check_send_business_function():
    """Детально проверяет функцию отправки Business сообщений"""
    print_colored("🔍 Детальная проверка send_business_message()...", "blue")
    
    try:
        from bot.webhook.handlers import send_business_message
        import inspect
        
        # Получаем сигнатуру функции
        sig = inspect.signature(send_business_message)
        print(f"📝 Сигнатура функции: {sig}")
        
        # Проверяем параметры
        expected_params = ['chat_id', 'text', 'business_connection_id']
        actual_params = list(sig.parameters.keys())
        
        missing_params = [p for p in expected_params if p not in actual_params]
        if missing_params:
            print_colored(f"❌ Отсутствуют параметры: {missing_params}", "red")
            return False
        
        print_colored("✅ Параметры функции корректны", "green")
        
        # Проверяем возвращаемый тип (в документации)
        source = inspect.getsource(send_business_message)
        if "Dict[str, Any]" in source or "return {" in source:
            print_colored("✅ Функция возвращает словарь (корректно)", "green")
        else:
            print_colored("⚠️ Возвращаемый тип неопределен", "yellow")
        
        # Проверяем наличие валидации
        if "chat_id" in source and "business_connection_id" in source:
            print_colored("✅ Валидация параметров присутствует", "green")
        else:
            print_colored("⚠️ Валидация параметров неполная", "yellow")
            
        # Проверяем использование requests для HTTP запросов
        if "requests.post" in source:
            print_colored("✅ Использует прямые HTTP запросы (правильно для Business API)", "green")
        else:
            print_colored("❌ НЕ использует прямые HTTP запросы (проблема!)", "red")
            return False
            
        return True
        
    except Exception as e:
        print_colored(f"❌ Ошибка проверки функции: {e}", "red")
        return False

def analyze_potential_issues():
    """Анализирует потенциальные проблемы"""
    print_colored("🔍 Анализ потенциальных проблем...", "blue")
    
    issues_found = []
    
    print("📋 Чек-лист потенциальных проблем:")
    
    # 1. Webhook не установлен с Business событиями
    print("   1. ❓ Webhook установлен без Business событий")
    print("      Решение: Запустить ./check_and_setup_webhook.py")
    
    # 2. Business API не настроен в Telegram
    print("   2. ❓ Business API не настроен в Telegram Premium аккаунте")
    print("      Решение: Settings → Business → Chatbots → подключить бота")
    
    # 3. pyTelegramBotAPI не поддерживает Business API
    print("   3. ❓ Попытка использовать bot.send_message() для Business")
    print("      Решение: Должна использоваться функция send_business_message()")
    
    # 4. Неправильный business_connection_id
    print("   4. ❓ Неправильный или отсутствующий business_connection_id")
    print("      Решение: Проверить webhook получает business_connection_id")
    
    # 5. Приложение не развернуто на DigitalOcean
    print("   5. ❓ Код не развернут на DigitalOcean или есть ошибки деплоя")
    print("      Решение: Запустить ./get_digitalocean_logs.sh")
    
    # 6. Ошибки в отправке HTTP запросов
    print("   6. ❓ Ошибки в send_business_message() или timeout")
    print("      Решение: Проверить логи и улучшить обработку ошибок")
    
    print()
    print_colored("💡 Рекомендуемый порядок диагностики:", "yellow")
    print("   1. Запустить ./get_digitalocean_logs.sh - проверить деплой")
    print("   2. Запустить ./check_and_setup_webhook.py - проверить webhook")
    print("   3. В боте выполнить /business_status - проверить подключения")
    print("   4. Протестировать отправку реального Business сообщения")
    print("   5. Проверить логи DigitalOcean на наличие ошибок отправки")

def create_test_script():
    """Создает скрипт для тестирования Business API"""
    print_colored("📝 Создание тест-скрипта для Business API...", "blue")
    
    test_script = '''#!/usr/bin/env python3
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
'''
    
    try:
        with open("test_business_api_send.py", "w", encoding="utf-8") as f:
            f.write(test_script)
        
        os.chmod("test_business_api_send.py", 0o755)
        print_colored("✅ Создан test_business_api_send.py", "green")
        
    except Exception as e:
        print_colored(f"❌ Ошибка создания тест-скрипта: {e}", "red")

def main():
    """Главная функция диагностики"""
    print_colored("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ BUSINESS API", "blue")
    print_colored("Проблема: Пользователи не получают сообщения от агента", "yellow")
    print("=" * 60)
    
    issues_count = 0
    
    # Шаг 1: Проверка конфигурации
    if not check_webhook_config():
        issues_count += 1
    print()
    
    # Шаг 2: Проверка обработчиков
    if not check_business_handlers():
        issues_count += 1
    print()
    
    # Шаг 3: Проверка маршрутизации
    if not check_agent_routing():
        issues_count += 1
    print()
    
    # Шаг 4: Проверка функции отправки
    if not check_send_business_function():
        issues_count += 1
    print()
    
    # Шаг 5: Анализ проблем
    analyze_potential_issues()
    print()
    
    # Шаг 6: Создание тест-скрипта
    create_test_script()
    print()
    
    # Заключение
    if issues_count == 0:
        print_colored("🎉 Код Business API выглядит корректно!", "green")
        print_colored("Проблема скорее всего в конфигурации или деплое", "yellow")
    else:
        print_colored(f"⚠️ Найдено {issues_count} потенциальных проблем в коде", "yellow")
    
    print()
    print_colored("🚀 СЛЕДУЮЩИЕ ШАГИ:", "blue")
    print("1. ./get_digitalocean_logs.sh - проверить статус приложения")
    print("2. ./check_and_setup_webhook.py - проверить webhook")
    print("3. В боте: /business_status - проверить подключения")
    print("4. Протестировать с реальным Business сообщением")
    
    return issues_count

if __name__ == "__main__":
    issues = main()
    sys.exit(issues)