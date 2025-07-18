"""
Admin endpoints для управления ботом
"""

import json
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional

from ...core.config import config
from ...auth import is_admin_token
from ..services import AdminService

router = APIRouter()

# Admin authentication dependency
async def verify_admin(x_admin_token: Optional[str] = Header(None)):
    """Проверяет админский токен"""
    if not (config.admin.user_ids or config.admin.usernames):
        raise HTTPException(status_code=404, detail="Admin endpoints disabled")
    
    if not is_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    return True


@router.post("/reload-prompt", dependencies=[Depends(verify_admin)])
async def reload_prompt():
    """Перезагрузить инструкции из файла"""
    admin_service = AdminService()
    result = await admin_service.reload_instructions()
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=500, detail=result['error'])


@router.post("/clear-memory/{user_id}", dependencies=[Depends(verify_admin)])
async def clear_user_memory(user_id: int):
    """Очистить память конкретного пользователя"""
    admin_service = AdminService()
    result = await admin_service.clear_user_memory(user_id)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=500, detail=result['error'])


@router.get("/stats", dependencies=[Depends(verify_admin)])
async def get_stats():
    """Получить статистику бота"""
    admin_service = AdminService()
    return await admin_service.get_bot_stats()


@router.post("/broadcast", dependencies=[Depends(verify_admin)])
async def broadcast_message(
    message: str,
    user_ids: Optional[list] = None,
    parse_mode: str = "HTML"
):
    """Отправить сообщение пользователям"""
    admin_service = AdminService()
    result = await admin_service.broadcast_message(
        message=message,
        user_ids=user_ids,
        parse_mode=parse_mode
    )
    
    return result


@router.post("/update-config", dependencies=[Depends(verify_admin)])
async def update_config(updates: dict):
    """Обновить конфигурацию (временно, до перезапуска)"""
    admin_service = AdminService()
    result = await admin_service.update_runtime_config(updates)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=400, detail=result['error'])


@router.get("/users", dependencies=[Depends(verify_admin)])
async def list_users(limit: int = 100, offset: int = 0):
    """Получить список пользователей"""
    admin_service = AdminService()
    return await admin_service.get_users_list(limit, offset)


@router.post("/service/{service_name}/{action}", dependencies=[Depends(verify_admin)])
async def manage_service(service_name: str, action: str):
    """Управление сервисами (enable/disable/restart)"""
    if action not in ["enable", "disable", "restart"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    admin_service = AdminService()
    result = await admin_service.manage_service(service_name, action)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=500, detail=result['error'])