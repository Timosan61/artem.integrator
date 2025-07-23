#!/usr/bin/env python3
"""
Прямой тест DigitalOcean MCP функций
"""
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

# Импорт Claude Code SDK
from claude_code_sdk import query, ClaudeCodeOptions, Message

async def test_digitalocean_functions():
    """Тест различных функций DigitalOcean MCP"""
    
    # Конфигурация MCP
    mcp_servers = {
        "digitalocean": {
            "command": "npx",
            "args": ["-y", "@digitalocean/mcp"],
            "env": {
                "DIGITALOCEAN_API_TOKEN": os.getenv("DIGITALOCEAN_API_TOKEN", "")
            }
        }
    }
    
    # Тестируемые функции
    test_cases = [
        {
            "name": "List Apps",
            "prompt": "Use mcp__digitalocean__list_apps with parameter {\"query\": {}} to list all apps",
            "expected_function": "mcp__digitalocean__list_apps"
        },
        {
            "name": "List Database Clusters", 
            "prompt": "Use mcp__digitalocean__list_databases_cluster with parameter {\"query\": {}} to list all database clusters",
            "expected_function": "mcp__digitalocean__list_databases_cluster"
        },
        {
            "name": "Get Database Options",
            "prompt": "Use mcp__digitalocean__get_database_options with no parameters to get database options",
            "expected_function": "mcp__digitalocean__get_database_options"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 Тест: {test['name']}")
        print(f"📝 Промпт: {test['prompt']}")
        print("-" * 60)
        
        # Опции SDK
        options = ClaudeCodeOptions(
            max_turns=1,
            system_prompt=f"You MUST use {test['expected_function']} function. Do not use any other tools.",
            allowed_tools=[test['expected_function']],
            disallowed_tools=["TodoWrite", "Task", "Bash", "Read", "Write"],
            mcp_servers=mcp_servers,
            permission_mode="acceptEdits"
        )
        
        messages = []
        try:
            async for message in query(prompt=test['prompt'], options=options):
                messages.append(message)
                
                # Анализируем сообщения
                if hasattr(message, 'content') and isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, 'name'):
                            print(f"✅ Использована функция: {block.name}")
                            if hasattr(block, 'input'):
                                print(f"   Параметры: {json.dumps(block.input, indent=2)}")
                        elif hasattr(block, 'text'):
                            print(f"💬 Сообщение: {block.text}")
                
                # Проверяем результаты tool_result
                if hasattr(message, 'content') and isinstance(message.content, list):
                    for item in message.content:
                        if isinstance(item, dict) and item.get('type') == 'tool_result':
                            print(f"\n📊 Результат:")
                            content = item.get('content', '')
                            if len(content) > 500:
                                print(f"{content[:500]}...")
                            else:
                                print(content)
                            
                            if item.get('is_error'):
                                print(f"❌ Ошибка: {content}")
                            
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")
        
        print(f"\n📈 Всего сообщений: {len(messages)}")

if __name__ == "__main__":
    asyncio.run(test_digitalocean_functions())