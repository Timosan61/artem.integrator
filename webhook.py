"""
🤖 Telegram Business Bot Webhook Server
Единственная точка входа - БЕЗ polling режима!
Updated: 2025-06-19 10:45 - Auto webhook setup + better error handling
"""

import os
import sys
import logging
import traceback
from fastapi import FastAPI, Request, HTTPException
import telebot
import json
import asyncio

# Добавляем путь для импорта модулей бота
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Загрузка Telegram Business Bot Webhook Server...")

# Пытаемся импортировать AI agent
try:
    import bot
    print("✅ Модуль bot найден")
    from bot.agent import agent
    print("✅ AI Agent загружен успешно")
    AI_ENABLED = True
except ImportError as e:
    print(f"⚠️ AI Agent не доступен: {e}")
    print(f"📁 Текущая директория: {os.getcwd()}")
    print(f"📁 Файлы в директории: {os.listdir('.')}")
    if os.path.exists('bot'):
        print(f"📁 Файлы в bot/: {os.listdir('bot')}")
    AI_ENABLED = False
except Exception as e:
    print(f"❌ Ошибка загрузки AI Agent: {e}")
    AI_ENABLED = False

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
            "ai_status": "✅ ENABLED" if AI_ENABLED else "❌ DISABLED",
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
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
        # Проверяем secret token из заголовков
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token != WEBHOOK_SECRET_TOKEN:
            logger.warning(f"❌ Неверный secret token: {secret_token}")
            return {"ok": False, "error": "Invalid secret token"}
        
        json_data = await request.body()
        json_string = json_data.decode('utf-8')
        
        logger.info(f"📨 Webhook получен: {json_string[:150]}...")
        print(f"📨 Обработка webhook update...")
        
        update_dict = json.loads(json_string)
        
        # === ОБЫЧНЫЕ СООБЩЕНИЯ ===
        if "message" in update_dict:
            msg = update_dict["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            user_id = msg.get("from", {}).get("id", "unknown")
            user_name = msg.get("from", {}).get("first_name", "Пользователь")
            
            try:
                # Отправляем индикатор набора текста
                bot.send_chat_action(chat_id, 'typing')
                
                if text.startswith("/start"):
                    if AI_ENABLED:
                        response = agent.get_welcome_message()
                    else:
                        response = f"🤖 Привет, {user_name}! Я Textil PRO бот.\n\n✅ Работаю через webhook\n💼 Поддерживаю Business API\n\nНапишите ваш вопрос!"
                
                elif text.startswith("/help"):
                    response = """ℹ️ Помощь:
/start - начать работу
/help - показать помощь

Просто напишите ваш вопрос о текстильном производстве, и я с радостью помогу!

📞 Для срочных вопросов: +86 123 456 789"""
                
                elif text and AI_ENABLED:
                    # Используем AI для генерации ответа
                    try:
                        session_id = f"user_{user_id}"
                        response = await agent.generate_response(text, session_id)
                    except Exception as ai_error:
                        logger.error(f"Ошибка AI генерации: {ai_error}")
                        response = f"Извините, произошла ошибка AI. Ваш вопрос: {text}\n\nПопробуйте позже или свяжитесь с поддержкой."
                    
                elif text:
                    # Fallback если AI не доступен
                    response = f"💬 {user_name}, получил ваш вопрос: {text}\n\n📞 Для детальной консультации свяжитесь с нашими специалистами."
                else:
                    response = "📎 Спасибо за файл! Я работаю только с текстовыми сообщениями."
                    
                # Отправляем без parse_mode для надежности
                bot.send_message(chat_id, response)
                logger.info(f"✅ Ответ отправлен в чат {chat_id}")
                print(f"✅ Отправлен ответ пользователю {user_name}")
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
                bot.send_message(chat_id, "Извините, произошла ошибка. Попробуйте позже.")
        
        # === BUSINESS СООБЩЕНИЯ ===
        elif "business_message" in update_dict:
            bus_msg = update_dict["business_message"]
            chat_id = bus_msg["chat"]["id"]
            text = bus_msg.get("text", "")
            user_id = bus_msg.get("from", {}).get("id", "unknown")
            business_connection_id = bus_msg.get("business_connection_id")
            user_name = bus_msg.get("from", {}).get("first_name", "Клиент")
            
            # Логируем business_connection_id для отладки
            logger.info(f"📊 Business message - connection_id: '{business_connection_id}' (тип: {type(business_connection_id)})")
            
            # Проверяем наличие business_connection_id
            if not business_connection_id:
                logger.warning(f"⚠️ Business message без connection_id от {user_name} ({user_id})")
            
            # Обрабатываем ВСЕ business сообщения с текстом
            if text:
                try:
                    bot.send_chat_action(chat_id, 'typing')
                    
                    if AI_ENABLED:
                        # Используем AI для Business сообщений
                        session_id = f"business_{user_id}"
                        response = await agent.generate_response(text, session_id)
                    else:
                        response = f"💼 Здравствуйте, {user_name}!\n\n✅ Ваше сообщение получено через Business API: {text}\n\n🤖 Наш специалист скоро ответит!"
                    
                    # ВСЕГДА отправляем business_message с business_connection_id
                    # Это критично для работы Business API
                    bot.send_message(
                        chat_id=chat_id,
                        text=response,
                        business_connection_id=business_connection_id
                    )
                    logger.info(f"✅ Business ответ отправлен в чат {chat_id} с connection_id='{business_connection_id}'")
                    
                    print(f"✅ Business ответ отправлен пользователю {user_name}")
                    
                except Exception as e:
                    # Детальное логирование ошибки с traceback
                    logger.error(f"❌ Ошибка обработки business сообщения: {e}")
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
                    logger.error(f"Business connection_id: '{business_connection_id}'")
                    
                    # ВАЖНО: Отправляем ошибку ТОЖЕ через Business API!
                    try:
                        error_message = "Извините, произошла временная ошибка. Пожалуйста, попробуйте позже или обратитесь к нашему менеджеру."
                        
                        # Если есть business_connection_id - используем его
                        if business_connection_id:
                            bot.send_message(
                                chat_id=chat_id,
                                text=error_message,
                                business_connection_id=business_connection_id
                            )
                            logger.info(f"✅ Сообщение об ошибке отправлено через Business API")
                        else:
                            # Fallback: если нет connection_id, отправляем обычное сообщение
                            bot.send_message(chat_id, error_message)
                            logger.warning(f"⚠️ Сообщение об ошибке отправлено БЕЗ Business API (нет connection_id)")
                            
                    except Exception as send_error:
                        logger.error(f"❌ Не удалось отправить сообщение об ошибке: {send_error}")
        
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
        print(f"🤖 AI: {'✅ ВКЛЮЧЕН' if AI_ENABLED else '❌ ОТКЛЮЧЕН'}")
        print(f"🔑 OpenAI API: {'✅ Настроен' if os.getenv('OPENAI_API_KEY') else '❌ Не настроен'}")
        print("="*50)
        logger.info("✅ Бот инициализирован успешно")
        
        # ВСЕГДА автоматически устанавливаем webhook при старте
        print("🔧 Автоматическая установка webhook...")
        try:
            # Сначала проверяем текущий статус
            current_webhook = bot.get_webhook_info()
            if current_webhook.url:
                print(f"📍 Текущий webhook: {current_webhook.url}")
            else:
                print("❌ Webhook не установлен")
            
            # Устанавливаем webhook
            webhook_url = os.getenv("WEBHOOK_URL", "https://bot-production-472c.up.railway.app/webhook")
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
                print(f"✅ Webhook автоматически установлен: {webhook_url}")
                logger.info(f"✅ Webhook установлен при старте: {webhook_url}")
            else:
                print("❌ Не удалось установить webhook автоматически")
                logger.error("Ошибка автоматической установки webhook")
                
        except Exception as e:
            print(f"❌ Ошибка при автоматической установке webhook: {e}")
            logger.error(f"Ошибка автоустановки webhook: {e}")
            
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