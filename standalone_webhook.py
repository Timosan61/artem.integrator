"""
Standalone webhook сервер для Telegram Business API
Полностью изолирован от остального кода
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException
import telebot
import json

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "textil_pro_secret_2025")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

# === СОЗДАНИЕ БОТА ===
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === FASTAPI ПРИЛОЖЕНИЕ ===
app = FastAPI(title="Standalone Telegram Webhook")

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        bot_info = bot.get_me()
        return {
            "status": "✅ OK",
            "service": "Standalone Telegram Webhook",
            "bot": f"@{bot_info.username}",
            "bot_id": bot_info.id
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "❌ ERROR", 
            "error": str(e)
        }

@app.get("/webhook/info")
async def webhook_info():
    """Получить информацию о webhook"""
    try:
        info = bot.get_webhook_info()
        return {
            "webhook_url": info.url or "❌ Не установлен",
            "pending_updates": info.pending_update_count,
            "last_error": info.last_error_message or "Нет ошибок",
            "has_custom_certificate": info.has_custom_certificate,
            "allowed_updates": info.allowed_updates
        }
    except Exception as e:
        logger.error(f"Ошибка получения webhook info: {e}")
        return {"error": str(e)}

@app.post("/webhook/set")
async def set_webhook():
    """Установить webhook"""
    try:
        # Определяем URL для webhook
        webhook_url = "https://bot-production-472c.up.railway.app/webhook"
        
        # Устанавливаем webhook
        result = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            allowed_updates=[
                "message", 
                "business_connection",
                "business_message"
            ]
        )
        
        if result:
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return {
                "status": "✅ SUCCESS",
                "webhook_url": webhook_url,
                "secret_token": "✅ Настроен"
            }
        else:
            return {"status": "❌ FAILED", "error": "set_webhook returned False"}
            
    except Exception as e:
        logger.error(f"Ошибка установки webhook: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

@app.delete("/webhook")
async def delete_webhook():
    """Удалить webhook"""
    try:
        result = bot.delete_webhook()
        if result:
            logger.info("✅ Webhook удален")
            return {"status": "✅ Webhook удален"}
        else:
            return {"status": "❌ Ошибка удаления"}
    except Exception as e:
        logger.error(f"Ошибка удаления webhook: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

@app.post("/webhook")
async def process_webhook(request: Request):
    """Обработка webhook от Telegram"""
    try:
        # Получаем данные
        json_data = await request.body()
        json_string = json_data.decode('utf-8')
        
        logger.info(f"📨 Получен webhook: {json_string[:100]}...")
        
        # Парсим update
        update_dict = json.loads(json_string)
        
        # === ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ ===
        if "message" in update_dict:
            message = update_dict["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user_name = message.get("from", {}).get("first_name", "Пользователь")
            
            if text:
                response = f"🤖 Привет, {user_name}! Получил сообщение: {text}"
                bot.send_message(chat_id, response)
                logger.info(f"✅ Ответил в чат {chat_id}")
        
        # === ОБРАБОТКА BUSINESS СООБЩЕНИЙ ===
        elif "business_message" in update_dict:
            bus_msg = update_dict["business_message"]
            chat_id = bus_msg["chat"]["id"]
            text = bus_msg.get("text", "")
            business_connection_id = bus_msg.get("business_connection_id")
            user_name = bus_msg.get("from", {}).get("first_name", "Клиент")
            
            if text and business_connection_id:
                response = f"💼 Привет, {user_name}! Ваше сообщение получено через Business API: {text}"
                bot.send_message(
                    chat_id=chat_id,
                    text=response,
                    business_connection_id=business_connection_id
                )
                logger.info(f"✅ Business ответ отправлен в чат {chat_id}")
        
        # === ОБРАБОТКА BUSINESS CONNECTION ===
        elif "business_connection" in update_dict:
            connection = update_dict["business_connection"]
            is_enabled = connection.get("is_enabled", False)
            user_name = connection.get("user", {}).get("first_name", "Пользователь")
            
            if is_enabled:
                logger.info(f"✅ Подключен к Business аккаунту: {user_name}")
            else:
                logger.info(f"❌ Отключен от Business аккаунта: {user_name}")
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        return {"ok": False, "error": str(e)}

@app.on_event("startup")
async def startup():
    """Инициализация при запуске"""
    logger.info("🚀 Запуск Standalone Telegram Webhook Server")
    
    # Удаляем webhook при старте чтобы избежать конфликтов
    try:
        bot.delete_webhook()
        logger.info("🧹 Webhook очищен при старте")
    except:
        pass
    
    try:
        bot_info = bot.get_me()
        logger.info(f"🤖 Бот готов: @{bot_info.username} ({bot_info.first_name})")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации бота: {e}")

@app.on_event("shutdown") 
async def shutdown():
    """Очистка при остановке"""
    logger.info("🛑 Остановка Standalone Webhook Server")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🌐 Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)