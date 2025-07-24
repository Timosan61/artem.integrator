#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обработки команды /agent
"""
import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импортируем необходимые модули
from bot.webhook.handlers import webhook_handler
from bot.core.interfaces import UserRole

async def test_agent_command():
    """Тестирует обработку команды /agent"""
    
    # Создаем тестовый update с командой /agent
    test_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1001,
            "from": {
                "id": 229838448,  # ID администратора из auto_admins.json
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
            "text": "/agent"
        }
    }
    
    logger.info("🚀 Отправляем команду /agent...")
    
    # Обрабатываем update
    result = await webhook_handler.handle_update(test_update)
    
    logger.info(f"📥 Результат обработки: {result}")
    
    # Проверяем результат
    if result.get("ok"):
        logger.info("✅ Команда обработана успешно")
        if result.get("command") == "agent":
            logger.info("✅ Команда распознана как /agent")
        else:
            logger.warning("⚠️ Команда не распознана правильно")
    else:
        logger.error(f"❌ Ошибка обработки: {result.get('error')}")


async def test_regular_message():
    """Тестирует обработку обычного сообщения от админа"""
    
    # Создаем тестовый update с обычным сообщением
    test_update = {
        "update_id": 123456790,
        "message": {
            "message_id": 1002,
            "from": {
                "id": 229838448,  # ID администратора
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
            "text": "Привет, как дела?"
        }
    }
    
    logger.info("🚀 Отправляем обычное сообщение...")
    
    # Обрабатываем update
    result = await webhook_handler.handle_update(test_update)
    
    logger.info(f"📥 Результат обработки: {result}")


async def main():
    """Главная функция"""
    logger.info("=== Тестирование обработки команды /agent ===")
    
    # Тест 1: Команда /agent
    await test_agent_command()
    
    logger.info("\n" + "="*50 + "\n")
    
    # Тест 2: Обычное сообщение
    await test_regular_message()
    
    logger.info("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    asyncio.run(main())