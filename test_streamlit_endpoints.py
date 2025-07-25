#!/usr/bin/env python3
"""
Тестовый скрипт для проверки endpoints Streamlit админ-панели
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://artemintegrator-nahdj.ondigitalocean.app"
ADMIN_TOKEN = "secure-admin-token"

def test_current_prompt():
    """Тестирует endpoint для получения информации о текущем промпте"""
    print("🔍 Тестируем /debug/current-prompt...")
    
    try:
        url = f"{BASE_URL}/debug/current-prompt"
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Успешно получена информация о промпте:")
            print(f"  - Файл существует: {data.get('exists', False)}")
            print(f"  - Последнее обновление: {data.get('last_updated', 'Неизвестно')}")
            print(f"  - Длина системной инструкции: {data.get('system_instruction_length', 0)}")
            print(f"  - Длина приветственного сообщения: {data.get('welcome_message_length', 0)}")
            
            if "error" in data:
                print(f"  ⚠️ Ошибка: {data['error']}")
        else:
            print(f"❌ Endpoint не найден (наши изменения еще не на сервере)")
            print("🔄 Тестируем существующий /debug/last-updates...")
            
            # Пробуем существующий endpoint
            url_existing = f"{BASE_URL}/debug/last-updates"
            response_existing = requests.get(url_existing, timeout=10)
            print(f"  Статус существующего endpoint: {response_existing.status_code}")
            if response_existing.status_code == 200:
                data_existing = response_existing.json()
                print(f"  ✅ Существующий endpoint работает: {data_existing.get('total_updates', 0)} updates")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

def test_reload_prompt():
    """Тестирует endpoint для перезагрузки промпта с аутентификацией"""
    print("\n🔄 Тестируем /admin/reload-prompt...")
    
    try:
        url = f"{BASE_URL}/admin/reload-prompt"
        headers = {
            "X-Admin-Token": ADMIN_TOKEN,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Успешная перезагрузка промпта:")
            print(f"  - Изменения: {data.get('changed', False)}")
            if data.get('changed'):
                print(f"  - Старое обновление: {data.get('old_updated', 'Неизвестно')}")
                print(f"  - Новое обновление: {data.get('new_updated', 'Неизвестно')}")
            else:
                print("  - Промпт перезагружен без изменений")
        elif response.status_code == 403:
            print("❌ Ошибка аутентификации (403) - неверный админский токен")
        elif response.status_code == 404:
            print("❌ Админские endpoints отключены (404)")
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"Детали: {error_data.get('detail', 'Неизвестная ошибка')}")
            except:
                print(f"Ответ: {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ Исключение: {e}")

def test_debug_config():
    """Тестирует endpoint для получения конфигурации"""
    print("\n⚙️ Тестируем /debug/config...")
    
    try:
        url = f"{BASE_URL}/debug/config"
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Конфигурация получена:")
            
            # Проверяем важные настройки
            admin_info = data.get('admin', {})
            print(f"  - Админы настроены: {admin_info.get('user_ids_count', 0)} ID + {admin_info.get('usernames_count', 0)} usernames")
            
            env_vars = data.get('environment_variables', {})
            print(f"  - ADMIN_TOKEN настроен: {env_vars.get('ADMIN_TOKEN_configured', False)}")
            print(f"  - VOICE_ENABLED: {env_vars.get('VOICE_ENABLED', 'не установлен')}")
            print(f"  - BASE_URL: {env_vars.get('BASE_URL', 'не установлен')}")
            
        else:
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"Ответ: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

def main():
    print("🧪 Тестирование Streamlit админ-панели endpoints")
    print(f"🌐 Сервер: {BASE_URL}")
    print(f"🔑 Токен: {ADMIN_TOKEN}")
    print(f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Тестируем endpoints
    test_current_prompt()
    test_reload_prompt()
    test_debug_config()
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    main()