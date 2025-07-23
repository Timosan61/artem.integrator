#!/usr/bin/env python3
"""
Тест списка проектов DigitalOcean через MCP
"""
import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

from bot.services.claude_code_service import claude_code_service

async def test_projects():
    """Тест команды списка проектов"""
    
    print("🚀 Тест списка проектов DigitalOcean")
    print("=" * 60)
    
    # Проверяем доступные команды
    commands = [
        "/mcp projects",           # Возможная команда для проектов
        "/mcp do projects",        # Альтернативная команда
        "/mcp digitalocean list",  # Общий список
    ]
    
    for cmd in commands:
        print(f"\n📨 Тестируем команду: {cmd}")
        print("-" * 60)
        
        try:
            result = await claude_code_service.execute_mcp_command(cmd)
            
            print(f"✅ Успешно: {result.get('success', False)}")
            print(f"📝 Ответ:\n{result.get('response', 'Нет ответа')}")
            
            if result.get('data'):
                print(f"\n📊 Данные: {result.get('data')}")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_projects())