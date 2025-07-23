#!/usr/bin/env python3
"""
Прямой вызов MCP сервера для демонстрации
"""

import asyncio
import subprocess
import json
import os
from pathlib import Path

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

async def call_digitalocean_mcp():
    """Прямой вызов DigitalOcean MCP"""
    
    print("\n🚀 Прямой вызов DigitalOcean MCP сервера")
    print("=" * 60)
    
    # Устанавливаем токен
    env = os.environ.copy()
    env["DIGITALOCEAN_API_TOKEN"] = os.getenv("DIGITALOCEAN_API_TOKEN")
    
    # Команда для запуска MCP сервера
    cmd = ["npx", "-y", "@anysphere/digitalocean-mcp"]
    
    print("📡 Запускаем MCP сервер...")
    print(f"🔧 Команда: {' '.join(cmd)}")
    print(f"🔑 Токен установлен: {'✅' if env.get('DIGITALOCEAN_API_TOKEN') else '❌'}")
    
    # Создаем процесс
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    # Отправляем команду для получения списка приложений
    request = {
        "jsonrpc": "2.0",
        "method": "mcp__digitalocean__list_apps",
        "params": {
            "query": {
                "page": 1,
                "per_page": 10
            }
        },
        "id": 1
    }
    
    print(f"\n📨 Отправляем запрос: {request['method']}")
    
    # Отправляем и получаем ответ
    try:
        # Отправляем JSON-RPC запрос
        process.stdin.write(json.dumps(request).encode() + b'\n')
        await process.stdin.drain()
        
        # Читаем ответ
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        
        if response_line:
            response = json.loads(response_line.decode())
            
            print("\n✅ Получен ответ от MCP сервера!")
            
            if "result" in response:
                apps = response["result"].get("apps", [])
                print(f"\n📱 Найдено приложений: {len(apps)}")
                
                for app in apps:
                    print(f"\n  🌊 {app.get('spec', {}).get('name', 'Unknown')}")
                    print(f"     ID: {app.get('id', 'N/A')}")
                    print(f"     Регион: {app.get('region', {}).get('slug', 'N/A')}")
                    print(f"     Статус: {app.get('phase', 'N/A')}")
                    
            elif "error" in response:
                print(f"\n❌ Ошибка: {response['error']}")
        else:
            print("\n❌ Нет ответа от сервера")
            
    except asyncio.TimeoutError:
        print("\n❌ Таймаут ожидания ответа")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        # Завершаем процесс
        process.terminate()
        await process.wait()

async def test_with_telegram_format():
    """Тест с форматированием для Telegram"""
    
    print("\n📱 Симуляция ответа для Telegram")
    print("=" * 60)
    
    # Эмулируем успешный ответ
    mock_apps = [
        {
            "id": "app-12345",
            "spec": {"name": "artem-integrator"},
            "region": {"slug": "fra1"},
            "phase": "ACTIVE",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-23T14:45:00Z"
        },
        {
            "id": "app-67890",
            "spec": {"name": "admin-panel"},
            "region": {"slug": "nyc1"},
            "phase": "ACTIVE",
            "created_at": "2024-01-10T08:00:00Z",
            "updated_at": "2024-01-22T16:30:00Z"
        }
    ]
    
    # Форматируем для Telegram
    message = "🌊 **DigitalOcean Apps**\n\n"
    
    for i, app in enumerate(mock_apps, 1):
        message += f"{i}. **{app['spec']['name']}**\n"
        message += f"   📍 Region: `{app['region']['slug']}`\n"
        message += f"   ✅ Status: `{app['phase']}`\n"
        message += f"   🆔 ID: `{app['id']}`\n"
        message += f"   📅 Updated: {app['updated_at'][:10]}\n\n"
    
    message += f"_Total apps: {len(mock_apps)}_"
    
    print("\n📨 Сообщение для Telegram:")
    print("-" * 60)
    print(message)
    
    return message

if __name__ == "__main__":
    print("Выберите тест:")
    print("1. Прямой вызов MCP сервера (может не работать в этом окружении)")
    print("2. Симуляция ответа для демонстрации")
    
    choice = input("\nВаш выбор (1 или 2): ").strip()
    
    if choice == "1":
        asyncio.run(call_digitalocean_mcp())
    else:
        asyncio.run(test_with_telegram_format())