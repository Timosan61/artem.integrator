#!/usr/bin/env python3
"""
Тест команды /mcp apps для проверки эмуляции
"""

import asyncio
import logging
import sys
from pathlib import Path

# Настройка логирования в файл
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_test.log'),
        logging.StreamHandler()
    ]
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from bot.services.claude_code_service import ClaudeCodeService

async def test_mcp_apps():
    """Тест команды /mcp apps"""
    
    print("\n🧪 Тест команды /mcp apps")
    print("=" * 50)
    
    service = ClaudeCodeService()
    
    from bot.services.claude_code_service import CLAUDE_CODE_SDK_AVAILABLE
    print(f"✅ SDK доступен: {CLAUDE_CODE_SDK_AVAILABLE}")
    print(f"✅ MCP включен: {service.enabled}")
    
    # Тестируем команду
    result = await service.execute_mcp_command("/mcp apps")
    
    print(f"\n📊 Результат:")
    print(f"   - Успешно: {result.get('success')}")
    print(f"   - Ошибка: {result.get('error', 'Нет')}")
    
    response = result.get('response', '')
    print(f"\n📄 Ответ:")
    print("-" * 50)
    print(response)
    
    # Проверяем на эмуляцию
    if "Emulated" in response or "⚠️" in response:
        print("\n⚠️ ВНИМАНИЕ: Получен эмулированный ответ!")
    else:
        print("\n✅ Получен реальный ответ от MCP")

if __name__ == "__main__":
    asyncio.run(test_mcp_apps())