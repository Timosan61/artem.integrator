#!/usr/bin/env python3
"""
Тест MCP с мок-сервером для проверки работы SDK
"""

import asyncio
import json
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

async def test_with_mock():
    """Тест с мок-сервером"""
    
    print("\n🔍 Тест MCP с мок-сервером")
    print("=" * 60)
    
    # Используем Python мок-сервер вместо Node.js
    mock_server_path = Path(__file__).parent / "mcp-mock" / "server.py"
    
    # Конфигурация с мок-сервером
    mcp_config = {
        "mcpServers": {
            "test-server": {
                "command": "python",
                "args": [str(mock_server_path)],
                "env": {}
            }
        }
    }
    
    print(f"📋 Используем мок-сервер: {mock_server_path}")
    print(f"   Существует: {mock_server_path.exists()}")
    
    # Опции SDK
    options = ClaudeCodeOptions(
        max_turns=1,
        mcp_servers=mcp_config["mcpServers"],
        mcp_tools=["*"],
        permission_mode="acceptEdits"
    )
    
    # Тестовые запросы
    test_prompts = [
        "Use MCP to get test data",
        "Call test-server tool to get status"
    ]
    
    for prompt in test_prompts:
        print(f"\n🧪 Тест: {prompt}")
        print("-" * 40)
        
        try:
            messages = []
            start_time = asyncio.get_event_loop().time()
            
            async for message in query(prompt=prompt, options=options):
                msg_type = type(message).__name__
                
                # Выводим подробную информацию о сообщении
                print(f"\n📨 {msg_type}:")
                
                if hasattr(message, 'content'):
                    content = str(message.content)
                    if len(content) > 200:
                        print(f"   Content: {content[:200]}...")
                    else:
                        print(f"   Content: {content}")
                
                if hasattr(message, 'tool_calls'):
                    print(f"   Tool calls: {message.tool_calls}")
                
                if hasattr(message, '__dict__'):
                    attrs = [k for k in message.__dict__.keys() if not k.startswith('_')]
                    print(f"   Attributes: {attrs}")
                
                messages.append(message)
            
            duration = asyncio.get_event_loop().time() - start_time
            print(f"\n⏱️ Время: {duration:.2f} сек")
            print(f"✅ Сообщений: {len(messages)}")
            
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_mock())