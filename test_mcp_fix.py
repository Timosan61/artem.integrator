#!/usr/bin/env python
"""
Тест исправленной MCP архитектуры без маппингов
"""
import asyncio
import os
from agent.core.intelligent_agent import IntelligentAgent

async def test_mcp_fix():
    """Тестирует исправленную MCP архитектуру"""
    print("🧪 Тестирование исправленной MCP архитектуры")
    
    # Проверяем, есть ли API ключ
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Нет OPENAI_API_KEY в переменных окружения")
        return
    
    # Создаем агента
    print("📦 Создание агента...")
    agent = IntelligentAgent(api_key=api_key)
    
    # Тестируем проблемное сообщение
    test_message = "какие у меня есть mcp сервера"
    
    print(f"\n🎯 Тестирование: '{test_message}'")
    
    try:
        response = await agent.process_message(
            message=test_message,
            user_id="test_user_123"
        )
        
        print(f"   ✅ Ответ: {response.message[:200]}...")
        print(f"   🔧 Инструмент: {response.tool_used}")
        print(f"   📊 Уверенность: {response.confidence:.2f}")
        
        if response.tool_response:
            print(f"   📋 Данные: {response.tool_response.success}")
            if response.tool_response.data:
                print(f"   💾 Результат: {str(response.tool_response.data)[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_mcp_fix())