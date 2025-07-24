#!/usr/bin/env python3
"""
Тест обработки вопроса о приложениях DigitalOcean
"""
import asyncio
import logging
from datetime import datetime

# Настройка расширенного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импортируем необходимые модули
from bot.webhook.handlers import webhook_handler
from bot.services.intelligent_agent_service import intelligent_agent_service

async def test_digitalocean_apps():
    """Тестирует обработку вопроса о приложениях DigitalOcean"""
    
    # Создаем тестовое сообщение от админа
    test_update = {
        "update_id": 87654321,
        "message": {
            "message_id": 4321,
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
            "text": "покажи мои приложения в digitalocean"
        }
    }
    
    logger.info("=" * 80)
    logger.info("ТЕСТ: Вопрос о приложениях DigitalOcean")
    logger.info("=" * 80)
    
    logger.info(f"\n📤 Отправка сообщения: '{test_update['message']['text']}'")
    
    # Обрабатываем сообщение
    result = await webhook_handler.handle_update(test_update)
    
    logger.info(f"\n📥 Результат: {result}")
    
    # Проверяем логи на использование MCP
    if result.get("ok"):
        logger.info("✅ Сообщение обработано успешно")
        if result.get("response_sent"):
            logger.info("✅ Ответ отправлен")
            logger.info(f"   Message ID: {result.get('message_id')}")
        else:
            logger.error("❌ Ответ НЕ отправлен")
    else:
        logger.error(f"❌ Ошибка обработки: {result.get('error')}")


async def test_direct_mcp_command():
    """Тестирует прямое выполнение MCP команды"""
    logger.info("\n" + "=" * 80)
    logger.info("ПРЯМОЙ ТЕСТ MCP КОМАНДЫ")
    logger.info("=" * 80)
    
    if intelligent_agent_service and intelligent_agent_service.agent:
        agent = intelligent_agent_service.agent
        
        # Тестируем обработку команды напрямую
        response = await agent.process_message(
            message="покажи список моих приложений на digitalocean",
            user_id="229838448",
            context=None
        )
        
        logger.info(f"\nAgent Response:")
        logger.info(f"   Message: {response.message[:200]}...")
        logger.info(f"   Tool Used: {response.tool_used}")
        logger.info(f"   Intent: {response.intent}")
        logger.info(f"   Confidence: {response.confidence}")
        
        if response.tool_response:
            logger.info(f"\nTool Response:")
            logger.info(f"   Success: {response.tool_response.success}")
            if response.tool_response.data:
                logger.info(f"   Command: {response.tool_response.data.get('command')}")
                logger.info(f"   Response: {response.tool_response.data.get('response', '')[:200]}...")


async def main():
    """Главная функция"""
    # Тест 1: Через webhook handler
    await test_digitalocean_apps()
    
    # Небольшая пауза
    await asyncio.sleep(2)
    
    # Тест 2: Напрямую через Intelligent Agent
    await test_direct_mcp_command()


if __name__ == "__main__":
    asyncio.run(main())