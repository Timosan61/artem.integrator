#!/usr/bin/env python3
"""
Быстрый тест голосового MCP
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.services.claude_code_service import claude_code_service

async def quick_test():
    """Быстрый тест одной голосовой команды"""
    
    print("🚀 Быстрый тест голосового MCP")
    
    # Тестируем одну команду
    command = "/voice какие у меня приложения в DigitalOcean"
    
    try:
        result = await asyncio.wait_for(
            claude_code_service.execute_mcp_command(command, user_id="test_user"),
            timeout=30  # 30 секунд максимум
        )
        
        if result["success"]:
            print("✅ Успешно!")
            print(f"📝 Ответ: {result['response']}")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            
    except asyncio.TimeoutError:
        print("⏰ Тайм-аут теста")
    except Exception as e:
        print(f"❌ Исключение: {e}")

if __name__ == "__main__":
    asyncio.run(quick_test())