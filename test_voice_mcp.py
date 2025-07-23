#!/usr/bin/env python3
"""
Тест голосового MCP pipeline
Эмулирует обработку голосового сообщения для проверки интеграции
"""

import asyncio
import sys
import os
import logging

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice.voice_service import VoiceService
from bot.services.claude_code_service import claude_code_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_voice_mcp():
    """Тест голосового MCP pipeline"""
    
    print("🎤 Тестирование голосового MCP pipeline")
    print("=" * 50)
    
    # Эмулируем голосовые данные
    voice_data = {
        'file_id': 'test_voice_file_123',
        'duration': 15,
        'mime_type': 'audio/ogg'
    }
    
    # Эмулируем транскрипцию для теста
    test_voice_texts = [
        "посмотри какие у меня приложения в DigitalOcean",
        "какие у меня базы данных",
        "покажи деплойменты",
        "информация о sample-aspnetapp"
    ]
    
    for test_text in test_voice_texts:
        print(f"\n📋 Тестируем запрос: '{test_text}'")
        
        # Прямой тест Claude Code SDK с голосовым форматом
        mcp_command = f"/voice {test_text}"
        
        try:
            result = await claude_code_service.execute_mcp_command(
                command=mcp_command,
                user_id="test_user_123"
            )
            
            if result["success"]:
                print(f"✅ Успешно обработано")
                print(f"📝 Ответ: {result['response'][:200]}...")
            else:
                print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Тест голосового MCP pipeline завершен")

async def test_direct_voice_processing():
    """Тест прямой обработки голосовых команд"""
    
    print("\n🎯 Тест прямой обработки голосовых команд")
    print("=" * 50)
    
    # Проверка ClaudeCodeService напрямую
    test_cases = [
        "/voice какие у меня приложения",
        "/voice покажи мои базы данных",
        "/voice список деплойментов",
        "/voice информация о приложении sample-aspnetapp"
    ]
    
    for command in test_cases:
        print(f"\n🔧 Тест: {command}")
        
        try:
            result = await claude_code_service.execute_mcp_command(
                command=command,
                user_id="test_user_456"
            )
            
            if result["success"]:
                print(f"✅ Ответ получен ({len(result['response'])} символов)")
                print(f"📊 Формат: {type(result['response'])}")
            else:
                print(f"❌ Ошибка: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")

if __name__ == "__main__":
    async def main():
        print("🚀 Запуск тестов голосового MCP")
        
        # Проверка доступности сервисов
        print("🔍 Проверка доступности сервисов...")
        
        claude_test = await claude_code_service.test_connection()
        print(f"ClaudeCodeService: {'✅' if claude_test['success'] else '❌'}")
        print(f"  Enabled: {claude_test['enabled']}")
        print(f"  API Key: {claude_test['api_key_set']}")
        
        # Запуск тестов
        await test_direct_voice_processing()
        await test_voice_mcp()
        
        print("\n🎉 Все тесты завершены!")
    
    asyncio.run(main())