"""
Конфигурация приложения (обратная совместимость)

Этот файл оставлен для обратной совместимости.
Новый код должен использовать bot.core.config
"""

import warnings
from bot.core.config import (
    config,
    # Экспортируем старые переменные для обратной совместимости
    TELEGRAM_BOT_TOKEN,
    BOT_ID,
    BOT_USERNAME,
    ADMIN_USER_ID,
    ADMIN_USERNAMES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    ZEP_API_KEY,
    ZEP_API_URL,
    VOICE_ENABLED,
    SOCIAL_MEDIA_ENABLED,
    MCP_ENABLED
)

# Дополнительные переменные для полной совместимости
YOUTUBE_API_KEY = config.social_media.youtube_api_key
INSTAGRAM_API_KEY = config.social_media.instagram_api_key
TIKTOK_API_KEY = config.social_media.tiktok_api_key

# MCP серверы
MCP_SUPABASE_ENABLED = config.mcp.servers.get('supabase', None) and config.mcp.servers['supabase'].enabled
MCP_DIGITALOCEAN_ENABLED = config.mcp.servers.get('digitalocean', None) and config.mcp.servers['digitalocean'].enabled
MCP_CONTEXT7_ENABLED = config.mcp.servers.get('context7', None) and config.mcp.servers['context7'].enabled

# Пути
import os
BASE_DIR = str(config.base_dir)
DATA_DIR = str(config.data_dir)
LOGS_DIR = str(config.logs_dir)
INSTRUCTION_FILE = os.path.join(BASE_DIR, 'data', 'instruction.json')

# Для обратной совместимости - все проверки и выводы теперь в core.config
# Здесь оставляем минимальную логику для старого кода
if not TELEGRAM_BOT_TOKEN:
    warnings.warn(
        "Использование bot.config устарело. Переходите на bot.core.config",
        DeprecationWarning,
        stacklevel=2
    )