#!/usr/bin/env python
"""
Простой быстрый тест
"""
import asyncio
import os
import sys
sys.path.append('/home/coder/Desktop/2202/artem.integrator')

async def test_quick():
    print("🧪 Быстрый тест импорта")
    
    try:
        from agent.core.intelligent_agent import IntelligentAgent
        print("✅ IntelligentAgent импортирован")
        
        # Проверяем что API ключ есть
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ Нет OPENAI_API_KEY")
            return
            
        print("✅ API ключ найден")
        
        # Создаем агента
        agent = IntelligentAgent(api_key=api_key)
        print("✅ Simple Agent создан")
        
        # Проверяем доступные функции
        functions = agent.available_functions
        print(f"✅ Доступно функций: {len(functions)}")
        
        for func in functions:
            name = func['function']['name']
            print(f"   - {name}")
        
        # Проверяем Claude Code Service
        if hasattr(agent, 'claude_code_service') and agent.claude_code_service:
            print("✅ Claude Code Service подключен")
        else:
            print("❌ Claude Code Service НЕ подключен")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_quick())