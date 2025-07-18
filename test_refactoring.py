#!/usr/bin/env python3
"""
Тест рефакторинга - проверяем работу новой архитектуры
"""

import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_new_config():
    """Тестируем новую систему конфигурации"""
    print("\n🔧 Тестирование новой конфигурации...")
    
    try:
        from bot.core.config import config
        
        print(f"✅ Конфигурация загружена")
        print(f"📊 Статус: {config.get_status_info()}")
        print(f"🔍 Окружение: {config.environment.value}")
        print(f"🤖 Bot ID: {config.telegram.bot_id}")
        print(f"👤 Админы: {config.admin.user_ids}")
        
        # Проверяем обратную совместимость
        from bot.config import TELEGRAM_BOT_TOKEN, BOT_ID
        print(f"\n✅ Обратная совместимость:")
        print(f"   TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:10]}...")
        print(f"   BOT_ID: {BOT_ID}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка тестирования конфигурации: {e}", exc_info=True)
        return False


async def test_new_agent():
    """Тестируем новую архитектуру агента"""
    print("\n🤖 Тестирование нового агента...")
    
    try:
        from bot.core.agent import ArtemAgent
        from bot.core.interfaces import Message, User, MessageType, UserRole
        
        # Создаем агента
        agent = ArtemAgent()
        print("✅ Агент создан")
        
        # Проверяем статус
        status = await agent.get_agent_status()
        print(f"📊 Статус агента: {status}")
        
        # Создаем тестовое сообщение
        test_user = User(
            id=123456,
            username="test_user",
            first_name="Test",
            last_name="User",
            role=UserRole.USER
        )
        
        test_message = Message(
            id=1,
            user=test_user,
            chat_id=123456,
            text="Привет! Как дела?",
            type=MessageType.TEXT,
            timestamp=datetime.now()
        )
        
        print(f"\n📨 Тестовое сообщение: '{test_message.text}'")
        
        # Обрабатываем сообщение
        response = await agent.process_message(test_message)
        print(f"💬 Ответ: {response.text[:100]}...")
        print(f"📊 Метаданные: {response.metadata}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка тестирования агента: {e}", exc_info=True)
        return False


async def test_legacy_compatibility():
    """Тестируем обратную совместимость"""
    print("\n🔄 Тестирование обратной совместимости...")
    
    try:
        from bot.agent import myassistant
        
        # Создаем старый агент
        agent = myassistant()
        print("✅ Legacy агент создан")
        
        # Проверяем старый API
        intent = agent.detect_social_media_intent("Посмотри видео на YouTube")
        print(f"📊 Intent detection: {intent}")
        
        # Генерируем ответ через старый API
        response = await agent.generate_response(
            user_message="Привет, что умеешь?",
            user_id=123456,
            user_name="Test User",
            is_admin=False
        )
        print(f"💬 Legacy ответ: {response[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка тестирования совместимости: {e}", exc_info=True)
        return False


async def test_services():
    """Тестируем новые сервисы"""
    print("\n🔧 Тестирование сервисов...")
    
    try:
        # Тест Intent Detector
        from bot.services.intent_detector import IntentDetector, IntentType
        from bot.core.interfaces import Message, User, MessageType, UserRole
        
        detector = IntentDetector()
        print("✅ Intent Detector создан")
        
        test_messages = [
            "Привет!",
            "Помоги мне",
            "Спасибо большое",
            "Посмотри это видео https://youtube.com/watch?v=dQw4w9WgXcQ",
            "/help",
            "Что нового в Instagram?"
        ]
        
        for text in test_messages:
            user = User(id=1, username="test", first_name="Test", last_name="User")
            msg = Message(
                id=1, user=user, chat_id=1, text=text,
                type=MessageType.TEXT, timestamp=datetime.now()
            )
            
            intent = await detector.detect(msg)
            print(f"📝 '{text}' -> {intent['type']} (confidence: {intent['confidence']})")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка тестирования сервисов: {e}", exc_info=True)
        return False


async def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов рефакторинга...")
    print("=" * 50)
    
    results = []
    
    # Запускаем тесты
    results.append(("Конфигурация", await test_new_config()))
    results.append(("Новый агент", await test_new_agent()))
    results.append(("Обратная совместимость", await test_legacy_compatibility()))
    results.append(("Сервисы", await test_services()))
    
    # Результаты
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("⚠️ Некоторые тесты не прошли")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)