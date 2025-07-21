"""
Улучшенная система конфигурации с типизацией и валидацией

Использует Pydantic для type safety и автоматической валидации
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Окружения приложения"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class ServiceStatus(str, Enum):
    """Статусы сервисов"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    token: str
    bot_id: int
    bot_username: str
    webhook_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'TelegramConfig':
        """Создает конфигурацию из переменных окружения"""
        token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        
        # Проверка, запущен ли код в Streamlit Cloud
        if os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or 'streamlit' in sys.modules:
            # Используем заглушку для Streamlit Cloud
            if not token:
                token = 'dummy:token_for_streamlit_cloud'
        elif not token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
            
        # Извлекаем bot_id из токена
        try:
            bot_id = int(token.split(':')[0])
        except (IndexError, ValueError):
            # Для Streamlit Cloud используем заглушку
            if os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or 'streamlit' in sys.modules:
                bot_id = 123456789
            else:
                raise ValueError("Неверный формат TELEGRAM_BOT_TOKEN")
            
        return cls(
            token=token,
            bot_id=bot_id,
            bot_username=os.getenv('BOT_USERNAME', 'artem_integrator_bot'),
            webhook_url=os.getenv('WEBHOOK_URL')
        )


@dataclass
class AdminConfig:
    """Конфигурация администраторов"""
    user_ids: List[int] = field(default_factory=list)
    usernames: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> 'AdminConfig':
        """Создает конфигурацию из переменных окружения"""
        # Парсим ID администраторов
        admin_ids = []
        admin_id_str = os.getenv('ADMIN_USER_ID', '')
        if admin_id_str:
            try:
                # Поддержка нескольких ID через запятую
                admin_ids = [int(id.strip()) for id in admin_id_str.split(',') if id.strip()]
            except ValueError:
                logger.warning(f"Неверный формат ADMIN_USER_ID: {admin_id_str}")
        
        # Парсим username администраторов
        admin_usernames = []
        admin_names_str = os.getenv('ADMIN_USERNAMES', '')
        if admin_names_str:
            admin_usernames = [name.strip() for name in admin_names_str.split(',') if name.strip()]
            
        return cls(user_ids=admin_ids, usernames=admin_usernames)
    
    def is_admin(self, user_id: int, username: Optional[str] = None) -> bool:
        """Проверяет, является ли пользователь администратором"""
        if user_id in self.user_ids:
            return True
        if username and username in self.usernames:
            return True
        return False


@dataclass
class OpenAIConfig:
    """Конфигурация OpenAI"""
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'OpenAIConfig':
        """Создает конфигурацию из переменных окружения"""
        api_key = os.getenv('OPENAI_API_KEY')
        return cls(
            api_key=api_key,
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            enabled=bool(api_key)
        )


