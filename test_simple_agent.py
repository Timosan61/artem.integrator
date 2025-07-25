#!/usr/bin/env python
"""
Тест упрощенной архитектуры Simple Agent
"""
import asyncio
import os
from agent.core.intelligent_agent import IntelligentAgent

async def test_simple_agent():
    """Тестирует упрощенную архитектуру"""
    print("🧪 Тестирование Simple Agent")
    
    # Проверяем, есть ли API ключ
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Нет OPENAI_API_KEY в переменных окружения")
        return
    
    # Создаем агента
    print("📦 Создание агента...")
    agent = IntelligentAgent(api_key=api_key)
    
    # Тестовые сообщения
    test_messages = [
        "привет, как дела?",
        "покажи мои приложения",
        "какие у меня базы данных?",
        "список MCP серверов",
        "нарисуй кота"
    ]
    
    print("\n🎯 Тестирование сообщений:")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. Тест: '{message}'")
        try:
            response = await agent.process_message(
                message=message,
                user_id="test_user_123"
            )
            
            print(f"   ✅ Ответ: {response.message[:100]}...")
            print(f"   🔧 Инструмент: {response.tool_used}")
            print(f"   📊 Уверенность: {response.confidence:.2f}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_simple_agent())