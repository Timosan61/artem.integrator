#!/usr/bin/env python3
"""
Подробный тест MCP с выводом всех сообщений
"""

import asyncio
import logging
import sys
from pathlib import Path
import os
import json

# Детальное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

from bot.services.claude_code_service import ClaudeCodeService

async def test_verbose():
    """Подробный тест MCP"""
    
    print("\n🔍 Подробный тест MCP команды")
    print("=" * 60)
    
    service = ClaudeCodeService()
    
    # Выполняем команду
    result = await service.execute_mcp_command("/mcp apps")
    
    print(f"\n✅ Результат:")
    print(f"  - Успешно: {result.get('success')}")
    print(f"  - Сообщений: {result.get('message_count')}")
    
    if result.get('error'):
        print(f"\n❌ Ошибка: {result.get('error')}")
    
    print(f"\n📝 Полный ответ:")
    print("-" * 60)
    response = result.get('response', '')
    print(response)
    
    # Если ответ содержит информацию о блокировке
    if "Permission" in response and "denied" in response:
        print("\n⚠️ SDK попытался использовать заблокированную функцию!")
        print("Это означает, что disallowed_tools работает, но SDK сначала пытается неправильную функцию.")

if __name__ == "__main__":
    asyncio.run(test_verbose())