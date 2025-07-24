#!/usr/bin/env python3
"""
Тестирование обработки голосовых сообщений через Intelligent Agent
"""
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импортируем необходимые модули
from bot.webhook.handlers import webhook_handler
from bot.services.intelligent_agent_service import intelligent_agent_service

async def test_voice_message():
    """Тестирует обработку голосового сообщения"""
    
    # Создаем тестовое голосовое сообщение от админа
    test_update = {
        "update_id": 888888,
        "message": {
            "message_id": 8888,
            "from": {
                "id": 229838448,  # Admin ID
                "is_bot": False,
                "first_name": "Artem",
                "username": "aaatema",
                "language_code": "ru"
            },
            "chat": {
                "id": 229838448,
                "first_name": "Artem",
                "username": "aaatema",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "voice": {
                "duration": 3,
                "mime_type": "audio/ogg",
                "file_id": "TEST_VOICE_FILE_ID",
                "file_unique_id": "TEST_UNIQUE_ID",
                "file_size": 10000
            }
        }
    }
    
    logger.info("=" * 50)
    logger.info("ТЕСТ ГОЛОСОВОГО СООБЩЕНИЯ")
    logger.info("=" * 50)
    
    # Мокаем voice_service для теста
    from unittest.mock import AsyncMock, Mock
    from bot.webhook import handlers
    
    # Создаем мок voice_service
    mock_voice_service = Mock()
    mock_voice_service.process_voice = AsyncMock(return_value={
        "success": True,
        "text": "Какие у тебя есть инструменты?",
        "language": "ru",
        "duration": 3
    })
    
    # Временно заменяем voice_service
    original_voice_service = handlers.voice_service
    handlers.voice_service = mock_voice_service
    
    try:
        # Обрабатываем голосовое сообщение
        logger.info("📤 Отправляем голосовое сообщение...")
        result = await webhook_handler.handle_update(test_update)
        
        logger.info(f"\n📥 Результат: {result}")
        
        # Проверяем, что voice_service был вызван
        if mock_voice_service.process_voice.called:
            logger.info("✅ Voice service вызван для транскрипции")
            call_args = mock_voice_service.process_voice.call_args
            logger.info(f"   Аргументы: {call_args}")
        else:
            logger.error("❌ Voice service НЕ был вызван")
            
    finally:
        # Восстанавливаем оригинальный voice_service
        handlers.voice_service = original_voice_service


async def test_text_message_comparison():
    """Тестирует обработку текстового сообщения для сравнения"""
    
    # Создаем текстовое сообщение с тем же текстом
    test_update = {
        "update_id": 777777,
        "message": {
            "message_id": 7777,
            "from": {
                "id": 229838448,  # Admin ID
                "is_bot": False,
                "first_name": "Artem",
                "username": "aaatema",
                "language_code": "ru"
            },
            "chat": {
                "id": 229838448,
                "first_name": "Artem",
                "username": "aaatema",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": "Какие у тебя есть инструменты?"
        }
    }
    
    logger.info("\n" + "=" * 50)
    logger.info("ТЕСТ ТЕКСТОВОГО СООБЩЕНИЯ (для сравнения)")
    logger.info("=" * 50)
    
    # Обрабатываем текстовое сообщение
    logger.info("📤 Отправляем текстовое сообщение...")
    result = await webhook_handler.handle_update(test_update)
    
    logger.info(f"\n📥 Результат: {result}")


async def main():
    """Главная функция"""
    # Проверяем статус Intelligent Agent
    if intelligent_agent_service:
        logger.info("✅ Intelligent Agent Service доступен")
        logger.info(f"   Tools: {intelligent_agent_service.tool_registry.list_tools()}")
    else:
        logger.error("❌ Intelligent Agent Service недоступен")
    
    # Тест 1: Голосовое сообщение
    await test_voice_message()
    
    # Тест 2: Текстовое сообщение
    await test_text_message_comparison()


if __name__ == "__main__":
    asyncio.run(main())