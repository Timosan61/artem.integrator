#!/usr/bin/env python3
"""
Быстрый тест системы fallback с настоящими API ключами
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent))

from agent.core.intelligent_agent import IntelligentAgent

async def test_with_real_keys():
    """Тест с настоящими API ключами"""
    
    # Пробуем получить ключи из окружения
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    print("🔑 API ключи:")
    print(f"  OpenAI: {'✅ Есть' if openai_key else '❌ Нет'}")
    print(f"  Anthropic: {'✅ Есть' if anthropic_key else '❌ Нет'}")
    
    if not anthropic_key:
        print("❌ Anthropic ключ обязателен для этого теста")
        return False
    
    try:
        # Создаем агента
        agent = IntelligentAgent(
            api_key=openai_key or "sk-invalid_key_for_testing",
            model="gpt-4o-mini",
            anthropic_api_key=anthropic_key
        )
        
        print("\n🧪 Тестируем простое сообщение...")
        
        response = await agent.process_message(
            message="Просто скажи 'Привет от системы fallback!'",
            user_id="test_user"
        )
        
        print(f"\n📝 Ответ: {response.message}")
        print(f"📊 Уверенность: {response.confidence}")
        print(f"📊 Статистика провайдеров: {agent.provider_stats}")
        
        # Проверяем какой провайдер сработал
        if agent.provider_stats["openai_calls"] > 0:
            print("✅ Работает через OpenAI")
        elif agent.provider_stats["anthropic_calls"] > 0:
            print("✅ Работает через Anthropic (fallback)")
        elif agent.provider_stats["claude_sdk_calls"] > 0:
            print("✅ Работает через Claude SDK (fallback)")
        else:
            print("❌ Ни один провайдер не сработал")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    print("🚀 === БЫСТРЫЙ ТЕСТ СИСТЕМЫ FALLBACK ===")
    
    success = await test_with_real_keys()
    
    if success:
        print("\n🎉 Система fallback работает корректно!")
    else:
        print("\n❌ Проблемы с системой fallback")

if __name__ == "__main__":
    asyncio.run(main())