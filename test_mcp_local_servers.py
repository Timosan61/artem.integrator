#!/usr/bin/env python3
"""
Тест локальных MCP серверов с исправленными путями
"""

import asyncio
import json
import os
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

async def test_local_mcp_servers():
    """Тест с локальными MCP серверами"""
    
    print("\n🔍 Тест локальных MCP серверов")
    print("=" * 60)
    
    # Проверяем наличие Node.js
    print("📋 Проверка окружения:")
    os.system("which node")
    os.system("node --version")
    
    # Определяем базовый путь
    base_path = Path(__file__).parent
    
    # Создаем простой тестовый MCP сервер
    test_server_js = base_path / "test_mcp_server.js"
    
    # Создаем минимальный MCP сервер для тестирования
    test_server_content = """#!/usr/bin/env node

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');

const server = new Server(
  {
    name: 'test-local-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Добавляем простой инструмент
server.setRequestHandler('tools/list', async () => {
  return {
    tools: [
      {
        name: 'test_tool',
        description: 'Test tool for MCP',
        inputSchema: {
          type: 'object',
          properties: {
            message: {
              type: 'string',
              description: 'Test message'
            }
          }
        }
      }
    ]
  };
});

// Обработчик вызова инструмента
server.setRequestHandler('tools/call', async (request) => {
  if (request.params.name === 'test_tool') {
    return {
      content: [
        {
          type: 'text',
          text: `Test response: ${request.params.arguments.message || 'Hello from MCP!'}`
        }
      ]
    };
  }
});

const transport = new StdioServerTransport();
server.connect(transport);

console.error('Test MCP server started');
"""
    
    # Записываем тестовый сервер
    with open(test_server_js, 'w') as f:
        f.write(test_server_content)
    
    os.chmod(test_server_js, 0o755)
    print(f"✅ Создан тестовый сервер: {test_server_js}")
    
    # Проверяем официальные MCP серверы
    official_servers = {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    }
    
    # Используем локальный тестовый сервер если нет npm
    local_servers = {
        "test-local": {
            "command": str(test_server_js),
            "args": [],
            "env": {}
        }
    }
    
    # Конфигурация MCP
    mcp_config = local_servers  # Используем локальный сервер
    
    print(f"\n📦 Конфигурация MCP серверов:")
    print(json.dumps(mcp_config, indent=2))
    
    # Опции SDK
    options = ClaudeCodeOptions(
        max_turns=1,
        mcp_servers=mcp_config,
        mcp_tools=["*"],
        permission_mode="acceptEdits"
    )
    
    # Тестовые запросы
    test_prompts = [
        "Use the test_tool from test-local server with message 'Hello MCP'",
        "List available MCP tools"
    ]
    
    for prompt in test_prompts:
        print(f"\n🧪 Запрос: {prompt}")
        print("-" * 40)
        
        try:
            messages = []
            async for message in query(prompt=prompt, options=options):
                msg_type = type(message).__name__
                print(f"📨 {msg_type}")
                
                if hasattr(message, 'content'):
                    content = str(message.content)[:200]
                    print(f"   {content}")
                    
                messages.append(message)
                
            print(f"✅ Получено сообщений: {len(messages)}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    # Удаляем временный файл
    if test_server_js.exists():
        os.remove(test_server_js)
        print(f"\n🧹 Удален временный файл: {test_server_js}")

if __name__ == "__main__":
    asyncio.run(test_local_mcp_servers())