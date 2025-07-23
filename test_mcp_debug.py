#!/usr/bin/env python3
"""
Отладочный тест для MCP команд
"""

import asyncio
import logging
import sys
from pathlib import Path

# Детальное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_debug.log'),
        logging.StreamHandler()
    ]
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import os
load_dotenv()

# Устанавливаем переменные окружения
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

from bot.services.claude_code_service import ClaudeCodeService

async def test_mcp_debug():
    """Отладка MCP команды"""
    
    print("\n🔍 Отладка MCP команды /mcp apps")
    print("=" * 60)
    
    service = ClaudeCodeService()
    
    # Проверяем промпт
    prompt = service._format_mcp_prompt("/mcp apps")
    print(f"\n📝 Промпт: {prompt}")
    
    # Проверяем инструменты
    tools = service._get_allowed_tools("/mcp apps")
    print(f"\n🔧 Разрешенные инструменты:")
    for tool in tools:
        print(f"   - {tool}")
    
    # Проверяем системный промпт
    sys_prompt = service._get_system_prompt()
    print(f"\n💬 Системный промпт:")
    print("-" * 40)
    print(sys_prompt[:200] + "...")
    
    # Проверяем конфигурацию MCP
    import json
    if service.mcp_config_path.exists():
        with open(service.mcp_config_path) as f:
            config = json.load(f)
            print(f"\n📋 MCP серверы в конфигурации:")
            for server in config.get("mcpServers", {}):
                print(f"   - {server}")

if __name__ == "__main__":
    asyncio.run(test_mcp_debug())