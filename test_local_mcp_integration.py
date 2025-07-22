#!/usr/bin/env python3
"""
Интеграционный тест локальных MCP серверов через полный цикл
Telegram -> Claude Code SDK -> MCP DigitalOcean -> Telegram
"""

import asyncio
import json
import logging
import os
import sys
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Настройка логирования
log_file = f'mcp_integration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Добавляем путь к bot модулю
sys.path.insert(0, str(Path(__file__).parent))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Импортируем необходимые модули
from bot.services.claude_code_service import ClaudeCodeService, CLAUDE_CODE_SDK_AVAILABLE
from bot.core.config import config


class MCPIntegrationTester:
    """Тестер для полного цикла MCP интеграции"""
    
    def __init__(self):
        self.webhook_url = "http://localhost:8000/webhook"
        self.admin_id = int(os.getenv("ADMIN_TELEGRAM_ID", "229838448"))
        self.secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET", "test-secret")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
    async def send_telegram_update(self, text: str, chat_id: int = None) -> Dict[str, Any]:
        """Отправляет обновление в webhook как от Telegram"""
        if chat_id is None:
            chat_id = self.admin_id
            
        update = {
            "update_id": 10000,
            "message": {
                "message_id": 1000,
                "from": {
                    "id": chat_id,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": chat_id,
                    "type": "private"
                },
                "date": int(datetime.now().timestamp()),
                "text": text
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": self.secret_token
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=update,
                    headers=headers
                ) as response:
                    return {
                        "status": response.status,
                        "response": await response.json() if response.status == 200 else await response.text()
                    }
            except Exception as e:
                logger.error(f"❌ Ошибка отправки в webhook: {e}")
                return {"status": 0, "error": str(e)}
    
    async def test_direct_mcp_call(self):
        """Прямой тест вызова MCP через Claude Code Service"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 1: Прямой вызов MCP через Claude Code Service")
        print("="*60)
        
        if not CLAUDE_CODE_SDK_AVAILABLE:
            print("❌ Claude Code SDK не доступен!")
            return
            
        service = ClaudeCodeService()
        if not service.enabled:
            print("❌ Claude Code Service отключен!")
            return
            
        # Тестовые команды
        test_commands = [
            {
                "cmd": "/mcp status",
                "desc": "Статус MCP серверов"
            },
            {
                "cmd": "/mcp apps",
                "desc": "Список DigitalOcean приложений"
            },
            {
                "cmd": "/docs react useState",
                "desc": "Поиск документации React useState"
            }
        ]
        
        for test in test_commands:
            print(f"\n📝 Команда: {test['cmd']}")
            print(f"📋 Описание: {test['desc']}")
            print("-" * 40)
            
            start_time = asyncio.get_event_loop().time()
            
            try:
                result = await service.execute_mcp_command(test['cmd'])
                duration = asyncio.get_event_loop().time() - start_time
                
                print(f"⏱️ Время: {duration:.2f} сек")
                print(f"✅ Успех: {result.get('success', False)}")
                
                if result.get('success'):
                    response = result.get('response', '')
                    print(f"📄 Ответ ({len(response)} символов):")
                    print(f"   {response[:200]}..." if len(response) > 200 else f"   {response}")
                    
                    if result.get('data'):
                        print(f"📊 Данные: {json.dumps(result.get('data'), indent=2)[:200]}...")
                else:
                    print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                    
            except Exception as e:
                logger.error(f"❌ Исключение: {e}", exc_info=True)
                print(f"❌ Исключение: {e}")
    
    async def test_webhook_mcp_integration(self):
        """Тест полного цикла через webhook"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 2: Полный цикл через Telegram Webhook")
        print("="*60)
        
        # Проверяем доступность webhook
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/") as resp:
                    if resp.status != 200:
                        print("❌ Webhook сервер не доступен!")
                        return
                    print("✅ Webhook сервер доступен")
        except Exception as e:
            print(f"❌ Не могу подключиться к webhook: {e}")
            return
        
        # Тестовые сценарии
        test_scenarios = [
            {
                "message": "/mcp status",
                "description": "Команда статуса MCP"
            },
            {
                "message": "/mcp apps",
                "description": "Список DigitalOcean приложений"
            },
            {
                "message": "/docs vue composition api",
                "description": "Поиск документации Vue"
            },
            {
                "message": "Расскажи про MCP серверы",
                "description": "Обычное сообщение с упоминанием MCP"
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n📮 Отправка: {scenario['message']}")
            print(f"📋 Сценарий: {scenario['description']}")
            print("-" * 40)
            
            result = await self.send_telegram_update(scenario['message'])
            
            print(f"📬 Статус ответа: {result['status']}")
            
            if result['status'] == 200:
                response = result['response']
                print(f"✅ Webhook обработал запрос")
                print(f"   Ответ: {json.dumps(response, ensure_ascii=False, indent=2)}")
            else:
                print(f"❌ Ошибка webhook: {result.get('error', result.get('response'))}")
            
            # Даем время на обработку
            await asyncio.sleep(2)
    
    async def test_large_json_handling(self):
        """Тест обработки больших JSON ответов"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 3: Обработка больших JSON ответов")
        print("="*60)
        
        # Создаем тестовую команду, которая вернет большой ответ
        test_command = "/mcp do list_all_resources"
        
        print(f"📝 Команда: {test_command}")
        print("🎯 Цель: Проверить обработку больших JSON")
        print("-" * 40)
        
        service = ClaudeCodeService()
        
        try:
            # Включаем максимальное логирование
            original_level = logger.level
            logger.setLevel(logging.DEBUG)
            
            result = await service.execute_mcp_command(test_command)
            
            if result.get('success'):
                response = result.get('response', '')
                print(f"✅ Успешно обработан ответ размером {len(response)} символов")
                
                # Проверяем, что ответ корректно обрезан или обработан
                if len(response) > 10000:
                    print("⚠️ Большой ответ был получен и обработан")
            else:
                print(f"❌ Ошибка: {result.get('error')}")
                
            logger.setLevel(original_level)
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON ошибка (ожидаемо): {e}")
            print("   Нужно исправить обработку больших JSON")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
    
    async def run_all_tests(self):
        """Запускает все тесты"""
        print(f"\n🚀 Запуск интеграционных тестов MCP")
        print(f"📁 Лог-файл: {log_file}")
        print(f"🔧 SDK доступен: {CLAUDE_CODE_SDK_AVAILABLE}")
        print(f"🌐 Webhook URL: {self.webhook_url}")
        
        # Запускаем тесты последовательно
        await self.test_direct_mcp_call()
        await self.test_webhook_mcp_integration()
        await self.test_large_json_handling()
        
        print("\n" + "="*60)
        print("✅ Все тесты завершены")
        print(f"📋 Проверьте лог-файл для деталей: {log_file}")
        print("="*60)


async def main():
    """Главная функция"""
    tester = MCPIntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())