#!/usr/bin/env python3
"""
Тестирование новой системы промптов из YAML файлов
"""
import asyncio
import logging
from bot.services.claude_code_service import ClaudeCodeService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_yaml_prompts():
    """Тестирует загрузку и использование промптов из YAML"""
    
    print("🧪 Тестирование системы YAML промптов")
    print("-" * 60)
    
    # Создаем экземпляр сервиса
    service = ClaudeCodeService()
    
    # 1. Проверяем загрузку конфигураций
    print("\n1️⃣ Проверка загрузки YAML файлов:")
    print(f"   - voice_prompts загружен: {'✅' if service.voice_prompts else '❌'}")
    print(f"   - sdk_prompts загружен: {'✅' if service.sdk_prompts else '❌'}")
    
    if service.voice_prompts:
        scenarios = service.voice_prompts.get('voice_commands', {}).get('scenarios', [])
        print(f"   - Количество голосовых сценариев: {len(scenarios)}")
        print(f"   - Сценарии: {[s.get('name', 'Unknown') for s in scenarios]}")
    
    if service.sdk_prompts:
        mappings = service.sdk_prompts.get('command_mappings', {})
        print(f"   - Количество маппингов команд: {len(mappings)}")
        print(f"   - Команды: {list(mappings.keys())[:5]}...")
    
    # 2. Тестируем системный промпт
    print("\n2️⃣ Системный промпт:")
    system_prompt = service._get_system_prompt()
    print(f"   - Длина промпта: {len(system_prompt)} символов")
    print(f"   - Первые 100 символов: {system_prompt[:100]}...")
    
    # 3. Тестируем голосовые промпты
    print("\n3️⃣ Тестирование голосовых промптов:")
    
    test_voices = [
        "покажи мои приложения",
        "какие у меня есть дроплеты",
        "список баз данных",
        "непонятная команда"
    ]
    
    for voice_text in test_voices:
        print(f"\n   Голос: '{voice_text}'")
        prompt = service._format_voice_mcp_prompt(voice_text)
        # Показываем только первые 200 символов промпта
        print(f"   Промпт (первые 200 символов): {prompt[:200]}...")
        
        # Проверяем, какое действие будет выбрано
        if "mcp__digitalocean__list_apps" in prompt:
            print("   ✅ Будет вызван list_apps")
        elif "mcp__digitalocean__list_droplets" in prompt:
            print("   ✅ Будет вызван list_droplets")
        elif "mcp__digitalocean__list_databases_cluster" in prompt:
            print("   ✅ Будет вызван list_databases")
        elif "К сожалению" in prompt:
            print("   ⚠️ Функция недоступна")
        else:
            print("   ❓ Неопределенное действие")
    
    # 4. Тестируем текстовые команды
    print("\n4️⃣ Тестирование текстовых команд:")
    
    test_commands = [
        "/mcp apps",
        "/mcp droplets",
        "/mcp databases",
        "/db SELECT * FROM users"
    ]
    
    for cmd in test_commands:
        print(f"\n   Команда: '{cmd}'")
        prompt = service._format_mcp_prompt(cmd)
        tools = service._get_allowed_tools(cmd)
        print(f"   Промпт: {prompt[:100]}...")
        print(f"   Разрешенные инструменты: {tools[:3]}...")
    
    # 5. Тестируем горячую перезагрузку
    print("\n5️⃣ Тестирование горячей перезагрузки:")
    print("   Перезагружаем промпты...")
    service.reload_prompts()
    print("   ✅ Промпты перезагружены")
    
    print("\n✅ Тестирование завершено!")
    print("-" * 60)

async def test_real_mcp_call():
    """Тестирует реальный вызов MCP с новыми промптами"""
    
    print("\n6️⃣ Тестирование реального MCP вызова:")
    
    service = ClaudeCodeService()
    
    # Тестируем голосовую команду про дроплеты
    voice_command = "/voice покажи мои дроплеты"
    print(f"   Выполняем команду: '{voice_command}'")
    
    try:
        result = await service.execute_mcp_command(voice_command, "test_user")
        print(f"   Результат: {result}")
        
        if result.get('success'):
            if "сожалению" in result.get('mcp_response', ''):
                print("   ℹ️ Получен fallback ответ (функция недоступна)")
            else:
                print("   ✅ Команда выполнена успешно")
        else:
            print(f"   ❌ Ошибка: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")

if __name__ == "__main__":
    asyncio.run(test_yaml_prompts())
    
    # Опционально: тестируем реальный MCP вызов
    # asyncio.run(test_real_mcp_call())