#!/usr/bin/env python3
"""
Чистый тест без глобальных MCP серверов
"""

import asyncio
import os
import sys
from pathlib import Path

# Очищаем все возможные источники Cloudflare MCP
os.environ.pop("CLOUDFLARE_API_TOKEN", None)
os.environ.pop("CLOUDFLARE_ACCOUNT_ID", None)

# Удаляем возможные пути к конфигурациям
os.environ["MCP_CONFIG_PATH"] = str(Path(__file__).parent / "data" / "mcp-servers-local.json")

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

# Импортируем после установки переменных
from bot.services.claude_code_service import ClaudeCodeService

async def test_clean():
    """Чистый тест"""
    
    print("\n🧹 Чистый тест DigitalOcean MCP")
    print("=" * 60)
    
    # Проверяем переменные окружения
    print("\n📋 Переменные окружения:")
    print(f"  - DIGITALOCEAN_API_TOKEN: {'✅' if os.getenv('DIGITALOCEAN_API_TOKEN') else '❌'}")
    print(f"  - CLOUDFLARE_API_TOKEN: {'✅' if os.getenv('CLOUDFLARE_API_TOKEN') else '❌'}")
    print(f"  - MCP_CONFIG_PATH: {os.getenv('MCP_CONFIG_PATH', 'Not set')}")
    
    service = ClaudeCodeService()
    
    # Добавляем задержку для инициализации
    await asyncio.sleep(1)
    
    print("\n📨 Отправляем команду: /mcp digitalocean list apps")
    result = await service.execute_mcp_command("/mcp digitalocean list apps")
    
    print(f"\n✅ Результат: {result.get('success')}")
    
    if result.get('response'):
        response = result.get('response', '')
        print(f"\n📝 Ответ ({len(response)} символов):")
        print("-" * 60)
        
        # Проверяем на реальные данные
        if "error" in response.lower() or "permission" in response.lower():
            print("❌ Получена ошибка или отказ в доступе")
            print(response[:500])
        elif "digitalocean" in response.lower() or "app-" in response:
            print("✅ Получены реальные данные DigitalOcean!")
            print(response[:1000])
        else:
            print("⚠️ Получен общий ответ")
            print(response[:500])

if __name__ == "__main__":
    asyncio.run(test_clean())