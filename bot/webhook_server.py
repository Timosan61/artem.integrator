"""
FastAPI webhook server for Telegram Business API integration
"""

import os
import logging
from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
import telebot
from telebot import types
import json
import asyncio

from .config import TELEGRAM_BOT_TOKEN
from .business_handlers import handle_business_update

# Создаем синхронный бот для webhook
webhook_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки webhook
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "textil_pro_secret_2025")

# FastAPI приложение
app = FastAPI(
    title="Textil PRO Bot Webhook Server",
    description="Telegram Business API webhook endpoint",
    version="1.0.0"
)

@app.get("/")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "ok",
        "service": "Textil PRO Bot Webhook",
        "bot_username": os.getenv("BOT_USERNAME", "textilprofi_bot")
    }

@app.get("/webhook/info")
async def webhook_info():
    """Webhook information endpoint"""
    try:
        webhook_info = webhook_bot.get_webhook_info()
        return {
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections
        }
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        return {"error": str(e)}

@app.post(WEBHOOK_PATH)
async def process_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Main webhook endpoint for processing Telegram updates
    """
    try:
        # Проверяем secret token для безопасности
        if x_telegram_bot_api_secret_token != WEBHOOK_SECRET_TOKEN:
            logger.warning(f"Invalid secret token: {x_telegram_bot_api_secret_token}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid secret token"
            )
        
        # Получаем JSON данные от Telegram
        json_data = await request.body()
        json_string = json_data.decode('utf-8')
        
        logger.debug(f"Received webhook update: {json_string[:200]}...")
        
        # Парсим update объект
        update_dict = json.loads(json_string)
        update = types.Update.de_json(update_dict, webhook_bot)
        
        # Проверяем тип update
        if hasattr(update, 'business_connection') or hasattr(update, 'business_message'):
            # Обрабатываем Business API события
            await handle_business_update(update, webhook_bot)
        else:
            # Стандартная обработка сообщений
            webhook_bot.process_new_updates([update])
        
        logger.info(f"Successfully processed update {update.update_id}")
        return {"ok": True}
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/webhook/set")
async def set_webhook(webhook_url: str = None):
    """
    Utility endpoint to set webhook URL
    """
    try:
        if not webhook_url:
            # Автоматически определяем URL из Railway
            railway_url = os.getenv("RAILWAY_PUBLIC_URL")
            if railway_url:
                webhook_url = f"{railway_url}{WEBHOOK_PATH}"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Webhook URL not provided and RAILWAY_PUBLIC_URL not set"
                )
        
        # Устанавливаем webhook
        result = webhook_bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            allowed_updates=[
                "message", 
                "edited_message", 
                "callback_query",
                "business_connection",
                "business_message",
                "edited_business_message",
                "deleted_business_messages"
            ]
        )
        
        if result:
            logger.info(f"Webhook set successfully: {webhook_url}")
            return {
                "ok": True,
                "webhook_url": webhook_url,
                "secret_token": WEBHOOK_SECRET_TOKEN
            }
        else:
            logger.error("Failed to set webhook")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set webhook"
            )
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/webhook")
async def delete_webhook():
    """
    Delete webhook and switch back to polling
    """
    try:
        result = webhook_bot.delete_webhook()
        if result:
            logger.info("Webhook deleted successfully")
            return {"ok": True, "message": "Webhook deleted"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete webhook"
            )
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    logger.info("🚀 Starting Textil PRO Bot Webhook Server")
    logger.info(f"Bot token configured: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
    logger.info(f"Secret token: {'✅' if WEBHOOK_SECRET_TOKEN else '❌'}")
    
    # Проверяем состояние бота
    try:
        bot_info = webhook_bot.get_me()
        logger.info(f"Bot info: @{bot_info.username} ({bot_info.first_name})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Textil PRO Bot Webhook Server")

if __name__ == "__main__":
    import uvicorn
    
    # Запуск для разработки
    uvicorn.run(
        "bot.webhook_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )