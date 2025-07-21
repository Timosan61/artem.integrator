#!/usr/bin/env python3
"""
Минимальный webhook для тестирования
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telebot
import uvicorn
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки
BOT_TOKEN = "6658269281:AAETA0vTXiRCMPcL1y_DzEeU_Fc6DiqdpFk"
SECRET_TOKEN = "artyom_integrator_secret_2025"

# Создаем приложение и бота
app = FastAPI()
bot = telebot.TeleBot(BOT_TOKEN)

@app.post("/webhook")
async def webhook(request: Request):
    """Обработчик webhook"""
    # Проверяем секретный токен
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != SECRET_TOKEN:
        logger.warning(f"Invalid secret token: {secret}")
        return JSONResponse({"ok": False, "error": "Invalid secret token"})
    
    # Получаем данные
    data = await request.json()
    logger.info(f"Received update: {data}")
    
    # Обрабатываем сообщение
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        logger.info(f"Message from {chat_id}: {text}")
        
        # Отвечаем на команды
        if text == "/start":
            try:
                bot.send_message(chat_id, "👋 Привет! Я минимальный тестовый бот.")
                logger.info(f"Sent welcome message to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send: {e}")
        else:
            try:
                bot.send_message(chat_id, f"Вы написали: {text}")
                logger.info(f"Echoed message to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send: {e}")
    
    return JSONResponse({"ok": True})

@app.get("/")
async def root():
    return {"status": "Minimal webhook is running"}

if __name__ == "__main__":
    # Устанавливаем webhook
    webhook_url = "https://16bf5c25554f.ngrok-free.app/webhook"
    bot.set_webhook(webhook_url, secret_token=SECRET_TOKEN)
    logger.info(f"Webhook set to: {webhook_url}")
    
    # Запускаем сервер
    uvicorn.run(app, host="0.0.0.0", port=8001)