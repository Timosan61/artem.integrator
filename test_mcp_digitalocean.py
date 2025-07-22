#!/usr/bin/env python3
"""
Тест реального MCP запроса к DigitalOcean через Claude Code SDK
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Настройка подробного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'mcp_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Добавляем путь к bot модулю
sys.path.insert(0, str(Path(__file__).parent))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

async def test_digitalocean_mcp():
    """Тестирование реального MCP запроса к DigitalOcean"""
    
    print("\n🔍 Тестирование реального MCP запроса к DigitalOcean...")
    print("=" * 60)
    
    # Проверка переменных окружения
    do_token = os.getenv("DIGITALOCEAN_TOKEN")
    if not do_token:
        print("❌ DIGITALOCEAN_TOKEN не установлен в .env")
        return
    else:
        print(f"✅ DigitalOcean token найден: {do_token[:10]}...")
    
    try:
        from bot.services.claude_code_service import ClaudeCodeService, CLAUDE_CODE_SDK_AVAILABLE
        
        print(f"\n📦 Claude Code SDK доступен: {CLAUDE_CODE_SDK_AVAILABLE}")
        
        # Создаем сервис
        service = ClaudeCodeService()
        print(f"✅ ClaudeCodeService создан")
        print(f"   Enabled: {service.enabled}")
        
        if not service.enabled:
            print("❌ Сервис отключен. Проверьте конфигурацию MCP и Anthropic.")
            return
        
        # Тестовые команды
        test_commands = [
            {
                "command": "/mcp apps",
                "description": "Список DigitalOcean приложений"
            },
            {
                "command": "/mcp do list_apps",
                "description": "Альтернативная команда для списка приложений"  
            },
            {
                "command": "/mcp do regions",
                "description": "Список регионов DigitalOcean"
            }
        ]
        
        for test in test_commands:
            print(f"\n🧪 Тест: {test['description']}")
            print(f"📝 Команда: {test['command']}")
            print("-" * 40)
            
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Выполняем команду
                result = await service.execute_mcp_command(test['command'])
                
                end_time = asyncio.get_event_loop().time()
                duration = end_time - start_time
                
                print(f"⏱️ Время выполнения: {duration:.2f} сек")
                print(f"✅ Успешно: {result.get('success', False)}")
                
                if result.get('success'):
                    print(f"📄 Ответ: {result.get('response', 'Нет ответа')[:200]}...")
                    if result.get('data'):
                        print(f"📊 Данные: {str(result.get('data'))[:200]}...")
                else:
                    print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                    
            except Exception as e:
                print(f"❌ Исключение: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📋 Проверка логов...")
    
    # Читаем последние логи
    log_files = sorted(Path('.').glob('mcp_test_*.log'))
    if log_files:
        latest_log = log_files[-1]
        print(f"📄 Логи из {latest_log}:")
        print("-" * 40)
        
        with open(latest_log) as f:
            lines = f.readlines()
            # Фильтруем важные строки
            important_lines = [
                line for line in lines
                if any(keyword in line for keyword in [
                    'MCP', 'SDK', 'DigitalOcean', 'ERROR', 'WARNING',
                    'Используем', 'Переключаемся', 'tool', 'message'
                ])
            ]
            
            for line in important_lines[-20:]:  # Последние 20 важных строк
                print(line.rstrip())

if __name__ == "__main__":
    asyncio.run(test_digitalocean_mcp())