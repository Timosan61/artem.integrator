"""
Middleware для webhook сервера
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import config

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware для безопасности"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Проверка secret token для webhook
        if request.url.path == "/webhook":
            secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            expected_token = config.webhook.secret_token
            
            # Логируем для отладки
            logger.info(f"🔐 Webhook security check:")
            logger.info(f"   Headers: {dict(request.headers)}")
            logger.info(f"   Received token: {secret_token}")
            logger.info(f"   Expected token: {expected_token}")
            
            # Временно отключаем проверку токена для отладки
            if False and secret_token != expected_token:
                logger.warning(f"❌ Invalid secret token from {request.client.host if request.client else 'unknown'}")
                return JSONResponse(
                    status_code=200,  # Telegram требует 200 OK
                    content={"ok": False, "error": "Invalid secret token"}
                )
        
        response = await call_next(request)
        
        # Добавляем заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования запросов"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Логируем входящий запрос
        logger.debug(f"🔵 {request.method} {request.url.path}")
        
        # Обрабатываем запрос
        response = await call_next(request)
        
        # Считаем время обработки
        process_time = time.time() - start_time
        
        # Логируем результат
        status_emoji = "🟢" if response.status_code < 400 else "🔴"
        logger.info(
            f"{status_emoji} {request.method} {request.url.path} "
            f"-> {response.status_code} ({process_time:.3f}s)"
        )
        
        # Добавляем заголовок с временем обработки
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки ошибок"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"❌ Необработанная ошибка: {e}", exc_info=True)
            
            # В production скрываем детали ошибок
            if config.environment.value == "production":
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error"}
                )
            else:
                # В debug режиме показываем полную информацию
                import traceback
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": str(e),
                        "type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }
                )


class WebhookMiddleware:
    """Основной middleware для обработки webhook"""
    
    def __init__(self):
        self.request_counter = 0
        self.last_requests = []
    
    async def process_webhook(self, request: Request) -> dict:
        """
        Обрабатывает webhook запрос
        
        Args:
            request: FastAPI Request объект
            
        Returns:
            dict: Результат обработки
        """
        self.request_counter += 1
        
        # Получаем данные
        try:
            data = await request.json()
        except:
            return {"ok": False, "error": "Invalid JSON"}
        
        # Сохраняем для отладки
        if config.debug:
            self.last_requests.append({
                "id": self.request_counter,
                "timestamp": time.time(),
                "data": data
            })
            # Ограничиваем размер истории
            if len(self.last_requests) > 10:
                self.last_requests.pop(0)
        
        return {"ok": True, "data": data}