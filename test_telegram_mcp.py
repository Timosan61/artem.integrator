#!/usr/bin/env python3
"""
Тест MCP команды через Telegram бота
"""

import asyncio
import logging
from pathlib import Path
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

from bot.services.claude_code_service import claude_code_service
from bot.services.telegram_service import TelegramUpdate, TelegramResponse

# Создаем тестовое сообщение
test_update = TelegramUpdate(
    message_id=1001,
    user_id="229838448",  # Admin ID
    username="test_user",
    text="/mcp apps",
    chat_id="229838448",
    first_name="Test",
    last_name="User"
)

async def test_telegram_mcp():
    """Тест MCP через Telegram"""
    
    print("\n📱 Тест MCP команды через Telegram бота")
    print("=" * 60)
    print(f"👤 User: {test_update.username} (ID: {test_update.user_id})")
    print(f"💬 Команда: {test_update.text}")
    print("-" * 60)
    
    # Обрабатываем команду через Claude Code Service
    result = await claude_code_service.execute_mcp_command(
        command=test_update.text,
        user_id=test_update.user_id
    )
    
    # Создаем ответ для Telegram
    response_text = result.get('response', 'Ошибка выполнения команды')
    
    response = TelegramResponse(
        text=response_text,
        chat_id=test_update.chat_id,
        parse_mode="Markdown"
    )
    
    print(f"\n✅ Ответ получен!")
    print(f"📏 Длина: {len(response.text)} символов")
    print(f"📝 Форматирование: {response.parse_mode}")
    print("\n📨 Сообщение для Telegram:")
    print("-" * 60)
    print(response.text)
    
    # Проверяем наличие данных
    if "DigitalOcean Apps" in response.text:
        print("\n✅ Команда MCP успешно выполнена!")
        
        # Подсчитываем приложения
        app_count = response.text.count("**artem-") + response.text.count("**admin-") + response.text.count("**api-")
        print(f"📱 Найдено приложений: {app_count}")
    else:
        print("\n❌ Ответ не содержит данных о приложениях")

if __name__ == "__main__":
    asyncio.run(test_telegram_mcp())