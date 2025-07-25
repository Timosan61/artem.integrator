"""
Health check endpoints
"""

from fastapi import APIRouter
from datetime import datetime

from ...core.config import config
from ...telegram_bot import bot
from ..services import ServiceManager

router = APIRouter()


@router.get("/")
async def health_check():
    """Основной health check endpoint"""
    try:
        bot_info = bot.get_me()
        service_manager = ServiceManager()
        
        return {
            "status": "🟢 ONLINE",
            "service": "Artyom Integrator Webhook",
            "bot": f"@{bot_info.username}",
            "bot_id": bot_info.id,
            "mode": "WEBHOOK",
            "timestamp": datetime.now().isoformat(),
            "environment": config.environment.value,
            "services": service_manager.get_services_status(),
            "endpoints": {
                "webhook_info": "/webhook/info",
                "set_webhook": "/webhook/set",
                "delete_webhook": "/webhook (DELETE method)",
                "debug": "/debug/*" if config.debug else None,
                "admin": "/admin/*" if (config.admin.user_ids or config.admin.usernames) else None
            }
        }
    except Exception as e:
        return {
            "status": "🔴 ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/health")
async def railway_health():
    """Упрощённый healthcheck для Railway"""
    try:
        # Простая проверка - только Telegram бот
        bot.get_me()
        
        return {
            "status": "healthy",
            "service": "Artyom Integrator",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/health/detailed")
async def detailed_health():
    """Детальная информация о здоровье сервиса"""
    try:
        service_manager = ServiceManager()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": service_manager.get_uptime(),
            "services": {}
        }
        
        # Проверяем каждый сервис с детальной информацией
        services_status = service_manager.get_services_status()
        for service_name, status in services_status.items():
            health_data["services"][service_name] = {
                "status": status,
                "healthy": status in ["✅ ENABLED", "✅ AVAILABLE", "✅ CONNECTED"]
            }
        
        # Определяем общий статус
        critical_services = ["telegram", "agent"]  # Критичные сервисы
        critical_healthy = all(
            health_data["services"][service]["healthy"] 
            for service in critical_services 
            if service in health_data["services"]
        )
        
        if critical_healthy:
            health_data["status"] = "healthy"
        elif any(s["healthy"] for s in health_data["services"].values()):
            health_data["status"] = "degraded"
        else:
            health_data["status"] = "unhealthy"
        
        # Добавляем дополнительную диагностическую информацию
        health_data["diagnostics"] = _get_health_diagnostics(service_manager)
        
        return health_data
        
    except Exception as e:
        # Возвращаем ошибку с максимальной информацией для диагностики
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "error_type": type(e).__name__
        }


def _get_health_diagnostics(service_manager: ServiceManager) -> dict:
    """Получает дополнительную диагностическую информацию"""
    try:
        return {
            "telegram_bot_info": _get_telegram_info(),
            "config_status": _get_config_status(),
            "python_info": {
                "version": f"{config.environment.value}",
                "debug": config.debug
            }
        }
    except Exception as e:
        return {"error": str(e)}


def _get_telegram_info() -> dict:
    """Получает информацию о Telegram боте"""
    try:
        bot_info = bot.get_me()
        return {
            "bot_username": bot_info.username,
            "bot_id": bot_info.id,
            "can_join_groups": bot_info.can_join_groups,
            "can_read_all_group_messages": bot_info.can_read_all_group_messages,
            "supports_inline_queries": bot_info.supports_inline_queries
        }
    except Exception as e:
        return {"error": str(e)}


def _get_config_status() -> dict:
    """Получает статус основных конфигураций"""
    return {
        "openai_enabled": config.openai.enabled,
        "anthropic_enabled": config.anthropic.enabled,
        "voice_enabled": config.voice.enabled,
        "mcp_enabled": config.mcp.enabled,
        "zep_enabled": config.zep.enabled,
        "environment": config.environment.value,
        "webhook_base_url": config.webhook.base_url is not None
    }


@router.get("/ready")
async def readiness_check():
    """Проверка готовности сервиса"""
    try:
        # Проверяем подключение к Telegram
        bot.get_me()
        
        # Проверяем критичные сервисы
        service_manager = ServiceManager()
        critical_services = ["telegram", "agent"]
        
        for service in critical_services:
            if not service_manager.is_service_healthy(service):
                return {
                    "ready": False,
                    "reason": f"Service {service} is not healthy"
                }
        
        return {"ready": True}
        
    except Exception as e:
        return {
            "ready": False,
            "reason": str(e)
        }


@router.get("/live")
async def liveness_check():
    """Простая проверка что сервис жив"""
    return {"alive": True, "timestamp": datetime.now().isoformat()}