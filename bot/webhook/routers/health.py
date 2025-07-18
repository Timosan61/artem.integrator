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
                "admin": "/admin/*" if config.admin.enabled else None
            }
        }
    except Exception as e:
        return {
            "status": "🔴 ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/health")
async def detailed_health():
    """Детальная информация о здоровье сервиса"""
    service_manager = ServiceManager()
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": service_manager.get_uptime(),
        "services": {}
    }
    
    # Проверяем каждый сервис
    for service_name, status in service_manager.get_services_status().items():
        health_data["services"][service_name] = {
            "status": status,
            "healthy": status in ["✅ ENABLED", "✅ AVAILABLE"]
        }
    
    # Определяем общий статус
    if all(s["healthy"] for s in health_data["services"].values() if s["status"] != "❌ DISABLED"):
        health_data["status"] = "healthy"
    elif any(s["healthy"] for s in health_data["services"].values()):
        health_data["status"] = "degraded"
    else:
        health_data["status"] = "unhealthy"
    
    return health_data


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