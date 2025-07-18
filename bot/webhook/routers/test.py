"""
Test endpoints для тестирования функциональности
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from ...core.config import config
from ..services import TestService

router = APIRouter()

# Включаем только в debug/test режиме
if config.environment.value == "production" and not config.debug:
    router = APIRouter()  # Пустой роутер в production


@router.post("/message")
async def test_message(
    chat_id: int,
    text: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    message_type: str = "text"
):
    """Тестовая отправка сообщения боту"""
    test_service = TestService()
    
    # Создаем тестовый update
    test_update = test_service.create_test_update(
        chat_id=chat_id,
        text=text,
        user_id=user_id or chat_id,
        username=username,
        message_type=message_type
    )
    
    # Обрабатываем через handler
    from ..handlers import webhook_handler
    result = await webhook_handler.handle_update(test_update)
    
    return result


@router.post("/voice")
async def test_voice(
    chat_id: int,
    file_id: str,
    user_id: Optional[int] = None,
    duration: int = 5
):
    """Тестовая отправка голосового сообщения"""
    test_service = TestService()
    
    # Создаем тестовый voice update
    test_update = test_service.create_test_voice_update(
        chat_id=chat_id,
        file_id=file_id,
        user_id=user_id or chat_id,
        duration=duration
    )
    
    # Обрабатываем через handler
    from ..handlers import webhook_handler
    result = await webhook_handler.handle_update(test_update)
    
    return result


@router.post("/business-message")
async def test_business_message(
    chat_id: int,
    text: str,
    business_connection_id: str,
    user_id: Optional[int] = None
):
    """Тестовая отправка Business API сообщения"""
    test_service = TestService()
    
    # Создаем тестовый business update
    test_update = test_service.create_test_business_update(
        chat_id=chat_id,
        text=text,
        business_connection_id=business_connection_id,
        user_id=user_id or chat_id
    )
    
    # Обрабатываем через handler
    from ..handlers import webhook_handler
    result = await webhook_handler.handle_update(test_update)
    
    return result


@router.post("/social-media")
async def test_social_media(
    platform: str,
    url: str,
    user_id: int,
    action: str = "analyze"
):
    """Тестировать Social Media функциональность"""
    if platform not in ["youtube", "instagram", "tiktok"]:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    test_service = TestService()
    result = await test_service.test_social_media(
        platform=platform,
        url=url,
        user_id=user_id,
        action=action
    )
    
    return result


@router.post("/mcp")
async def test_mcp(
    service: str,
    method: str,
    params: dict,
    user_id: int
):
    """Тестировать MCP функциональность"""
    test_service = TestService()
    result = await test_service.test_mcp(
        service=service,
        method=method,
        params=params,
        user_id=user_id
    )
    
    return result


@router.get("/echo")
async def echo(message: str = "Hello, World!"):
    """Простой echo endpoint для проверки"""
    return {
        "echo": message,
        "reversed": message[::-1],
        "length": len(message),
        "config_ok": bool(config.telegram.bot_token)
    }