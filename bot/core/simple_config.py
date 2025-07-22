"""
Простая конфигурация для быстрого старта без Pydantic
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)


def env_str(key: str, default: str = "") -> str:
    """Получает строковое значение из окружения"""
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    """Получает булевое значение из окружения"""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def env_int(key: str, default: int = 0) -> int:
    """Получает целочисленное значение из окружения"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


class SimpleConfig:
    """Простая конфигурация без зависимостей"""
    
    def __init__(self):
        # Базовые пути
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        
        # Создаем директории
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Telegram
        self.telegram_bot_token = env_str("TELEGRAM_BOT_TOKEN", "")
        self.webhook_secret_token = env_str("WEBHOOK_SECRET_TOKEN", "default-secret")
        
        # Извлекаем bot_id из токена
        try:
            self.bot_id = int(self.telegram_bot_token.split(':')[0]) if self.telegram_bot_token else 0
        except (IndexError, ValueError):
            self.bot_id = 0
            
        # Admin
        admin_id_str = env_str("ADMIN_USER_ID", "")
        self.admin_user_ids = []
        if admin_id_str:
            try:
                self.admin_user_ids = [int(id.strip()) for id in admin_id_str.split(',') if id.strip()]
            except ValueError:
                logger.warning(f"Неверный формат ADMIN_USER_ID: {admin_id_str}")
        
        # AI провайдеры
        self.openai_api_key = env_str("OPENAI_API_KEY", "")
        self.openai_model = env_str("OPENAI_MODEL", "gpt-4o-mini")
        self.anthropic_api_key = env_str("ANTHROPIC_API_KEY", "")
        self.anthropic_model = env_str("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        
        # Функции
        self.voice_enabled = env_bool("VOICE_ENABLED", False)
        self.mcp_enabled = env_bool("MCP_ENABLED", True)
        
        # Ngrok settings (legacy)
        self.ngrok_api_key = env_str("NGROK_API_KEY", "")
        
        # Cloudflare settings
        self.cloudflare_tunnel_token = env_str("CLOUDFLARE_TUNNEL_TOKEN", "")
        self.cloudflare_api_token = env_str("CLOUDFLARE_API_TOKEN", "")
        self.cloudflare_account_id = env_str("CLOUDFLARE_ACCOUNT_ID", "")
        
        # Общие настройки
        self.debug = env_bool("DEBUG", False)
        self.port = env_int("PORT", 8000)
        
        # MCP серверы
        self.supabase_url = env_str("SUPABASE_URL", "")
        self.supabase_key = env_str("SUPABASE_SERVICE_ROLE_KEY", "")
        self.digitalocean_token = env_str("DIGITALOCEAN_API_TOKEN", "")
        self.context7_api_key = env_str("CONTEXT7_API_KEY", "")
        
        # MCP конфигурация
        self.mcp_config_path = env_str("MCP_CONFIG_PATH", "data/mcp-servers.json")
        self.mcp_use_official = env_bool("MCP_USE_OFFICIAL", False)
        
        # Проверка конфигурации
        self._validate()
    
    def _validate(self):
        """Валидация конфигурации"""
        warnings = []
        
        if not self.telegram_bot_token:
            warnings.append("❌ TELEGRAM_BOT_TOKEN не установлен")
            
        if not self.admin_user_ids:
            warnings.append("⚠️ Администраторы не настроены")
            
        if not self.openai_api_key and not self.anthropic_api_key:
            warnings.append("⚠️ Ни OpenAI, ни Anthropic не настроены")
            
        if warnings and self.debug:
            for warning in warnings:
                logger.warning(warning)
    
    @property
    def telegram(self):
        """Совместимость с Pydantic конфигом"""
        class TelegramCompat:
            token = self.telegram_bot_token
            bot_id = self.bot_id
            bot_username = "artem_integrator_bot"
        return TelegramCompat()
    
    @property
    def admin(self):
        """Совместимость с Pydantic конфигом"""
        class AdminCompat:
            user_ids = self.admin_user_ids
            usernames = []
            def is_admin(self, user_id: int, username=None) -> bool:
                return user_id in self.user_ids
        return AdminCompat()
    
    @property
    def openai(self):
        """Совместимость с Pydantic конфигом"""
        class OpenAICompat:
            api_key = self.openai_api_key
            model = self.openai_model
            enabled = bool(self.openai_api_key)
        return OpenAICompat()
    
    @property
    def anthropic(self):
        """Совместимость с Pydantic конфигом"""
        class AnthropicCompat:
            api_key = self.anthropic_api_key
            model = self.anthropic_model
            enabled = bool(self.anthropic_api_key)
        return AnthropicCompat()
    
    @property
    def voice(self):
        """Совместимость с Pydantic конфигом"""
        class VoiceCompat:
            enabled = self.voice_enabled
        return VoiceCompat()
    
    @property
    def mcp(self):
        """Совместимость с Pydantic конфигом"""
        class MCPCompat:
            enabled = self.mcp_enabled
            supabase_enabled = bool(self.supabase_url and self.supabase_key)
            digitalocean_enabled = bool(self.digitalocean_token)
            context7_enabled = True  # Всегда включен
        return MCPCompat()
    
    @property
    def webhook(self):
        """Совместимость с Pydantic конфигом"""
        class WebhookCompat:
            secret_token = self.webhook_secret_token
        return WebhookCompat()


# Создаем глобальный экземпляр конфигурации
config = SimpleConfig()

# Экспортируем для обратной совместимости
TELEGRAM_BOT_TOKEN = config.telegram_bot_token
BOT_ID = config.bot_id
ADMIN_USER_ID = config.admin_user_ids[0] if config.admin_user_ids else None
OPENAI_API_KEY = config.openai_api_key
ANTHROPIC_API_KEY = config.anthropic_api_key
VOICE_ENABLED = config.voice_enabled
MCP_ENABLED = config.mcp_enabled