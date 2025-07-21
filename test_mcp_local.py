#!/usr/bin/env python3
"""
Тестирование MCP команд через Claude Code Service
"""

import asyncio
import logging
from pathlib import Path
import sys

# Добавляем путь к модулям бота
sys.path.append(str(Path(__file__).parent))

from bot.services.claude_code_service import claude_code_service
from bot.core.config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mcp_status():
    """Тестирует команду /mcp status"""
    print("\n" + "="*60)
    print("🔌 Тестирование: /mcp status")
    print("="*60)
    
    result = await claude_code_service.execute_mcp_command("/mcp status", "test_user")
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📝 Response: {result.get('response', '')[:500]}...")
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    return result.get('success', False)


async def test_mcp_projects():
    """Тестирует команду /mcp projects"""
    print("\n" + "="*60)
    print("🗄️ Тестирование: /mcp projects")
    print("="*60)
    
    result = await claude_code_service.execute_mcp_command("/mcp projects", "test_user")
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📝 Response: {result.get('response', '')[:500]}...")
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    return result.get('success', False)


async def test_db_command():
    """Тестирует команду /db"""
    print("\n" + "="*60)
    print("🗄️ Тестирование: /db SELECT version()")
    print("="*60)
    
    result = await claude_code_service.execute_mcp_command("/db SELECT version()", "test_user")
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📝 Response: {result.get('response', '')[:500]}...")
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    return result.get('success', False)


async def test_mcp_apps():
    """Тестирует команду /mcp apps"""
    print("\n" + "="*60)
    print("🌊 Тестирование: /mcp apps")
    print("="*60)
    
    result = await claude_code_service.execute_mcp_command("/mcp apps", "test_user")
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📝 Response: {result.get('response', '')[:500]}...")
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    return result.get('success', False)


async def test_docs_command():
    """Тестирует команду /docs"""
    print("\n" + "="*60)
    print("📚 Тестирование: /docs react hooks")
    print("="*60)
    
    result = await claude_code_service.execute_mcp_command("/docs react hooks", "test_user")
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📝 Response: {result.get('response', '')[:500]}...")
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    return result.get('success', False)


async def test_connection():
    """Тестирует базовое подключение"""
    print("\n" + "="*60)
    print("🔗 Тестирование подключения к Claude Code Service")
    print("="*60)
    
    result = await claude_code_service.test_connection()
    
    print(f"✅ Success: {result.get('success')}")
    print(f"🔌 Enabled: {result.get('enabled')}")
    print(f"📁 MCP Config Exists: {result.get('mcp_config_exists')}")
    print(f"🔑 API Key Set: {result.get('api_key_set')}")
    if result.get('error'):
        print(f"❌ Error: {result.get('error')}")
    
    return result.get('success', False)


async def main():
    """Главная функция тестирования"""
    print("🚀 Начинаем тестирование MCP команд")
    print("=" * 80)
    
    # Проверяем конфигурацию
    print("\n📋 Конфигурация:")
    print(f"  MCP Enabled: {config.mcp.enabled}")
    print(f"  Anthropic Enabled: {config.anthropic.enabled}")
    print(f"  Anthropic API Key: {'✅ Set' if config.anthropic.api_key else '❌ Not set'}")
    print(f"  Supabase Enabled: {config.mcp.supabase_enabled}")
    print(f"  DigitalOcean Enabled: {config.mcp.digitalocean_enabled}")
    print(f"  Context7 Enabled: {config.mcp.context7_enabled}")
    
    if not config.mcp.enabled or not config.anthropic.enabled:
        print("\n❌ MCP или Anthropic отключены в конфигурации!")
        print("Проверьте .env файл и убедитесь что:")
        print("  - MCP_ENABLED=true")
        print("  - ANTHROPIC_ENABLED=true")
        print("  - ANTHROPIC_API_KEY установлен")
        return
    
    # Выполняем тесты
    results = {
        "connection": await test_connection(),
        "status": await test_mcp_status(),
        "projects": await test_mcp_projects(),
        "db": await test_db_command(),
        "apps": await test_mcp_apps(),
        "docs": await test_docs_command()
    }
    
    # Итоги
    print("\n" + "="*80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_name.ljust(15)}: {status}")
    
    print(f"\n📈 Результат: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно! MCP работает корректно.")
    else:
        print("⚠️ Некоторые тесты не прошли. Проверьте конфигурацию и логи.")
        print("\n💡 Советы по устранению проблем:")
        print("1. Убедитесь что claude-code-sdk установлен: pip install claude-code-sdk")
        print("2. Проверьте что ANTHROPIC_API_KEY корректный")
        print("3. Проверьте наличие data/mcp-servers.json")
        print("4. Убедитесь что MCP серверы правильно настроены")


if __name__ == "__main__":
    asyncio.run(main())