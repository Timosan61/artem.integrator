#!/usr/bin/env python3
"""
Тестируем выбор агента для обработки сообщений
"""
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импортируем webhook handler
from bot.webhook.handlers import webhook_handler
from bot.services.intelligent_agent_service import intelligent_agent_service

async def test_agent_selection():
    """Тестирует выбор агента"""
    
    # Создаем тестовое сообщение от админа
    test_update = {
        "update_id": 999999,
        "message": {
            "message_id": 9999,
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
    
    logger.info("=" * 50)
    logger.info("ПРОВЕРКА INTELLIGENT AGENT SERVICE")
    logger.info("=" * 50)
    
    # Проверяем статус Intelligent Agent
    if intelligent_agent_service:
        logger.info(f"✅ intelligent_agent_service существует")
        logger.info(f"   Enabled: {intelligent_agent_service.enabled}")
        logger.info(f"   Available: {intelligent_agent_service.is_available()}")
        
        if intelligent_agent_service.tool_registry:
            tools = intelligent_agent_service.tool_registry.list_tools()
            logger.info(f"   Tools: {tools}")
    else:
        logger.error("❌ intelligent_agent_service is None")
    
    logger.info("\n" + "=" * 50)
    logger.info("ОБРАБОТКА СООБЩЕНИЯ")
    logger.info("=" * 50)
    
    # Обрабатываем сообщение
    result = await webhook_handler.handle_update(test_update)
    
    logger.info(f"\n📥 Результат: {result}")


async def main():
    """Главная функция"""
    await test_agent_selection()


if __name__ == "__main__":
    asyncio.run(main())