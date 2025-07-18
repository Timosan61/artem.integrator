"""
Debug endpoints для разработки и диагностики
"""

import os
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime

from ...core.config import config
from ..handlers import webhook_handler
from ..services import ServiceManager, DebugService

router = APIRouter()

# Включаем только в debug режиме
if not config.debug:
    router = APIRouter()  # Пустой роутер в production


@router.get("/last-updates")
async def get_last_updates():
    """Получить последние обработанные updates"""
    return {
        "total_updates": webhook_handler.update_counter,
        "last_updates": webhook_handler.last_updates,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/service-status")
async def get_service_status():
    """Получить статус всех сервисов"""
    service_manager = ServiceManager()
    return service_manager.get_detailed_status()


@router.get("/config")
async def get_config():
    """Получить текущую конфигурацию (без секретов)"""
    return config.get_safe_config()


@router.get("/logs/recent")
async def get_recent_logs(lines: int = 50):
    """Получить последние строки из лог файла"""
    debug_service = DebugService()
    return debug_service.get_recent_logs(lines)


@router.get("/memory/{user_id}")
async def get_user_memory(user_id: int):
    """Получить память пользователя"""
    from ...core.agent import AgentFactory
    agent = AgentFactory.get_agent()
    
    try:
        context = await agent.memory_manager.get_context(user_id)
        summary = await agent.memory_manager.get_session_summary(user_id)
        
        return {
            "user_id": user_id,
            "context_size": len(context),
            "context": context,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-status")
async def get_agent_status():
    """Получить статус AI агента"""
    from ...core.agent import AgentFactory
    agent = AgentFactory.get_agent()
    
    return await agent.get_agent_status()


@router.get("/test-mode-status")
async def get_test_mode_status():
    """Получить статус тестового режима"""
    debug_service = DebugService()
    return debug_service.get_test_mode_status()


@router.post("/test-mode/{action}")
async def toggle_test_mode(action: str):
    """Включить/выключить тестовый режим"""
    if action not in ["enable", "disable"]:
        raise HTTPException(status_code=400, detail="Action must be 'enable' or 'disable'")
    
    debug_service = DebugService()
    result = debug_service.set_test_mode(action == "enable")
    
    return result


@router.get("/environment")
async def get_environment():
    """Получить информацию об окружении"""
    return {
        "environment": config.environment.value,
        "debug": config.debug,
        "python_version": os.sys.version,
        "working_directory": os.getcwd(),
        "env_vars": {
            key: "***" if any(secret in key.lower() for secret in ["key", "token", "secret", "password"]) else value
            for key, value in os.environ.items()
            if key.startswith("BOT_") or key.startswith("TELEGRAM_") or key.startswith("OPENAI_")
        }
    }


@router.post("/clear-cache")
async def clear_cache():
    """Очистить все кеши"""
    from ...core.utils import CacheUtils
    CacheUtils.clear_all()
    
    return {"status": "Cache cleared", "timestamp": datetime.now().isoformat()}