@dataclass
class AnthropicConfig:
    """Конфигурация Anthropic Claude"""
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'AnthropicConfig':
        """Создает конфигурацию из переменных окружения"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        return cls(
            api_key=api_key,
            model=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
            enabled=bool(api_key)
        )


@dataclass
class ZepConfig:
    """Конфигурация Zep памяти"""
    api_key: Optional[str] = None
    api_url: str = "https://api.getzep.com"
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'ZepConfig':
        """Создает конфигурацию из переменных окружения"""
        api_key = os.getenv('ZEP_API_KEY')
        return cls(
            api_key=api_key,
            api_url=os.getenv('ZEP_API_URL', 'https://api.getzep.com'),
            enabled=bool(api_key)
        )


@dataclass
class WebhookConfig:
    """Конфигурация webhook"""
    base_url: str = ""
    secret_token: str = ""
    auto_setup: bool = True
    allowed_updates: List[str] = None
    max_connections: int = 40
    
    def __post_init__(self):
        if self.allowed_updates is None:
            self.allowed_updates = [
                "message", "callback_query", 
                "business_message", "business_connection"
            ]
    
    @classmethod
    def from_env(cls) -> 'WebhookConfig':
        """Создает конфигурацию из переменных окружения"""
        base_url = os.getenv('BASE_URL', os.getenv('RAILWAY_PUBLIC_DOMAIN', ''))
        if base_url and not base_url.startswith('http'):
            base_url = f"https://{base_url}"
        
        return cls(
            base_url=base_url,
            secret_token=os.getenv('TELEGRAM_WEBHOOK_SECRET', 'default-secret-token'),
            auto_setup=os.getenv('AUTO_SETUP_WEBHOOK', 'true').lower() == 'true'
        )


@dataclass
class VoiceConfig:
    """Конфигурация голосовых сообщений"""
    enabled: bool = False
    whisper_api_url: Optional[str] = None
    whisper_model: str = "whisper-1"
    
    @classmethod
    def from_env(cls) -> 'VoiceConfig':
        """Создает конфигурацию из переменных окружения"""
        enabled = os.getenv('VOICE_ENABLED', 'false').lower() == 'true'
        return cls(
            enabled=enabled,
            whisper_api_url=os.getenv('WHISPER_API_URL'),
            whisper_model=os.getenv('WHISPER_MODEL', 'whisper-1')
        )


@dataclass
class SocialMediaConfig:
    """Конфигурация социальных медиа"""
    youtube_api_key: Optional[str] = None
    instagram_api_key: Optional[str] = None
    tiktok_api_key: Optional[str] = None
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'SocialMediaConfig':
        """Создает конфигурацию из переменных окружения"""
        youtube_key = os.getenv('YOUTUBE_API_KEY')
        instagram_key = os.getenv('INSTAGRAM_API_KEY')
        tiktok_key = os.getenv('TIKTOK_API_KEY')
        
        return cls(
            youtube_api_key=youtube_key,
            instagram_api_key=instagram_key,
            tiktok_api_key=tiktok_key,
            enabled=bool(youtube_key or instagram_key or tiktok_key)
        )


@dataclass
class MCPServerConfig:
    """Конфигурация MCP сервера"""
    enabled: bool = False
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    additional_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPConfig:
    """Конфигурация Model Context Protocol"""
    enabled: bool = False
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    
    @property
    def supabase_enabled(self) -> bool:
        """Проверяет, включен ли Supabase MCP"""
        return self.servers.get('supabase', MCPServerConfig()).enabled
    
    @property
    def digitalocean_enabled(self) -> bool:
        """Проверяет, включен ли DigitalOcean MCP"""
        return self.servers.get('digitalocean', MCPServerConfig()).enabled
    
    @property
    def context7_enabled(self) -> bool:
        """Проверяет, включен ли Context7 MCP"""
        return self.servers.get('context7', MCPServerConfig()).enabled
    
    @classmethod
    def from_env(cls) -> 'MCPConfig':
        """Создает конфигурацию из переменных окружения"""
        enabled = os.getenv('MCP_ENABLED', 'false').lower() == 'true'
        
        servers = {}
        
        # Supabase
        if os.getenv('SUPABASE_ENABLED', 'false').lower() == 'true':
            servers['supabase'] = MCPServerConfig(
                enabled=True,
                api_url=os.getenv('SUPABASE_URL'),
                api_key=os.getenv('SUPABASE_KEY')
            )
        
        # DigitalOcean
        if os.getenv('DIGITALOCEAN_ENABLED', 'false').lower() == 'true':
            servers['digitalocean'] = MCPServerConfig(
                enabled=True,
                api_key=os.getenv('DIGITALOCEAN_TOKEN')
            )
        
        # Context7
        if os.getenv('CONTEXT7_ENABLED', 'false').lower() == 'true':
            servers['context7'] = MCPServerConfig(
                enabled=True
            )
            
        return cls(enabled=enabled and len(servers) > 0, servers=servers)


@dataclass
class AppConfig:
    """Главная конфигурация приложения"""
    environment: Environment
    telegram: TelegramConfig
    admin: AdminConfig
    openai: OpenAIConfig
    anthropic: AnthropicConfig
    zep: ZepConfig
    webhook: WebhookConfig
    voice: VoiceConfig
    social_media: SocialMediaConfig
    mcp: MCPConfig
    
    # Пути
    base_dir: Path
    data_dir: Path
    logs_dir: Path
    
    # Общие настройки
    debug: bool = False
    port: int = 8000
    max_message_length: int = 4096
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Создает полную конфигурацию из переменных окружения"""
        # Определяем базовые пути
        base_dir = Path(__file__).parent.parent.parent
        data_dir = base_dir / "data"
        logs_dir = base_dir / "logs"
        
        # Создаем директории если не существуют
        data_dir.mkdir(exist_ok=True)
        logs_dir.mkdir(exist_ok=True)
        
        # Определяем окружение
        env_str = os.getenv('ENVIRONMENT', 'production').lower()
        environment = Environment.PRODUCTION
        if env_str == 'development':
            environment = Environment.DEVELOPMENT
        elif env_str == 'testing':
            environment = Environment.TESTING
            
        return cls(
            environment=environment,
            telegram=TelegramConfig.from_env(),
            admin=AdminConfig.from_env(),
            openai=OpenAIConfig.from_env(),
            anthropic=AnthropicConfig.from_env(),
            zep=ZepConfig.from_env(),
            webhook=WebhookConfig.from_env(),
            voice=VoiceConfig.from_env(),
            social_media=SocialMediaConfig.from_env(),
            mcp=MCPConfig.from_env(),
            base_dir=base_dir,
            data_dir=data_dir,
            logs_dir=logs_dir,
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            port=int(os.getenv('PORT', '8000')),
            max_message_length=int(os.getenv('MAX_MESSAGE_LENGTH', '4096'))
        )
    
    def validate(self) -> List[str]:
        """Валидирует конфигурацию и возвращает список предупреждений"""
        warnings = []
        
        if not self.telegram.token:
            warnings.append("❌ TELEGRAM_BOT_TOKEN не установлен")
            
        if not self.admin.user_ids and not self.admin.usernames:
            warnings.append("⚠️ Администраторы не настроены")
            
        if not self.openai.enabled and not self.anthropic.enabled:
            warnings.append("⚠️ Ни OpenAI, ни Anthropic не настроены - AI функции недоступны")
            
        if self.mcp.enabled and not (self.openai.enabled or self.anthropic.enabled):
            warnings.append("⚠️ MCP включен, но нет доступных AI провайдеров")
            
        return warnings
    
    def get_status_info(self) -> Dict[str, Any]:
        """Возвращает информацию о статусе конфигурации"""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "services": {
                "telegram": "✅" if self.telegram.token else "❌",
                "openai": "✅" if self.openai.enabled else "❌",
                "anthropic": "✅" if self.anthropic.enabled else "❌",
                "zep": "✅" if self.zep.enabled else "❌",
                "voice": "✅" if self.voice.enabled else "❌",
                "social_media": "✅" if self.social_media.enabled else "❌",
                "mcp": "✅" if self.mcp.enabled else "❌"
            },
            "admins": {
                "user_ids": len(self.admin.user_ids),
                "usernames": len(self.admin.usernames)
            }
        }


