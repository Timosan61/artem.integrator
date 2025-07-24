#!/usr/bin/env python3
"""
Тестовый скрипт для проверки импорта Intelligent Agent
"""
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    logger.info("1. Проверяем импорт agent.core.intelligent_agent...")
    from agent.core.intelligent_agent import IntelligentAgent
    logger.info("✅ IntelligentAgent импортирован")
except Exception as e:
    logger.error(f"❌ Ошибка импорта IntelligentAgent: {e}")

try:
    logger.info("\n2. Проверяем импорт agent.core.tool_registry...")
    from agent.core.tool_registry import ToolRegistry
    logger.info("✅ ToolRegistry импортирован")
except Exception as e:
    logger.error(f"❌ Ошибка импорта ToolRegistry: {e}")

try:
    logger.info("\n3. Проверяем импорт intelligent_agent_service...")
    from bot.services.intelligent_agent_service import intelligent_agent_service
    logger.info("✅ intelligent_agent_service импортирован")
    
    if intelligent_agent_service:
        logger.info(f"   Enabled: {intelligent_agent_service.enabled}")
        logger.info(f"   Available: {intelligent_agent_service.is_available()}")
        if intelligent_agent_service.tool_registry:
            tools = intelligent_agent_service.tool_registry.list_tools()
            logger.info(f"   Tools: {tools}")
    else:
        logger.warning("⚠️ intelligent_agent_service is None")
        
except Exception as e:
    logger.error(f"❌ Ошибка импорта intelligent_agent_service: {e}", exc_info=True)

logger.info("\n4. Проверяем переменные окружения...")
import os
logger.info(f"   OPENAI_API_KEY: {'✅ Установлен' if os.getenv('OPENAI_API_KEY') else '❌ Отсутствует'}")
logger.info(f"   YOUTUBE_API_KEY: {'✅ Установлен' if os.getenv('YOUTUBE_API_KEY') else '❌ Отсутствует'}")