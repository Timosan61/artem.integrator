#!/usr/bin/env python3
"""
Тесты базового функционала Intelligent Agent с реальными вызовами OpenAI
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agent.core.intelligent_agent import IntelligentAgent
from agent.core.models import AgentResponse, ToolType


async def test_echo_tool():
    """Тест echo инструмента"""
    print("\n🧪 Тест 1: Echo Tool")
    print("-" * 50)
    
    # Получаем API ключ из окружения
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Ошибка: Установите OPENAI_API_KEY в окружении")
        return False
    
    agent = IntelligentAgent(api_key=api_key, model="gpt-4o")
    
    # Тестовые запросы
    test_cases = [
        {
            "message": "Используй echo tool чтобы повторить фразу 'Hello World'",
            "user_id": "test_user_1"
        },
        {
            "message": "Повтори 'тестовое сообщение' в верхнем регистре используя echo",
            "user_id": "test_user_2"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nТест 1.{i}: {test['message']}")
        
        try:
            response = await agent.process_message(
                message=test["message"],
                user_id=test["user_id"]
            )
            
            print(f"✅ Ответ получен:")
            print(f"   Сообщение: {response.message}")
            print(f"   Использован инструмент: {response.tool_used}")
            print(f"   Уверенность: {response.confidence}")
            
            if response.tool_response:
                print(f"   Данные инструмента: {response.tool_response.data}")
                
            # Проверки
            assert isinstance(response, AgentResponse)
            assert response.tool_used == ToolType.ECHO
            assert response.tool_response.success
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    return True


async def test_mcp_intent():
    """Тест определения MCP намерений"""
    print("\n🧪 Тест 2: MCP Intent Detection")
    print("-" * 50)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Ошибка: Установите OPENAI_API_KEY в окружении")
        return False
    
    agent = IntelligentAgent(api_key=api_key, model="gpt-4o")
    
    test_cases = [
        "Покажи мои приложения в DigitalOcean",
        "Какие у меня есть базы данных?",
        "Список всех деплойментов"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\nТест 2.{i}: {message}")
        
        try:
            response = await agent.process_message(
                message=message,
                user_id="test_mcp_user"
            )
            
            print(f"✅ Ответ получен:")
            print(f"   Сообщение: {response.message}")
            print(f"   Использован инструмент: {response.tool_used}")
            
            # Проверка что определился MCP
            assert response.tool_used == ToolType.MCP or "MCP" in response.message
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    return True


async def test_image_generation_intent():
    """Тест определения намерения генерации изображения"""
    print("\n🧪 Тест 3: Image Generation Intent")
    print("-" * 50)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Ошибка: Установите OPENAI_API_KEY в окружении")
        return False
    
    agent = IntelligentAgent(api_key=api_key, model="gpt-4o")
    
    test_cases = [
        "Нарисуй красивый закат над океаном",
        "Создай изображение кота в космосе в стиле cartoon",
        "Сгенерируй картинку робота в стиле oil painting размером 1792x1024"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\nТест 3.{i}: {message}")
        
        try:
            response = await agent.process_message(
                message=message,
                user_id="test_image_user"
            )
            
            print(f"✅ Ответ получен:")
            print(f"   Сообщение: {response.message[:100]}...")
            print(f"   Использован инструмент: {response.tool_used}")
            
            if response.tool_response and response.tool_response.data:
                print(f"   Параметры: {response.tool_response.data}")
            
            # Проверка
            assert response.tool_used == ToolType.IMAGE_GENERATOR or "изображен" in response.message.lower()
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    return True


async def test_general_chat():
    """Тест обычного чата без инструментов"""
    print("\n🧪 Тест 4: General Chat (без инструментов)")
    print("-" * 50)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Ошибка: Установите OPENAI_API_KEY в окружении")
        return False
    
    agent = IntelligentAgent(api_key=api_key, model="gpt-4o")
    
    test_cases = [
        "Привет! Как дела?",
        "Расскажи анекдот про программистов",
        "Что такое искусственный интеллект?"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\nТест 4.{i}: {message}")
        
        try:
            response = await agent.process_message(
                message=message,
                user_id="test_chat_user"
            )
            
            print(f"✅ Ответ получен:")
            print(f"   Сообщение: {response.message[:150]}...")
            print(f"   Использован инструмент: {response.tool_used}")
            
            # Проверка что НЕ использовались инструменты
            assert response.tool_used is None
            assert response.tool_response is None
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    return True


async def test_context_handling():
    """Тест работы с контекстом"""
    print("\n🧪 Тест 5: Context Handling")
    print("-" * 50)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Ошибка: Установите OPENAI_API_KEY в окружении")
        return False
    
    agent = IntelligentAgent(api_key=api_key, model="gpt-4o")
    
    # Создаем контекст разговора
    context = [
        {"role": "user", "content": "Меня зовут Алексей"},
        {"role": "assistant", "content": "Приятно познакомиться, Алексей!"}
    ]
    
    print("Контекст установлен: пользователь представился как Алексей")
    
    try:
        response = await agent.process_message(
            message="Как меня зовут?",
            user_id="test_context_user",
            context=context
        )
        
        print(f"✅ Ответ получен:")
        print(f"   Сообщение: {response.message}")
        
        # Проверка что агент помнит имя
        assert "Алексей" in response.message or "алексей" in response.message.lower()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    return True


async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов базового функционала Intelligent Agent")
    print("=" * 60)
    
    tests = [
        ("Echo Tool", test_echo_tool),
        ("MCP Intent", test_mcp_intent),
        ("Image Generation", test_image_generation_intent),
        ("General Chat", test_general_chat),
        ("Context Handling", test_context_handling)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {name}: {e}")
            results.append((name, False))
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("-" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    print("-" * 60)
    print(f"Пройдено: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
    else:
        print(f"\n⚠️  Некоторые тесты не прошли ({total - passed} из {total})")
    
    return passed == total


if __name__ == "__main__":
    # Проверка API ключа
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Ошибка: Установите переменную окружения OPENAI_API_KEY")
        print("export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Запуск тестов
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)