#!/usr/bin/env python3
"""
Получение списка всех доступных функций DigitalOcean MCP
"""
import asyncio
import os
import json
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

from claude_code_sdk import query, ClaudeCodeOptions

async def list_mcp_functions():
    """Получить список всех функций DigitalOcean MCP"""
    
    mcp_servers = {
        "digitalocean": {
            "command": "npx",
            "args": ["-y", "@digitalocean/mcp"],
            "env": {
                "DIGITALOCEAN_API_TOKEN": os.getenv("DIGITALOCEAN_API_TOKEN", "")
            }
        }
    }
    
    options = ClaudeCodeOptions(
        max_turns=1,
        system_prompt="List ALL available mcp__digitalocean__* functions with their descriptions. Format as a list.",
        mcp_servers=mcp_servers,
        permission_mode="acceptEdits"
    )
    
    prompt = "Please list all available DigitalOcean MCP functions (mcp__digitalocean__*) with descriptions of what each function does."
    
    print("🔍 Запрашиваем список функций DigitalOcean MCP...")
    print("-" * 60)
    
    messages = []
    response_text = ""
    
    try:
        async for message in query(prompt=prompt, options=options):
            messages.append(message)
            
            # Собираем текстовый ответ
            if hasattr(message, 'content'):
                if isinstance(message.content, str):
                    response_text += message.content + "\n"
                elif isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_text += block.text + "\n"
        
        print(response_text)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print(f"\n📊 Всего сообщений: {len(messages)}")

if __name__ == "__main__":
    asyncio.run(list_mcp_functions())