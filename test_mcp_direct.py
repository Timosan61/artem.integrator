#!/usr/bin/env python3
"""
Прямой тест MCP через Claude Code SDK с логированием
"""

import asyncio
import os
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

# Загружаем .env
from dotenv import load_dotenv
load_dotenv()

async def test_direct_mcp():
    """Прямой тест MCP"""
    
    print("\n🔍 Прямой тест MCP через Claude Code SDK")
    print("=" * 60)
    
    # Проверяем наличие токенов
    tokens = {
        "DIGITALOCEAN_TOKEN": os.getenv("DIGITALOCEAN_TOKEN"),
        "DIGITALOCEAN_API_TOKEN": os.getenv("DIGITALOCEAN_API_TOKEN"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }
    
    for name, value in tokens.items():
        if value:
            print(f"✅ {name}: {value[:10]}...")
        else:
            print(f"❌ {name}: не установлен")
    
    # Создаем временный файл конфигурации с правильным токеном
    do_token = tokens["DIGITALOCEAN_TOKEN"] or tokens["DIGITALOCEAN_API_TOKEN"]
    
    if not do_token:
        print("\n❌ DigitalOcean токен не найден!")
        return
    
    # Создаем конфигурацию MCP с подстановкой токена
    mcp_config = {
        "mcpServers": {
            "digitalocean": {
                "command": "node",
                "args": [str(Path(__file__).parent / "docker/mcp/servers/digitalocean/server.js")],
                "env": {
                    "DIGITALOCEAN_API_TOKEN": do_token  # Прямая подстановка токена
                }
            }
        }
    }
    
    print(f"\n📋 MCP конфигурация:")
    print(f"   Command: {mcp_config['mcpServers']['digitalocean']['command']}")
    print(f"   Args: {mcp_config['mcpServers']['digitalocean']['args']}")
    print(f"   Token: {do_token[:10]}...")
    
    # Опции SDK
    options = ClaudeCodeOptions(
        max_turns=1,
        mcp_servers=mcp_config["mcpServers"],
        mcp_tools=["*"],
        permission_mode="acceptEdits"
    )
    
    print("\n🚀 Отправка запроса...")
    
    try:
        messages = []
        async for message in query(prompt="List DigitalOcean apps using MCP", options=options):
            msg_type = type(message).__name__
            content = str(getattr(message, 'content', ''))[:200] if hasattr(message, 'content') else 'No content'
            print(f"\n📨 {msg_type}:")
            print(f"   {content}")
            messages.append(message)
            
        print(f"\n✅ Всего сообщений: {len(messages)}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_mcp())