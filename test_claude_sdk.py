#!/usr/bin/env python3
"""
Простой тест для проверки работы Claude Code SDK
"""

import asyncio
import logging
import sys
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем путь к bot модулю
sys.path.insert(0, str(Path(__file__).parent))

async def test_claude_sdk():
    """Тестирование Claude Code SDK"""
    
    print("🔍 Проверка Claude Code SDK...")
    
    # Проверка импорта
    try:
        from claude_code_sdk import query, ClaudeCodeOptions, Message
        print("✅ Claude Code SDK успешно импортирован")
        print(f"   Версия: {getattr(query, '__version__', 'Неизвестно')}")
    except ImportError as e:
        print(f"❌ Ошибка импорта Claude Code SDK: {e}")
        return
    
    # Проверка сервиса
    try:
        from bot.services.claude_code_service import ClaudeCodeService, CLAUDE_CODE_SDK_AVAILABLE
        print(f"✅ ClaudeCodeService импортирован")
        print(f"   SDK доступен: {CLAUDE_CODE_SDK_AVAILABLE}")
        
        # Создаем экземпляр сервиса
        service = ClaudeCodeService()
        print(f"✅ Сервис создан")
        print(f"   Enabled: {service.enabled}")
        print(f"   MCP Config Path: {service.mcp_config_path}")
        
        # Тестовая команда
        if service.enabled:
            print("\n🧪 Тестирование команды MCP status...")
            result = await service.execute_mcp_command("/mcp status")
            print(f"   Результат: {result}")
        else:
            print("⚠️ Сервис отключен, пропускаем тестирование команд")
            
    except Exception as e:
        print(f"❌ Ошибка при работе с сервисом: {e}")
        import traceback
        traceback.print_exc()
    
    # Проверка конфигурации
    try:
        from bot.core.config import config
        print(f"\n📋 Конфигурация:")
        print(f"   MCP enabled: {config.mcp.enabled}")
        print(f"   Anthropic enabled: {config.anthropic.enabled}")
        print(f"   Anthropic API key: {'✅' if config.anthropic.api_key else '❌'}")
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации: {e}")
    
    # Проверка MCP серверов
    try:
        import json
        mcp_config_path = Path("data/mcp-servers.json")
        if mcp_config_path.exists():
            with open(mcp_config_path) as f:
                mcp_config = json.load(f)
            print(f"\n📦 MCP серверы:")
            for server, config in mcp_config.get("mcpServers", {}).items():
                print(f"   - {server}: {config.get('command', 'N/A')}")
    except Exception as e:
        print(f"❌ Ошибка чтения MCP конфигурации: {e}")

if __name__ == "__main__":
    asyncio.run(test_claude_sdk())