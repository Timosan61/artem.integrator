"""
Webhook management endpoints
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from typing import Optional

from ...core.config import config
from ..handlers import webhook_handler
from ..services import WebhookService

router = APIRouter()
logger = logging.getLogger(__name__)

# Создаем сервис
webhook_service = WebhookService()


@router.post("")
async def webhook_endpoint(request: Request):
    """Основной webhook endpoint для приема updates от Telegram"""
    try:
        # Получаем данные
        update = await request.json()
        
        # Логируем входящий update
        logger.info(f"📥 Received update: {update}")
        
        # Обрабатываем update
        result = await webhook_handler.handle_update(update)
        
        # Логируем результат
        logger.info(f"📤 Response: {result}")
        
        # Telegram требует всегда возвращать 200 OK
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка в webhook: {e}", exc_info=True)
        # Все равно возвращаем 200 OK для Telegram
        return {"ok": False, "error": str(e)}


@router.get("/info")
async def get_webhook_info():
    """Получить информацию о текущем webhook"""
    return await webhook_service.get_webhook_info()


@router.get("/set")
async def set_webhook_browser():
    """Установить webhook (GET для браузера)"""
    return await webhook_service.setup_webhook()


@router.post("/set")
async def set_webhook(
    url: Optional[str] = None,
    secret_token: Optional[str] = None
):
    """Установить webhook с кастомными параметрами"""
    return await webhook_service.setup_webhook(
        custom_url=url,
        custom_secret=secret_token
    )


@router.delete("")
async def delete_webhook():
    """Удалить webhook"""
    return await webhook_service.delete_webhook()


@router.post("/update-settings")
async def update_webhook_settings(
    allowed_updates: Optional[list] = None,
    max_connections: Optional[int] = None,
    drop_pending_updates: bool = False
):
    """Обновить настройки webhook"""
    current_info = await webhook_service.get_webhook_info()
    
    if not current_info.get('webhook_url'):
        raise HTTPException(status_code=400, detail="Webhook not set")
    
    # Переустанавливаем webhook с новыми параметрами
    return await webhook_service.setup_webhook(
        allowed_updates=allowed_updates,
        max_connections=max_connections,
        drop_pending_updates=drop_pending_updates
    )