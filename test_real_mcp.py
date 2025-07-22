#!/usr/bin/env python3
"""
Тест MCP с реальными API ключами
"""

import asyncio
import logging
import sys
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from bot.services.claude_code_service import ClaudeCodeService

async def test_real_mcp():
    """Тест с реальными ключами"""
    
    print("\n🚀 Тестирование MCP с реальными API ключами")
    print("=" * 60)
    
    service = ClaudeCodeService()
    
    if not service.enabled:
        print("❌ MCP сервис отключен!")
        return
        
    print(f"✅ MCP сервис инициализирован")
    print(f"✅ Используем конфигурацию: {service.mcp_config_path}")
    
    # Тестовые команды
    test_commands = [
        {
            "cmd": "/mcp status",
            "desc": "Проверка статуса MCP серверов"
        },
        {
            "cmd": "/mcp apps",
            "desc": "Список DigitalOcean приложений"
        },
        {
            "cmd": "/db SELECT current_database(), version()",
            "desc": "Тест Supabase базы данных"
        },
        {
            "cmd": "/docs react hooks",
            "desc": "Поиск документации React"
        }
    ]
    
    for test in test_commands:
        print(f"\n{'='*60}")
        print(f"🧪 {test['desc']}")
        print(f"📝 Команда: {test['cmd']}")
        print("-" * 40)
        
        try:
            result = await service.execute_mcp_command(test['cmd'])
            
            if result.get('success'):
                print(f"✅ Успешно выполнено!")
                print(f"📄 Ответ:")
                response = result.get('response', '')
                if len(response) > 500:
                    print(f"{response[:500]}...")
                    print(f"(всего {len(response)} символов)")
                else:
                    print(response)
                    
                if result.get('data'):
                    print(f"\n📊 Данные: {result.get('data')}")
            else:
                print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")
            logger.error("Ошибка выполнения команды", exc_info=True)
    
    print("\n" + "="*60)
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_real_mcp())