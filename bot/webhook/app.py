"""
Создание и конфигурация FastAPI приложения
"""

import logging
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core import config
from .middleware import SecurityMiddleware, LoggingMiddleware, ErrorHandlerMiddleware
from .routers import health, webhook, debug, admin, test

logger = logging.getLogger(__name__)


def create_app(title: Optional[str] = None, description: Optional[str] = None) -> FastAPI:
    """
    Создает и конфигурирует FastAPI приложение
    
    Args:
        title: Название приложения
        description: Описание приложения
        
    Returns:
        FastAPI: Сконфигурированное приложение
    """
    # Создаем приложение
    app = FastAPI(
        title=title or "🤖 Artyom Integrator Bot",
        description=description or "Webhook server для Telegram бота",
        version="2.0.0",
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None
    )
    
    # Добавляем middleware
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    
    # CORS для debug режима
    if config.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Подключаем роутеры
    app.include_router(health.router, tags=["Health"])
    app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
    app.include_router(debug.router, prefix="/debug", tags=["Debug"])
    app.include_router(admin.router, prefix="/admin", tags=["Admin"])
    app.include_router(test.router, prefix="/test", tags=["Test"])
    
    # Добавляем маршруты настройки
    from .setup_routes import register_setup_routes
    register_setup_routes(app)
    
    # События жизненного цикла
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 Webhook server starting...")
        
        # Проверяем, используется ли Cloudflare Tunnel
        if config.cloudflare_tunnel_token:
            logger.info("🌐 Используется Cloudflare Tunnel")
            from ..services.cloudflare_tunnel import cloudflare_tunnel
            
            # Устанавливаем webhook через Cloudflare
            success = await cloudflare_tunnel.setup_webhook(
                config.telegram_bot_token,
                config.webhook_secret_token
            )
            if success:
                logger.info("✅ Webhook установлен через Cloudflare Tunnel")
            else:
                logger.error("❌ Ошибка установки webhook через Cloudflare")
        
        # Fallback на обычную установку webhook
        elif hasattr(config, 'webhook') and hasattr(config.webhook, 'auto_setup') and config.webhook.auto_setup:
            from .services import WebhookService
            webhook_service = WebhookService()
            result = await webhook_service.setup_webhook()
            if result['success']:
                logger.info("✅ Webhook установлен автоматически")
            else:
                logger.error(f"❌ Ошибка установки webhook: {result['error']}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("👋 Webhook server shutting down...")
    
    return app