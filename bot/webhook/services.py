"""
Сервисы для webhook функциональности
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests

from ..core.config import config
from ..telegram_bot import bot
from ..core.agent import AgentFactory

logger = logging.getLogger(__name__)


class WebhookService:
    """Сервис для управления webhook"""
    
    def __init__(self):
        self.bot = bot
        self.base_url = config.webhook.base_url
    
    async def get_webhook_info(self) -> Dict[str, Any]:
        """Получает информацию о текущем webhook"""
        try:
            info = self.bot.get_webhook_info()
            return {
                "webhook_url": info.url or "❌ Not set",
                "pending_updates": info.pending_update_count,
                "last_error": info.last_error_message,
                "last_error_date": info.last_error_date,
                "has_custom_certificate": info.has_custom_certificate,
                "allowed_updates": info.allowed_updates or ["all"],
                "max_connections": info.max_connections,
                "ip_address": info.ip_address
            }
        except Exception as e:
            logger.error(f"Error getting webhook info: {e}")
            return {"error": str(e)}
    
    async def setup_webhook(
        self,
        custom_url: Optional[str] = None,
        custom_secret: Optional[str] = None,
        allowed_updates: Optional[List[str]] = None,
        max_connections: Optional[int] = None,
        drop_pending_updates: bool = False
    ) -> Dict[str, Any]:
        """Устанавливает webhook"""
        try:
            # Формируем URL
            webhook_url = custom_url or f"{self.base_url}/webhook"
            secret_token = custom_secret or config.webhook.secret_token
            
            # Детальное логирование для диагностики
            logger.info(f"🔧 Setting up webhook...")
            logger.info(f"   base_url: '{self.base_url}'")
            logger.info(f"   custom_url: '{custom_url}'")
            logger.info(f"   final webhook_url: '{webhook_url}'")
            logger.info(f"   secret_token: {'***' if secret_token else 'None'}")
            
            # Валидация URL
            if not webhook_url or webhook_url == "/webhook":
                error_msg = f"Invalid webhook URL: '{webhook_url}'. Check BASE_URL, RAILWAY_PUBLIC_DOMAIN or WEBHOOK_URL environment variables."
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # Параметры webhook
            params = {
                "url": webhook_url,
                "secret_token": secret_token,
                "allowed_updates": allowed_updates or config.webhook.allowed_updates,
                "drop_pending_updates": drop_pending_updates
            }
            
            if max_connections:
                params["max_connections"] = max_connections
            
            logger.info(f"🚀 Calling Telegram setWebhook with params: {dict(params, secret_token='***' if params.get('secret_token') else None)}")
            
            # Устанавливаем webhook
            result = self.bot.set_webhook(**params)
            
            if result:
                logger.info(f"✅ Webhook set successfully: {webhook_url}")
                return {
                    "success": True,
                    "webhook_url": webhook_url,
                    "message": "Webhook установлен успешно"
                }
            else:
                logger.error(f"❌ Telegram API returned False for setWebhook")
                return {
                    "success": False,
                    "error": "Telegram API returned False for setWebhook"
                }
                
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_webhook(self) -> Dict[str, Any]:
        """Удаляет webhook"""
        try:
            result = self.bot.delete_webhook()
            if result:
                logger.info("✅ Webhook deleted successfully")
                return {
                    "success": True,
                    "message": "Webhook удален"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete webhook"
                }
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class ServiceManager:
    """Менеджер для управления сервисами"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self._services_cache = {}
        self._cache_ttl = 60  # секунд
        self._last_cache_update = 0
    
    def get_services_status(self) -> Dict[str, str]:
        """Получает статус всех сервисов"""
        # Проверяем кеш
        if time.time() - self._last_cache_update < self._cache_ttl:
            return self._services_cache
        
        status = {
            "telegram": self._check_telegram(),
            "agent": self._check_agent(),
            "openai": self._check_openai(),
            "anthropic": self._check_anthropic(),
            "zep": self._check_zep(),
            "voice": self._check_voice(),
            "social_media": self._check_social_media(),
            "mcp": self._check_mcp()
        }
        
        self._services_cache = status
        self._last_cache_update = time.time()
        
        return status
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Получает детальный статус всех сервисов"""
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime": self.get_uptime(),
            "services": {
                name: {
                    "status": status,
                    "healthy": self.is_service_healthy(name)
                }
                for name, status in self.get_services_status().items()
            }
        }
    
    def get_uptime(self) -> str:
        """Получает время работы сервиса"""
        delta = datetime.now() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def is_service_healthy(self, service_name: str) -> bool:
        """Проверяет здоровье конкретного сервиса"""
        status = self.get_services_status().get(service_name, "❌ UNKNOWN")
        return status in ["✅ ENABLED", "✅ AVAILABLE", "✅ CONNECTED"]
    
    def _check_telegram(self) -> str:
        """Проверяет подключение к Telegram"""
        try:
            bot.get_me()
            return "✅ CONNECTED"
        except:
            return "❌ DISCONNECTED"
    
    def _check_agent(self) -> str:
        """Проверяет AI агента"""
        try:
            agent = AgentFactory.get_agent()
            return "✅ AVAILABLE" if agent else "❌ UNAVAILABLE"
        except:
            return "❌ ERROR"
    
    def _check_openai(self) -> str:
        """Проверяет OpenAI"""
        return "✅ ENABLED" if config.openai.enabled else "❌ DISABLED"
    
    def _check_anthropic(self) -> str:
        """Проверяет Anthropic"""
        return "✅ ENABLED" if config.anthropic.enabled else "❌ DISABLED"
    
    def _check_zep(self) -> str:
        """Проверяет Zep"""
        return "✅ ENABLED" if config.zep.enabled else "❌ DISABLED"
    
    def _check_voice(self) -> str:
        """Проверяет Voice Service"""
        try:
            # Сначала проверяем конфигурацию
            if not config.voice.enabled:
                return "❌ DISABLED"
            
            # Пытаемся импортировать модуль
            from voice.voice_service import VoiceService
            logger.debug("Voice service module imported successfully")
            return "✅ ENABLED"
        except ImportError as e:
            logger.warning(f"Voice service import error: {e}")
            return "⚠️ IMPORT ERROR"
        except Exception as e:
            logger.error(f"Voice service check error: {e}")
            return "❌ ERROR"
    
    def _check_social_media(self) -> str:
        """Проверяет Social Media Service"""
        try:
            from ..services.social_media_service import social_media_service
            return "✅ ENABLED" if social_media_service else "❌ DISABLED"
        except ImportError as e:
            logger.debug(f"Social media service import error: {e}")
            return "❌ NOT AVAILABLE"
        except Exception as e:
            logger.warning(f"Social media service check error: {e}")
            return "❌ ERROR"
    
    def _check_mcp(self) -> str:
        """Проверяет MCP"""
        return "✅ ENABLED" if config.mcp.enabled else "❌ DISABLED"


class DebugService:
    """Сервис для отладки"""
    
    def __init__(self):
        self.test_mode = False
    
    def get_recent_logs(self, lines: int = 50) -> Dict[str, Any]:
        """Получает последние строки из лог файла"""
        log_path = "logs/bot.log"
        
        try:
            if not os.path.exists(log_path):
                return {
                    "error": "Log file not found",
                    "log_path": log_path
                }
            
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                
            return {
                "total_lines": len(all_lines),
                "requested_lines": lines,
                "returned_lines": len(recent_lines),
                "logs": [line.strip() for line in recent_lines],
                "log_file_size": os.path.getsize(log_path)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "log_path": log_path
            }
    
    def get_test_mode_status(self) -> Dict[str, Any]:
        """Получает статус тестового режима"""
        return {
            "test_mode_enabled": self.test_mode,
            "environment": config.environment.value,
            "debug": config.debug,
            "timestamp": datetime.now().isoformat()
        }
    
    def set_test_mode(self, enabled: bool) -> Dict[str, Any]:
        """Устанавливает тестовый режим"""
        self.test_mode = enabled
        logger.info(f"Test mode {'enabled' if enabled else 'disabled'}")
        
        return {
            "test_mode_enabled": self.test_mode,
            "message": f"Test mode {'включен' if enabled else 'выключен'}",
            "timestamp": datetime.now().isoformat()
        }


class AdminService:
    """Сервис для админских функций"""
    
    def __init__(self):
        self.agent = AgentFactory.get_agent()
    
    async def reload_instructions(self) -> Dict[str, Any]:
        """Перезагружает инструкции из файла"""
        try:
            # Перезагружаем инструкции в самом агенте
            if hasattr(self.agent, 'reload_instructions'):
                self.agent.reload_instructions()
                logger.info("📝 Инструкции перезагружены в агенте")
            
            # Также перезагружаем в ResponseGenerator для совместимости
            from ..services.response_generator import HybridResponseGenerator
            if isinstance(self.agent.response_generator, HybridResponseGenerator):
                self.agent.response_generator._load_instructions()
                logger.info("📝 Инструкции перезагружены в HybridResponseGenerator")
                
            return {
                "success": True,
                "message": "Instructions reloaded successfully",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error reloading instructions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_user_memory(self, user_id: int) -> Dict[str, Any]:
        """Очищает память пользователя"""
        try:
            success = await self.agent.clear_user_memory(user_id)
            return {
                "success": success,
                "user_id": user_id,
                "message": "Memory cleared" if success else "Failed to clear memory",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error clearing memory for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Получает статистику бота"""
        service_manager = ServiceManager()
        
        return {
            "uptime": service_manager.get_uptime(),
            "start_time": service_manager.start_time.isoformat(),
            "services": service_manager.get_detailed_status(),
            "config": {
                "environment": config.environment.value,
                "debug": config.debug,
                "webhook_url": config.webhook.base_url
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def broadcast_message(
        self,
        message: str,
        user_ids: Optional[List[int]] = None,
        parse_mode: str = "HTML"
    ) -> Dict[str, Any]:
        """Отправляет сообщение пользователям"""
        if not user_ids:
            return {
                "success": False,
                "error": "No user IDs provided"
            }
        
        sent = 0
        failed = 0
        errors = []
        
        for user_id in user_ids:
            try:
                bot.send_message(user_id, message, parse_mode=parse_mode)
                sent += 1
            except Exception as e:
                failed += 1
                errors.append({"user_id": user_id, "error": str(e)})
        
        return {
            "success": sent > 0,
            "sent": sent,
            "failed": failed,
            "errors": errors[:10],  # Ограничиваем количество ошибок
            "timestamp": datetime.now().isoformat()
        }
    
    async def update_runtime_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет конфигурацию во время выполнения"""
        # Здесь можно реализовать обновление конфигурации
        # Но это временное решение, изменения не сохранятся после перезапуска
        
        return {
            "success": False,
            "error": "Runtime config update not implemented yet"
        }
    
    async def get_users_list(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Получает список пользователей"""
        # Здесь нужна интеграция с базой данных или Zep
        return {
            "users": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "User list not implemented yet"
        }
    
    async def manage_service(self, service_name: str, action: str) -> Dict[str, Any]:
        """Управляет сервисами"""
        # Здесь можно реализовать управление сервисами
        return {
            "success": False,
            "error": f"Service management for {service_name} not implemented yet"
        }


class TestService:
    """Сервис для тестирования"""
    
    def create_test_update(
        self,
        chat_id: int,
        text: str,
        user_id: int,
        username: Optional[str] = None,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """Создает тестовый update"""
        timestamp = int(time.time())
        
        return {
            "update_id": int(time.time() * 1000000),
            "message": {
                "message_id": int(time.time() * 1000),
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": f"Test User {user_id}",
                    "username": username or f"test_user_{user_id}"
                },
                "chat": {
                    "id": chat_id,
                    "first_name": f"Test User {user_id}",
                    "username": username or f"test_user_{user_id}",
                    "type": "private"
                },
                "date": timestamp,
                "text": text if message_type == "text" else None
            }
        }
    
    def create_test_voice_update(
        self,
        chat_id: int,
        file_id: str,
        user_id: int,
        duration: int = 5
    ) -> Dict[str, Any]:
        """Создает тестовый voice update"""
        base_update = self.create_test_update(chat_id, "", user_id)
        base_update["message"]["voice"] = {
            "duration": duration,
            "mime_type": "audio/ogg",
            "file_id": file_id,
            "file_unique_id": f"voice_{int(time.time())}",
            "file_size": duration * 1000
        }
        return base_update
    
    def create_test_business_update(
        self,
        chat_id: int,
        text: str,
        business_connection_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Создает тестовый business update"""
        timestamp = int(time.time())
        
        return {
            "update_id": int(time.time() * 1000000),
            "business_message": {
                "message_id": int(time.time() * 1000),
                "business_connection_id": business_connection_id,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": f"Business User {user_id}",
                    "username": f"business_user_{user_id}"
                },
                "chat": {
                    "id": chat_id,
                    "type": "private"
                },
                "date": timestamp,
                "text": text
            }
        }
    
    async def test_social_media(
        self,
        platform: str,
        url: str,
        user_id: int,
        action: str
    ) -> Dict[str, Any]:
        """Тестирует Social Media функциональность"""
        try:
            from ..services.social_media_service import social_media_service
            
            if not social_media_service:
                return {
                    "success": False,
                    "error": "Social Media service not available"
                }
            
            # Создаем тестовое сообщение
            test_message = f"/{platform} {url}"
            
            result = await social_media_service.process_message(
                test_message,
                user_id,
                f"Test User {user_id}"
            )
            
            return {
                "success": result.get("success", False),
                "platform": platform,
                "url": url,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_mcp(
        self,
        service: str,
        method: str,
        params: dict,
        user_id: int
    ) -> Dict[str, Any]:
        """Тестирует MCP функциональность"""
        try:
            if not config.mcp.enabled:
                return {
                    "success": False,
                    "error": "MCP not enabled"
                }
            
            # MCP тестирование теперь через Claude Code SDK
            return {
                "success": False,
                "error": "MCP testing through Claude Code SDK not implemented yet"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }