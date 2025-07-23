#!/usr/bin/env python3
"""
Прямой тест команды /mcp apps через сервис
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

async def test_mcp_apps():
    """Тест команды /mcp apps"""
    
    print("🚀 Тест команды /mcp apps")
    print("=" * 60)
    
    # Выполняем команду
    result = await claude_code_service.execute_mcp_command("/mcp apps", user_id="test")
    
    print(f"✅ Успешно: {result.get('success', False)}")
    print(f"📋 Команда: {result.get('command', '')}")
    print(f"📊 Количество сообщений: {result.get('message_count', 0)}")
    print(f"\n📝 Ответ:")
    print("-" * 60)
    print(result.get('response', 'Нет ответа'))
    print("-" * 60)
    
    if result.get('error'):
        print(f"\n❌ Ошибка: {result.get('error')}")
    
    if result.get('data'):
        print(f"\n📊 Данные: {result.get('data')}")

if __name__ == "__main__":
    asyncio.run(test_mcp_apps())