#!/usr/bin/env python3
"""
Тест маршрутизации администратора к IntelligentAgent
"""

import sys
import os
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_admin_routing():
    """Тестирует маршрутизацию админа к правильному агенту"""
    
    try:
        # Импортируем необходимые модули
        from bot.core.interfaces import Message, User, UserRole, MessageType
        from bot.core.agent_adapters import IntelligentAgentAdapter, DefaultAgentAdapter
        
        print("🧪 Тестирование маршрутизации администратора...")
        print("=" * 50)
        
        # Создаем тестового админа
        admin_user = User(
            id=12345,
            username="test_admin",
            first_name="Test",
            role=UserRole.ADMIN
        )
        
        # Создаем тестовое MCP сообщение от админа
        mcp_message = Message(
            id=1,
            user=admin_user,
            chat_id=12345,
            text="/mcp apps",
            type=MessageType.TEXT,
            timestamp=datetime.now(),
            metadata={},
            is_business_message=False
        )
        
        # Создаем тестовое обычное сообщение от админа
        regular_message = Message(
            id=2,
            user=admin_user,
            chat_id=12345,
            text="Привет, как дела?",
            type=MessageType.TEXT,
            timestamp=datetime.now(),
            metadata={},
            is_business_message=False
        )
        
        # Тестируем IntelligentAgent
        print("📊 Тестирование IntelligentAgentAdapter:")
        intelligent_agent = IntelligentAgentAdapter()
        
        try:
            # Проверяем MCP команду
            can_handle_mcp = await intelligent_agent.can_handle(mcp_message)
            print(f"   MCP команда '/mcp apps': {'✅ ОБРАБАТЫВАЕТ' if can_handle_mcp else '❌ НЕ ОБРАБАТЫВАЕТ'}")
            
            # Проверяем обычное сообщение (теперь должен обрабатывать)
            can_handle_regular = await intelligent_agent.can_handle(regular_message)
            print(f"   Обычное сообщение: {'✅ ОБРАБАТЫВАЕТ' if can_handle_regular else '❌ НЕ ОБРАБАТЫВАЕТ'}")
            
        except Exception as e:
            print(f"   ❌ Ошибка тестирования IntelligentAgent: {e}")
        
        # Тестируем DefaultAgent
        print("\n📊 Тестирование DefaultAgentAdapter:")
        default_agent = DefaultAgentAdapter()
        
        try:
            # Проверяем MCP команду (не должен обрабатывать если IntelligentAgent доступен)
            can_handle_mcp_default = await default_agent.can_handle(mcp_message)
            print(f"   MCP команда '/mcp apps': {'⚠️ ОБРАБАТЫВАЕТ (fallback)' if can_handle_mcp_default else '✅ НЕ ОБРАБАТЫВАЕТ'}")
            
            # Проверяем обычное сообщение (должен обрабатывать)
            can_handle_regular_default = await default_agent.can_handle(regular_message)
            print(f"   Обычное сообщение: {'✅ ОБРАБАТЫВАЕТ' if can_handle_regular_default else '❌ НЕ ОБРАБАТЫВАЕТ'}")
            
        except Exception as e:
            print(f"   ❌ Ошибка тестирования DefaultAgent: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 Ожидаемое поведение:")
        print("   • IntelligentAgent: обрабатывает ВСЕ сообщения от администраторов")
        print("   • DefaultAgent: обрабатывает сообщения от обычных пользователей и Business")
        print("   • Приоритет: IntelligentAgent (90) > DefaultAgent (10)")
        print("   • Администраторы ВСЕГДА используют IntelligentAgent")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Проверьте, что переменные окружения настроены правильно")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

async def run_test():
    """Запускает асинхронный тест"""
    return test_admin_routing()

if __name__ == "__main__":
    import asyncio
    
    try:
        result = asyncio.run(run_test())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)