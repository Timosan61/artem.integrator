#!/usr/bin/env python3
"""
Быстрый тест одной MCP команды
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from bot.services.claude_code_service import ClaudeCodeService

async def quick_test():
    service = ClaudeCodeService()
    
    print("🚀 Быстрый тест MCP с реальным API")
    print("="*50)
    
    # Тестируем только статус
    result = await service.execute_mcp_command("/mcp status")
    
    if result.get('success'):
        print("✅ Успешно!")
        print(f"📄 Ответ: {result.get('response', '')[:200]}...")
    else:
        print(f"❌ Ошибка: {result.get('error')}")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(quick_test())