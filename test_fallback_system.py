#!/usr/bin/env python3
"""
Тест системы fallback LLM провайдеров
OpenAI → Anthropic → Claude SDK
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from agent.core.intelligent_agent import IntelligentAgent

async def test_normal_operation():
    """Тест нормальной работы с OpenAI"""
    print("\n🧪 === ТЕСТ 1: Нормальная работа с OpenAI ===")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY не найден - пропускаем тест")
        return False
    
    print(f"✅ OpenAI ключ: {'***' + openai_key[-4:] if openai_key else 'Нет'}")
    print(f"✅ Anthropic ключ: {'***' + anthropic_key[-4:] if anthropic_key else 'Нет'}")
    
    try:
        # Создаем агента с обоими ключами
        agent = IntelligentAgent(
            api_key=openai_key,
            model="gpt-4o-mini",  # Используем более дешевую модель для тестов
            anthropic_api_key=anthropic_key
        )
        
        print("✅ IntelligentAgent создан успешно")
        
        # Проверяем статистику провайдеров
        print(f"📊 Статистика: {agent.provider_stats}")
        
        # Тестируем простое сообщение
        response = await agent.process_message(
            message="Привет! Скажи просто 'Привет от агента'",
            user_id="test_user"
        )
        
        print(f"📝 Ответ: {response.message[:100]}...")
        print(f"📊 Уверенность: {response.confidence}")
        print(f"📊 Статистика после: {agent.provider_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        return False

async def test_openai_failure():
    """Тест fallback при отказе OpenAI"""
    print("\n🧪 === ТЕСТ 2: Fallback при неправильном OpenAI ключе ===")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY не найден - пропускаем тест fallback")
        return False
    
    try:
        # Создаем агента с неправильным OpenAI ключом
        agent = IntelligentAgent(
            api_key="sk-invalid_key_to_test_fallback",  # Неправильный ключ
            model="gpt-4o-mini",
            anthropic_api_key=anthropic_key
        )
        
        print("✅ IntelligentAgent создан с неправильным OpenAI ключом")
        
        # Тестируем fallback на Anthropic
        response = await agent.process_message(
            message="Скажи 'Привет от Anthropic fallback'",
            user_id="test_user"
        )
        
        print(f"📝 Ответ: {response.message[:100]}...")
        print(f"📊 Уверенность: {response.confidence}")
        print(f"📊 Статистика: {agent.provider_stats}")
        
        # Проверяем что был использован Anthropic
        if agent.provider_stats["anthropic_calls"] > 0:
            print("✅ Fallback на Anthropic работает!")
            return True
        else:
            print("❌ Fallback на Anthropic не сработал")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка в тесте fallback: {e}")
        return False

async def test_claude_sdk_fallback():
    """Тест fallback на Claude SDK при отказе всех LLM"""
    print("\n🧪 === ТЕСТ 3: Fallback на Claude SDK ===")
    
    try:
        # Создаем агента без правильных ключей
        agent = IntelligentAgent(
            api_key="sk-invalid_openai_key",
            model="gpt-4o-mini",
            anthropic_api_key="sk-ant-invalid_anthropic_key"
        )
        
        print("✅ IntelligentAgent создан без правильных ключей")
        
        # Проверяем доступность Claude SDK
        if agent.claude_code_service:
            print("✅ Claude Code Service доступен")
            
            # Тестируем fallback на Claude SDK
            response = await agent.process_message(
                message="список приложений",  # MCP команда
                user_id="test_user"
            )
            
            print(f"📝 Ответ: {response.message[:100]}...")
            print(f"📊 Статистика: {agent.provider_stats}")
            
            # Проверяем что был использован Claude SDK
            if agent.provider_stats["claude_sdk_calls"] > 0:
                print("✅ Fallback на Claude SDK работает!")
                return True
            else:
                print("⚠️ Claude SDK не был вызван (возможно, из-за ошибок API)")
                return False
        else:
            print("⚠️ Claude Code Service недоступен")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка в тесте Claude SDK: {e}")
        return False

async def test_provider_statistics():
    """Тест статистики использования провайдеров"""
    print("\n🧪 === ТЕСТ 4: Статистика провайдеров ===")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY не найден")
        return False
    
    try:
        agent = IntelligentAgent(
            api_key=openai_key,
            model="gpt-4o-mini",
            anthropic_api_key=anthropic_key
        )
        
        print("📊 Начальная статистика:", agent.provider_stats)
        
        # Делаем несколько запросов
        messages = [
            "Привет",
            "Как дела?", 
            "Спасибо за ответы"
        ]
        
        for i, msg in enumerate(messages, 1):
            print(f"\n📨 Запрос {i}: {msg}")
            response = await agent.process_message(msg, user_id="test_user")
            print(f"📨 Ответ {i}: {response.message[:50]}...")
            print(f"📊 Статистика: {agent.provider_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте статистики: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🚀 === ТЕСТИРОВАНИЕ СИСТЕМЫ FALLBACK LLM ПРОВАЙДЕРОВ ===")
    
    # Проверяем переменные окружения
    print("\n🔧 Проверка окружения:")
    print(f"OPENAI_API_KEY: {'✅ Есть' if os.getenv('OPENAI_API_KEY') else '❌ Нет'}")
    print(f"ANTHROPIC_API_KEY: {'✅ Есть' if os.getenv('ANTHROPIC_API_KEY') else '❌ Нет'}")
    print(f"MCP_ENABLED: {os.getenv('MCP_ENABLED', 'false')}")
    
    # Загружаем .env файл
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env файл загружен")
    except ImportError:
        print("⚠️ python-dotenv не установлен, пропускаем .env")
    
    results = []
    
    # Запускаем тесты
    test_functions = [
        ("Нормальная работа OpenAI", test_normal_operation),
        ("Fallback на Anthropic", test_openai_failure),
        ("Fallback на Claude SDK", test_claude_sdk_fallback),
        ("Статистика провайдеров", test_provider_statistics)
    ]
    
    for test_name, test_func in test_functions:
        try:
            result = await test_func()
            results.append((test_name, "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"))
        except Exception as e:
            results.append((test_name, f"💥 ОШИБКА: {e}"))
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("📋 ИТОГОВЫЙ ОТЧЕТ:")
    for test_name, status in results:
        print(f"  {status}: {test_name}")
    
    passed = sum(1 for _, status in results if "✅" in status)
    total = len(results)
    print(f"\n🎯 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система fallback работает корректно!")
    else:
        print("⚠️ Есть проблемы с системой fallback")

if __name__ == "__main__":
    asyncio.run(main())