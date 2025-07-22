#!/usr/bin/env python3
"""
Тест Claude Code SDK с подробной отладкой
"""

import asyncio
import logging
import sys
from pathlib import Path

# Максимальный уровень логирования для отладки
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Добавляем путь к bot модулю
sys.path.insert(0, str(Path(__file__).parent))

async def test_sdk_debug():
    """Тестирование SDK с отладкой"""
    
    print("🔍 Тестирование Claude Code SDK с отладкой...")
    
    try:
        # Прямой тест SDK
        from claude_code_sdk import query, ClaudeCodeOptions
        
        print("\n📝 Прямой вызов SDK...")
        messages = []
        
        options = ClaudeCodeOptions(
            mcpServersConfigFile=str(Path("data/mcp-servers.json"))
        )
        
        async for message in query("Check MCP status", options=options):
            msg_type = type(message).__name__
            print(f"  - Тип сообщения: {msg_type}")
            
            if hasattr(message, '__dict__'):
                print(f"    Атрибуты: {list(message.__dict__.keys())}")
            
            messages.append(message)
            
        print(f"\n✅ Получено сообщений: {len(messages)}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sdk_debug())