"""
Простой webhook сервер для тестирования
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException, status
import telebot
from telebot import types
import json

# Настройки из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "textil_pro_secret_2025")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

# Создаем бот
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(title="Simple Webhook Server")

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Simple Webhook Server",
        "bot_configured": bool(TELEGRAM_BOT_TOKEN)
    }

@app.get("/webhook/info")
async def webhook_info():
    """Webhook information endpoint"""
    try:
        webhook_info = bot.get_webhook_info()
        return {
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message
        }
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        return {"error": str(e)}

@app.post("/webhook/set")
async def set_webhook():
    """Set webhook URL"""
    try:
        # Получаем URL из Railway
        railway_url = os.getenv("RAILWAY_PUBLIC_URL")
        if railway_url:
            webhook_url = f"{railway_url}/webhook"
        else:
            # Пытаемся определить из заголовков
            webhook_url = "https://bot-production-472c.up.railway.app/webhook"
        
        result = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN
        )
        
        if result:
            logger.info(f"Webhook set successfully: {webhook_url}")
            return {"ok": True, "webhook_url": webhook_url}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def process_webhook(request: Request):
    """Process webhook updates"""
    try:
        json_data = await request.body()
        json_string = json_data.decode('utf-8')
        
        logger.info(f"Received webhook update: {json_string[:100]}...")
        
        # Парсим update
        update_dict = json.loads(json_string)
        
        # Простая обработка
        if "message" in update_dict:
            message = update_dict["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            if text:
                response = f"Получено сообщение: {text}"
                bot.send_message(chat_id, response)
                logger.info(f"Sent response to chat {chat_id}")
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 Starting Simple Webhook Server")
    
    # ВАЖНО: Удаляем webhook при старте чтобы избежать конфликтов
    try:
        bot.delete_webhook()
        logger.info("Webhook deleted on startup")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")
    
    try:
        bot_info = bot.get_me()
        logger.info(f"Bot info: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        
    # НЕ запускаем polling! Только webhook режим

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))