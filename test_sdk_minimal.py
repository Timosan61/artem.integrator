#!/usr/bin/env python3
"""
Минимальный тест Claude Code SDK с явным MCP
"""
import asyncio
import os
import json
from pathlib import Path

# Настройка Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

# Загружаем ключи из .env
from dotenv import load_dotenv
load_dotenv()

# Импорт Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions, Message
    print("✅ Claude Code SDK импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта Claude Code SDK: {e}")
    exit(1)

async def test_direct_mcp():
    """Тест прямого вызова MCP"""
    
    # Конфигурация MCP
    mcp_servers = {
        "digitalocean": {
            "command": "npx",
            "args": ["-y", "@anysphere/digitalocean-mcp"],
            "env": {
                "DIGITALOCEAN_API_TOKEN": os.getenv("DIGITALOCEAN_API_TOKEN", "")
            }
        }
    }
    
    # Опции SDK
    options = ClaudeCodeOptions(
        max_turns=1,
        system_prompt="""You MUST use mcp__digitalocean__list_apps function.
DO NOT use TodoWrite, Task, or any other tools.
Just call the MCP function directly.""",
        allowed_tools=["mcp__digitalocean__list_apps"],
        disallowed_tools=["TodoWrite", "Task", "ExitPlanMode", "WebSearch", "WebFetch"],
        mcp_servers=mcp_servers,
        permission_mode="acceptEdits"
    )
    
    # Промпт
    prompt = "Use mcp__digitalocean__list_apps function to list all DigitalOcean apps. Call it with parameter {\"query\": {}}."
    
    print(f"\n📨 Отправляем промпт: {prompt}")
    print("-" * 60)
    
    messages = []
    async for message in query(prompt=prompt, options=options):
        messages.append(message)
        print(f"\n📩 Получено сообщение: {type(message).__name__}")
        if hasattr(message, 'content') and message.content:
            print(f"   Содержимое: {str(message.content)[:200]}...")
    
    print(f"\n✅ Получено {len(messages)} сообщений")
    
    # Анализируем результат
    for msg in messages:
        if hasattr(msg, 'content') and isinstance(msg.content, list):
            for block in msg.content:
                if hasattr(block, 'name'):
                    print(f"\n🔧 Использован инструмент: {block.name}")
                    if hasattr(block, 'input'):
                        print(f"   Параметры: {block.input}")

if __name__ == "__main__":
    asyncio.run(test_direct_mcp())