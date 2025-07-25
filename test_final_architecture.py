#!/usr/bin/env python
"""
Тест окончательной архитектуры: убран MCPTool, прямой вызов Claude Code Service
"""
import asyncio
import os
from agent.core.intelligent_agent import IntelligentAgent

async def test_final_architecture():
    """Тестирует окончательную архитектуру без MCPTool"""
    print("🎯 Тестирование окончательной архитектуры")
    print("📋 Изменения:")
    print("   - Убран MCPTool класс")
    print("   - Убран ToolRegistry")
    print("   - Прямой вызов claude_code_service")
    print("   - claude_code_direct вместо execute_mcp_command")
    
    # Проверяем, есть ли API ключ
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Нет OPENAI_API_KEY в переменных окружения")
        return
    
    # Создаем агента
    print("\n📦 Создание Simple Agent...")
    agent = IntelligentAgent(api_key=api_key)
    
    # Тестируем разные типы запросов
    test_cases = [
        {
            "message": "какие у меня есть mcp сервера",
            "expected_tool": "claude_code_direct",
            "description": "MCP запрос (основной тест)"
        },
        {
            "message": "покажи мои приложения",
            "expected_tool": "claude_code_direct", 
            "description": "Приложения DigitalOcean"
        },
        {
            "message": "привет, как дела?",
            "expected_tool": None,
            "description": "Обычный чат"
        },
        {
            "message": "нарисуй кота",
            "expected_tool": "generate_image",
            "description": "Генерация изображения"
        }
    ]
    
    print(f"\n🧪 Запуск {len(test_cases)} тестов:")
    
    for i, test_case in enumerate(test_cases, 1):
        message = test_case["message"]
        expected_tool = test_case["expected_tool"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   📝 Запрос: '{message}'")
        
        try:
            response = await agent.process_message(
                message=message,
                user_id="test_user_final"
            )
            
            # Проверяем результат
            actual_tool = response.tool_used
            tool_match = "✅" if actual_tool == expected_tool else "❌"
            
            print(f"   {tool_match} Инструмент: {actual_tool} (ожидался: {expected_tool})")
            print(f"   📊 Уверенность: {response.confidence:.2f}")
            print(f"   💬 Ответ: {response.message[:80]}...")
            
            if response.tool_response:
                print(f"   📋 Успех tool: {response.tool_response.success}")
                if response.tool_response.data:
                    print(f"   💾 Данные: {str(response.tool_response.data)[:60]}...")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_final_architecture())