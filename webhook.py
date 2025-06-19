"""
🤖 Telegram Business Bot Webhook Server
Единственная точка входа - БЕЗ polling режима!
Updated: 2025-06-19 10:00 - Added GET endpoint for webhook/set
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException
import telebot
import json

print("🚀 Загрузка Telegram Business Bot Webhook Server...")

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "textil_pro_secret_2025")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN отсутствует!")

print(f"✅ Токен бота получен: {TELEGRAM_BOT_TOKEN[:20]}...")

# === СОЗДАНИЕ СИНХРОННОГО БОТА (НЕ ASYNC!) ===
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === FASTAPI ПРИЛОЖЕНИЕ ===
app = FastAPI(
    title="🤖 Telegram Business Bot", 
    description="Webhook-only режим для Telegram Business API"
)

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        bot_info = bot.get_me()
        return {
            "status": "🟢 ONLINE", 
            "service": "Telegram Business Bot Webhook",
            "bot": f"@{bot_info.username}",
            "bot_id": bot_info.id,
            "mode": "WEBHOOK_ONLY",
            "endpoints": {
                "webhook_info": "/webhook/info",
                "set_webhook": "/webhook/set",
                "delete_webhook": "/webhook (DELETE method)"
            },
            "hint": "Используйте /webhook/set в браузере для установки webhook"
        }
    except Exception as e:
        return {"status": "🔴 ERROR", "error": str(e)}

@app.get("/webhook/info")
async def webhook_info():
    """Информация о webhook"""
    try:
        info = bot.get_webhook_info()
        return {
            "webhook_url": info.url or "❌ Не установлен",
            "pending_updates": info.pending_update_count,
            "last_error": info.last_error_message or "✅ Нет ошибок",
            "has_custom_certificate": info.has_custom_certificate,
            "allowed_updates": info.allowed_updates or ["все"]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/webhook/set")
async def set_webhook_get():
    """Установка webhook через GET (для браузера)"""
    return await set_webhook()

@app.post("/webhook/set")
async def set_webhook():
    """Установка webhook"""
    try:
        webhook_url = "https://bot-production-472c.up.railway.app/webhook"
        
        result = bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            allowed_updates=[
                "message",
                "business_connection", 
                "business_message",
                "edited_business_message",
                "deleted_business_messages"
            ]
        )
        
        if result:
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return {
                "status": "✅ SUCCESS",
                "webhook_url": webhook_url,
                "secret_token": "✅ Настроен",
                "allowed_updates": "✅ Business API включен"
            }
        else:
            return {"status": "❌ FAILED"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

@app.delete("/webhook")
async def delete_webhook():
    """Удаление webhook"""
    try:
        result = bot.delete_webhook()
        return {"status": "✅ Webhook удален" if result else "❌ Ошибка"}
    except Exception as e:
        return {"status": "❌ ERROR", "error": str(e)}

@app.post("/webhook")
async def process_webhook(request: Request):
    """Главный обработчик webhook"""
    try:
        json_data = await request.body()
        json_string = json_data.decode('utf-8')
        
        logger.info(f"📨 Webhook получен: {json_string[:150]}...")
        
        update_dict = json.loads(json_string)
        
        # === ОБЫЧНЫЕ СООБЩЕНИЯ ===
        if "message" in update_dict:
            msg = update_dict["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            user_name = msg.get("from", {}).get("first_name", "Пользователь")
            
            if text.startswith("/start"):
                response = f"🤖 Привет, {user_name}! Я Textil PRO бот.\n\n✅ Работаю через webhook\n💼 Поддерживаю Business API\n\nНапишите ваш вопрос!"
            elif text.startswith("/help"):
                response = "ℹ️ Помощь:\n/start - начать\n/help - помощь\n\nПросто напишите вопрос и я отвечу!"
            elif text:
                response = f"💬 {user_name}, получил сообщение: {text}\n\n🤖 Скоро здесь будет AI ответ!"
            else:
                response = "📎 Спасибо за файл! Пока работаю только с текстом."
                
            bot.send_message(chat_id, response)
            logger.info(f"✅ Ответ отправлен в чат {chat_id}")
        
        # === BUSINESS СООБЩЕНИЯ ===
        elif "business_message" in update_dict:
            bus_msg = update_dict["business_message"]
            chat_id = bus_msg["chat"]["id"]
            text = bus_msg.get("text", "")
            business_connection_id = bus_msg.get("business_connection_id")
            user_name = bus_msg.get("from", {}).get("first_name", "Клиент")
            
            if text and business_connection_id:
                response = f"💼 Здравствуйте, {user_name}!\n\n✅ Ваше сообщение получено через Business API: {text}\n\n🤖 Наш специалист скоро ответит!"
                bot.send_message(
                    chat_id=chat_id,
                    text=response,
                    business_connection_id=business_connection_id
                )
                logger.info(f"✅ Business ответ отправлен в чат {chat_id}")
        
        # === BUSINESS CONNECTION ===
        elif "business_connection" in update_dict:
            conn = update_dict["business_connection"]
            is_enabled = conn.get("is_enabled", False)
            user_name = conn.get("user", {}).get("first_name", "Пользователь")
            
            status = "✅ Подключен" if is_enabled else "❌ Отключен"
            logger.info(f"{status} к Business аккаунту: {user_name}")
        
        return {"ok": True, "status": "processed"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return {"ok": False, "error": str(e)}

@app.on_event("startup")
async def startup():
    """Запуск сервера"""
    print("\n" + "="*50)
    print("🚀 TELEGRAM BUSINESS BOT WEBHOOK SERVER")
    print("="*50)
    
    # Очищаем webhook при старте
    try:
        bot.delete_webhook()
        print("🧹 Webhook очищен")
    except:
        pass
    
    try:
        bot_info = bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        print(f"📊 ID: {bot_info.id}")
        print(f"📛 Имя: {bot_info.first_name}")
        print("🔗 Режим: WEBHOOK ONLY")
        print("❌ Polling: ОТКЛЮЧЕН")
        print("="*50)
        logger.info("✅ Бот инициализирован успешно")
        
        # Автоматически устанавливаем webhook при старте
        if os.getenv("AUTO_SET_WEBHOOK", "false").lower() == "true":
            print("🔧 Автоматическая установка webhook...")
            await set_webhook()
            
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        logger.error(f"❌ Ошибка инициализации бота: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Остановка сервера"""
    logger.info("🛑 Остановка Telegram Business Bot Webhook Server")
    print("🛑 Сервер остановлен")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)