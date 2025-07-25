#!/usr/bin/env python
"""
Тест одного MCP запроса
"""
import asyncio
import os
import sys
sys.path.append('/home/coder/Desktop/2202/artem.integrator')

async def test_one_mcp():
    print("🧪 Тест одного MCP запроса")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Нет OPENAI_API_KEY")
        return
    
    from agent.core.intelligent_agent import IntelligentAgent
    
    agent = IntelligentAgent(api_key=api_key)
    
    message = "какие у меня есть mcp сервера"
    print(f"📝 Запрос: '{message}'")
    
    try:
        response = await agent.process_message(
            message=message,
            user_id="test_user"
        )
        
        print(f"✅ Инструмент: {response.tool_used}")
        print(f"📊 Уверенность: {response.confidence:.2f}")
        print(f"💬 Ответ: {response.message[:100]}...")
        
        if response.tool_response:
            print(f"📋 Tool успех: {response.tool_response.success}")
            if response.tool_response.error:
                print(f"❌ Tool ошибка: {response.tool_response.error}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_one_mcp())