#!/usr/bin/env python3
"""
Тест обработки вопроса об инструментах MCP через Intelligent Agent
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
from agent.core.intelligent_agent import IntelligentAgent

async def test_mcp_tools_question():
    """Тестирует обработку вопроса об инструментах MCP"""
    
    # Создаем тестовое сообщение от админа
    test_update = {
        "update_id": 12345678,
        "message": {
            "message_id": 1234,
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
            "text": "какие у тебя инструменты mcp"
        }
    }
    
    logger.info("=" * 80)
    logger.info("ТЕСТ: Вопрос об инструментах MCP")
    logger.info("=" * 80)
    
    # Проверяем статус Intelligent Agent
    logger.info("\n1. ПРОВЕРКА INTELLIGENT AGENT SERVICE:")
    if intelligent_agent_service:
        logger.info(f"   ✅ Service существует")
        status = intelligent_agent_service.get_status()
        logger.info(f"   Enabled: {status['enabled']}")
        logger.info(f"   Available: {status['available']}")
        logger.info(f"   Tools: {status['tools']}")
        
        # Проверяем реестр инструментов
        if intelligent_agent_service.tool_registry:
            mcp_tool = intelligent_agent_service.tool_registry.get_tool("mcp_executor")
            if mcp_tool:
                logger.info(f"   ✅ MCP Tool найден в реестре")
                logger.info(f"      Metadata: {mcp_tool.get_metadata()}")
            else:
                logger.error(f"   ❌ MCP Tool НЕ найден в реестре")
    else:
        logger.error("   ❌ intelligent_agent_service is None")
    
    # Проверяем Intelligent Agent напрямую
    logger.info("\n2. ПРОВЕРКА INTELLIGENT AGENT:")
    if intelligent_agent_service and intelligent_agent_service.agent:
        agent = intelligent_agent_service.agent
        logger.info(f"   ✅ Agent существует")
        logger.info(f"   Model: {agent.model}")
        logger.info(f"   Tool Registry: {agent.tool_registry}")
        
        # Проверяем доступные функции
        logger.info(f"   Available functions: {len(agent.available_functions)}")
        for func in agent.available_functions:
            func_name = func['function']['name']
            logger.info(f"      - {func_name}")
    
    logger.info("\n3. ОТПРАВКА ТЕСТОВОГО СООБЩЕНИЯ:")
    logger.info(f"   Text: '{test_update['message']['text']}'")
    logger.info(f"   User: @{test_update['message']['from']['username']} (ID: {test_update['message']['from']['id']})")
    
    # Обрабатываем сообщение
    result = await webhook_handler.handle_update(test_update)
    
    logger.info("\n4. РЕЗУЛЬТАТ ОБРАБОТКИ:")
    logger.info(f"   Response: {result}")
    
    # Проверяем логи на использование MCP
    logger.info("\n5. АНАЛИЗ ОБРАБОТКИ:")
    if result.get("ok"):
        logger.info("   ✅ Сообщение обработано успешно")
        if result.get("response_sent"):
            logger.info("   ✅ Ответ отправлен")
        else:
            logger.error("   ❌ Ответ НЕ отправлен")
    else:
        logger.error(f"   ❌ Ошибка обработки: {result.get('error')}")
    
    logger.info("\n" + "=" * 80)
    logger.info("ТЕСТ ЗАВЕРШЕН")
    logger.info("=" * 80)


async def test_direct_intelligent_agent():
    """Тестирует Intelligent Agent напрямую"""
    logger.info("\n" + "=" * 80)
    logger.info("ПРЯМОЙ ТЕСТ INTELLIGENT AGENT")
    logger.info("=" * 80)
    
    if intelligent_agent_service and intelligent_agent_service.agent:
        agent = intelligent_agent_service.agent
        
        # Тестируем обработку сообщения напрямую
        response = await agent.process_message(
            message="какие у тебя инструменты mcp",
            user_id="229838448",
            context=None
        )
        
        logger.info(f"\nAgent Response:")
        logger.info(f"   Message: {response.message}")
        logger.info(f"   Tool Used: {response.tool_used}")
        logger.info(f"   Intent: {response.intent}")
        logger.info(f"   Confidence: {response.confidence}")
        
        if response.tool_response:
            logger.info(f"\nTool Response:")
            logger.info(f"   Success: {response.tool_response.success}")
            logger.info(f"   Data: {response.tool_response.data}")
            logger.info(f"   Metadata: {response.tool_response.metadata}")


async def main():
    """Главная функция"""
    # Тест 1: Через webhook handler
    await test_mcp_tools_question()
    
    # Небольшая пауза
    await asyncio.sleep(2)
    
    # Тест 2: Напрямую через Intelligent Agent
    await test_direct_intelligent_agent()


if __name__ == "__main__":
    asyncio.run(main())