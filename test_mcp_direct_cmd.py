#!/usr/bin/env python3
"""
Тест прямой команды DigitalOcean
"""

import asyncio
import logging
import sys
from pathlib import Path
import os

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Moonshot API
os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"

from bot.services.claude_code_service import ClaudeCodeService

async def test_direct():
    service = ClaudeCodeService()
    
    print("\n🚀 Тест команды: /mcp digitalocean list_apps")
    print("=" * 50)
    
    result = await service.execute_mcp_command("/mcp digitalocean list_apps")
    
    print(f"\nРезультат: {result.get('success')}")
    print(f"Ответ: {result.get('response', '')[:500]}")
    
    if result.get('error'):
        print(f"Ошибка: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_direct())