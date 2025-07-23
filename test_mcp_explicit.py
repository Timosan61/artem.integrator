#!/usr/bin/env python3
"""
Явный тест с прямым указанием использовать DigitalOcean
"""

import asyncio
import logging
import sys
from pathlib import Path
import os

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

from claude_code_sdk import query, ClaudeCodeOptions, Message

async def test_explicit():
    """Явный тест DigitalOcean"""
    
    print("\n🚀 Явный тест DigitalOcean MCP")
    print("=" * 60)
    
    # Загружаем конфигурацию
    import json
    config_path = Path(__file__).parent / "data" / "mcp-servers-local.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Опции с явным указанием
    options = ClaudeCodeOptions(
        max_turns=1,
        system_prompt="""You have access to DigitalOcean MCP server ONLY.
        
Available function: mcp__digitalocean__list_apps

When asked to list apps, you MUST use mcp__digitalocean__list_apps.
Do NOT use any other functions.""",
        allowed_tools=["mcp__digitalocean__list_apps"],
        disallowed_tools=["mcp__cloudflare__*"],
        mcp_servers=config["mcpServers"],
        permission_mode="acceptEdits"
    )
    
    prompt = "Call the mcp__digitalocean__list_apps function to list all DigitalOcean apps."
    
    print(f"📝 Промпт: {prompt}")
    print("🔧 Разрешенные инструменты: mcp__digitalocean__list_apps")
    print("❌ Запрещенные инструменты: mcp__cloudflare__*")
    print("-" * 60)
    
    messages = []
    async for message in query(prompt=prompt, options=options):
        messages.append(message)
        
        # Выводим тип сообщения
        msg_type = type(message).__name__
        print(f"\n📨 {msg_type}:")
        
        # Детали для AssistantMessage
        if hasattr(message, 'content'):
            if isinstance(message.content, list):
                for block in message.content:
                    if hasattr(block, 'name'):
                        print(f"  - Tool: {block.name}")
                    elif hasattr(block, 'text'):
                        print(f"  - Text: {block.text[:100]}...")
            elif isinstance(message.content, str):
                print(f"  - Content: {message.content[:100]}...")
    
    print(f"\n✅ Получено сообщений: {len(messages)}")

if __name__ == "__main__":
    asyncio.run(test_explicit())