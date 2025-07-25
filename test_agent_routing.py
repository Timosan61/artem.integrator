#!/usr/bin/env python3
"""
Тестирование маршрутизации агентов
"""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.core.interfaces import Message, User, MessageType, UserRole
from bot.core.unified_agent import unified_agent

async def test_agent_routing():
    """Тестирует маршрутизацию между агентами"""
    print("🧪 Тестирование маршрутизации агентов\n")
    
    # Создаем тестовых пользователей
    admin_user = User(
        id=12345,  # Первый админ
        username="admin",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN
    )
    
    regular_user = User(
        id=67890,
        username="user",
        first_name="Regular",
        last_name="User", 
        role=UserRole.USER
    )
    
    # Тестовые сценарии
    test_cases = [
        {
            "name": "Админ пишет MCP команду",
            "user": admin_user,
            "text": "/mcp apps",
            "is_business": False,
            "expected_agent": "IntelligentAgent"
        },
        {
            "name": "Админ пишет обычное сообщение",
            "user": admin_user,
            "text": "Привет, как дела?",
            "is_business": False,
            "expected_agent": "DefaultAgent"
        },
        {
            "name": "Business сообщение от админа",
            "user": admin_user,
            "text": "Привет, это бизнес сообщение",
            "is_business": True,
            "expected_agent": "DefaultAgent"
        },
        {
            "name": "Обычный пользователь",
            "user": regular_user,
            "text": "Привет, расскажи о своих услугах",
            "is_business": False,
            "expected_agent": "DefaultAgent"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"📋 Тест {i}: {case['name']}")
        print(f"   👤 Пользователь: {case['user'].username} (роль: {case['user'].role.value})")
        print(f"   💬 Сообщение: {case['text']}")
        print(f"   📱 Business: {case['is_business']}")
        
        # Создаем сообщение
        message = Message(
            id=i,
            user=case['user'],
            chat_id=123456,
            text=case['text'],
            type=MessageType.TEXT,
            timestamp=datetime.now(),
            is_business_message=case['is_business']
        )
        
        # Проверяем каждый агент по отдельности
        print(f"   🔍 Проверка агентов:")
        for agent in unified_agent.chain.agents:
            can_handle = await agent.can_handle(message)
            print(f"     - {agent.get_name()}: {can_handle}")
        
        # Определяем какой агент будет обрабатывать
        handling_agent = await unified_agent.get_agent_for_message(message)
        
        print(f"   🤖 Будет обрабатывать: {handling_agent}")
        print(f"   ✅ Ожидаемый агент: {case['expected_agent']}")
        
        if handling_agent == case['expected_agent']:
            print("   ✅ ТЕСТ ПРОЙДЕН")
        else:
            print("   ❌ ТЕСТ НЕ ПРОЙДЕН")
        
        print()
    
    # Проверяем статус системы
    print("📊 Статус системы агентов:")
    status = unified_agent.get_status()
    for agent_name, agent_status in status.items():
        if isinstance(agent_status, dict):
            print(f"   {agent_name}: {agent_status}")
        else:
            print(f"   {agent_name}: {agent_status}")

if __name__ == "__main__":
    asyncio.run(test_agent_routing())