#!/usr/bin/env python3
"""
Тест Voice Service для проверки работоспособности
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_service_import():
    """Тест импорта Voice Service"""
    try:
        from voice import VoiceService
        print("✅ Voice Service импортирован успешно")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта Voice Service: {e}")
        return False

def test_voice_service_init():
    """Тест инициализации Voice Service"""
    try:
        from voice import VoiceService
        
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if not telegram_token:
            print("❌ TELEGRAM_BOT_TOKEN не найден")
            return False
        
        if not openai_key:
            print("❌ OPENAI_API_KEY не найден")
            return False
        
        # Инициализируем сервис
        voice_service = VoiceService(telegram_token, openai_key)
        print("✅ Voice Service инициализирован успешно")
        
        # Получаем информацию о сервисе
        service_info = voice_service.get_service_info()
        print(f"📋 Информация о сервисе: {service_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации Voice Service: {e}")
        return False

async def test_voice_service_connection():
    """Тест подключения к внешним API"""
    try:
        from voice import VoiceService
        
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if not telegram_token or not openai_key:
            print("⚠️ Пропущен тест подключения: отсутствуют API ключи")
            return False
        
        voice_service = VoiceService(telegram_token, openai_key)
        
        # Тестируем сервис
        test_results = await voice_service.test_service()
        print(f"🔍 Результаты тестирования: {test_results}")
        
        if test_results.get('service_ready'):
            print("✅ Voice Service готов к работе")
            return True
        else:
            print("⚠️ Voice Service не полностью готов")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования подключения: {e}")
        return False

def test_voice_components():
    """Тест отдельных компонентов"""
    try:
        # Тест импорта компонентов
        from voice.config import TEMP_AUDIO_DIR, MAX_AUDIO_SIZE_MB
        print(f"✅ Конфигурация загружена: {TEMP_AUDIO_DIR}, макс. размер: {MAX_AUDIO_SIZE_MB}MB")
        
        from voice.telegram_audio import TelegramAudioDownloader
        print("✅ TelegramAudioDownloader импортирован")
        
        from voice.whisper_client import WhisperTranscriber
        print("✅ WhisperTranscriber импортирован")
        
        # Тест создания временной папки
        from voice.config import ensure_temp_dir
        temp_dir = ensure_temp_dir()
        print(f"✅ Временная папка создана: {temp_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования компонентов: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🔍 Тестирование Voice Service...")
    print("=" * 50)
    
    tests = [
        ("Импорт Voice Service", test_voice_service_import),
        ("Тестирование компонентов", test_voice_components),
        ("Инициализация Voice Service", test_voice_service_init),
    ]
    
    # Синхронные тесты
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - ПРОЙДЕН")
            else:
                print(f"❌ {test_name} - НЕ ПРОЙДЕН")
        except Exception as e:
            print(f"❌ {test_name} - ОШИБКА: {e}")
    
    # Асинхронный тест
    print(f"\n🧪 Тестирование подключения...")
    try:
        if await test_voice_service_connection():
            passed += 1
            print(f"✅ Тестирование подключения - ПРОЙДЕН")
        else:
            print(f"❌ Тестирование подключения - НЕ ПРОЙДЕН")
        total += 1
    except Exception as e:
        print(f"❌ Тестирование подключения - ОШИБКА: {e}")
        total += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Voice Service готов к работе")
        return True
    else:
        print("⚠️ Некоторые тесты не пройдены. Проверьте конфигурацию")
        return False

if __name__ == "__main__":
    asyncio.run(main())