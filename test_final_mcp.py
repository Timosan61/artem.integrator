#!/usr/bin/env python3
"""
Финальный тест MCP команды
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.services.claude_code_service import claude_code_service

async def main():
    """Главная функция теста"""
    
    print("\n🎯 ФИНАЛЬНЫЙ ТЕСТ MCP КОМАНДЫ")
    print("=" * 60)
    
    # Тестируем команду /mcp apps
    print("\n📱 Тестируем команду: /mcp apps")
    result = await claude_code_service.execute_mcp_command("/mcp apps")
    
    if result.get('success'):
        print("✅ Команда выполнена успешно!")
        print(f"\n📝 Ответ для Telegram ({len(result.get('response', ''))} символов):")
        print("-" * 60)
        print(result.get('response', ''))
        
        # Проверяем наличие данных
        response = result.get('response', '')
        if "artem-integrator" in response and "DigitalOcean" in response:
            print("\n✅ ТЕСТ ПРОЙДЕН! MCP команда работает корректно.")
            print("📊 Данные содержат информацию о приложениях DigitalOcean")
        else:
            print("\n⚠️ Тест выполнен, но данные могут быть неполными")
    else:
        print("❌ Ошибка выполнения команды")
        print(f"Детали: {result.get('error', 'Неизвестная ошибка')}")
    
    # Тестируем другие команды
    print("\n\n📋 Тестируем команду: /mcp status")
    status_result = await claude_code_service.execute_mcp_command("/mcp status")
    
    if status_result.get('success'):
        print("✅ Команда status выполнена")
        # Показываем только первые 500 символов
        status_text = status_result.get('response', '')[:500]
        print(f"📝 Краткий ответ: {status_text}...")

if __name__ == "__main__":
    asyncio.run(main())