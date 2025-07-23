#!/usr/bin/env python3
"""
Прямой тест Claude Code Service
"""
import asyncio
import logging
from bot.services.claude_code_service import ClaudeCodeService

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_mcp_apps():
    """Тест команды MCP apps напрямую"""
    print("🧪 Тестирование Claude Code Service напрямую")
    print("-" * 60)
    
    # Создаем сервис
    service = ClaudeCodeService()
    
    # Проверяем что сервис включен
    print(f"✅ Service enabled: {service.enabled}")
    print(f"📁 Config path: {service.mcp_config_path}")
    print(f"🔑 API key set: {bool(service.api_key)}")
    print("-" * 60)
    
    # Выполняем команду
    print("🚀 Executing /mcp apps...")
    result = await service.execute_mcp_command("/mcp apps", "test_user")
    
    print("\n📊 Результат:")
    print(f"Success: {result.get('success')}")
    print(f"Response length: {len(result.get('response', ''))}")
    print(f"Has error: {bool(result.get('error'))}")
    print(f"Message count: {result.get('message_count', 0)}")
    
    print("\n📝 Response:")
    print("-" * 60)
    print(result.get('response', 'No response'))
    print("-" * 60)
    
    if result.get('error'):
        print(f"\n❌ Error: {result.get('error')}")
    
    if result.get('data'):
        print(f"\n📦 Data: {result.get('data')}")

if __name__ == "__main__":
    asyncio.run(test_mcp_apps())