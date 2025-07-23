#!/usr/bin/env python3
"""
Прямой тест DigitalOcean MCP команды
"""

import asyncio
import logging
import sys
from pathlib import Path
import os

# Детальное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_direct_do.log'),
        logging.StreamHandler()
    ]
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

# Отключаем логи от urllib3
import urllib3
urllib3.disable_warnings()
logging.getLogger("urllib3").setLevel(logging.WARNING)

from bot.services.claude_code_service import ClaudeCodeService

async def test_direct_do():
    """Тест прямой команды DigitalOcean"""
    
    print("\n🚀 Тест прямой команды DigitalOcean")
    print("=" * 60)
    
    service = ClaudeCodeService()
    
    # Проверяем конфигурацию
    print("\n📋 Проверка конфигурации:")
    print(f"  - MCP включен: {service.enabled}")
    print(f"  - Конфиг существует: {service.mcp_config_path.exists()}")
    
    if service.mcp_config_path.exists():
        import json
        with open(service.mcp_config_path) as f:
            config = json.load(f)
            servers = list(config.get("mcpServers", {}).keys())
            print(f"  - MCP серверы: {servers}")
            
            # Проверяем DigitalOcean
            do_config = config.get("mcpServers", {}).get("digitalocean", {})
            if do_config:
                print("\n✅ DigitalOcean MCP настроен:")
                print(f"  - Command: {do_config.get('command')}")
                print(f"  - Env token: {'DIGITALOCEAN_API_TOKEN' in do_config.get('env', {})}")
    
    # Тестируем команду
    print("\n📨 Отправляем команду: /mcp apps")
    print("-" * 60)
    
    result = await service.execute_mcp_command("/mcp apps")
    
    print(f"\n📊 Результат:")
    print(f"  - Успешно: {result.get('success')}")
    print(f"  - Количество сообщений: {result.get('message_count', 0)}")
    
    if result.get('error'):
        print(f"  - ❌ Ошибка: {result.get('error')}")
    
    if result.get('response'):
        print(f"\n📝 Ответ:")
        print("-" * 60)
        print(result.get('response'))
        
    if result.get('data'):
        print(f"\n📦 Данные:")
        print("-" * 60)
        print(result.get('data'))

if __name__ == "__main__":
    asyncio.run(test_direct_do())