# Создаем глобальный экземпляр конфигурации
try:
    config = AppConfig.from_env()
    
    # Валидируем и выводим предупреждения
    warnings = config.validate()
    if warnings and config.debug:
        for warning in warnings:
            logger.warning(warning)
            
    # Выводим статус в debug режиме
    if config.debug:
        logger.info(f"🚀 Конфигурация загружена: {config.get_status_info()}")
        
except Exception as e:
    logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
    raise


# Экспортируем для обратной совместимости
TELEGRAM_BOT_TOKEN = config.telegram.token
BOT_ID = config.telegram.bot_id
BOT_USERNAME = config.telegram.bot_username

ADMIN_USER_ID = config.admin.user_ids[0] if config.admin.user_ids else None
ADMIN_USERNAMES = config.admin.usernames

OPENAI_API_KEY = config.openai.api_key
OPENAI_MODEL = config.openai.model

ANTHROPIC_API_KEY = config.anthropic.api_key
ANTHROPIC_MODEL = config.anthropic.model

ZEP_API_KEY = config.zep.api_key
ZEP_API_URL = config.zep.api_url

VOICE_ENABLED = config.voice.enabled
SOCIAL_MEDIA_ENABLED = config.social_media.enabled
MCP_ENABLED = config.mcp.enabled