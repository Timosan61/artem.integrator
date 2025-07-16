"""
🤖 Artyom Integrator Webhook Server

Основной сервер для обработки сообщений через Telegram Business API.
Работает в режиме webhook для мгновенных ответов от имени консультанта Елены из Textile Pro.

Возможности:
- Обработка обычных сообщений боту
- Обработка Business API сообщений (от вашего Premium аккаунта)
- AI-powered ответы через OpenAI (консультант Елена)
- Память диалогов через Zep
- Автоматическая установка webhook при старте
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
import telebot
import json
import asyncio
import requests

# Добавляем путь для импорта модулей бота
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Загрузка Artyom Integrator Webhook Server...")

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

# Пытаемся импортировать SocialMedia сервис и авторизацию
try:
    from bot.services.social_media_service import social_media_service
    from bot.formatters.telegram_formatter import telegram_formatter
    from bot.auth import is_admin, get_user_mode, format_admin_welcome_message, format_user_welcome_message
    print("✅ SocialMedia сервис и авторизация загружены успешно")
    SOCIAL_MEDIA_ENABLED = True
except ImportError as e:
    print(f"⚠️ SocialMedia сервис не доступен: {e}")
    SOCIAL_MEDIA_ENABLED = False

# Пытаемся импортировать YouTube Transcript Service
try:
    from bot.services.youtube_transcript_service import youtube_transcript_service
    print("✅ YouTube Transcript Service загружен успешно")
    YOUTUBE_TRANSCRIPT_ENABLED = True
except ImportError as e:
    print(f"⚠️ YouTube Transcript Service не доступен: {e}")
    YOUTUBE_TRANSCRIPT_ENABLED = False

# Пытаемся импортировать Voice Service
try:
    print(f"🔍 Попытка импорта Voice Service...")
    print(f"📁 Текущая директория: {os.getcwd()}")
    print(f"📁 Содержимое директории: {os.listdir('.')}")
    print(f"📁 Существует ли voice/: {os.path.exists('voice')}")
    if os.path.exists('voice'):
        print(f"📁 Содержимое voice/: {os.listdir('voice')}")
    
    from voice import VoiceService
    print("✅ Voice Service загружен успешно")
    VOICE_ENABLED = True
except ImportError as e:
    print(f"⚠️ Voice Service не доступен (ImportError): {e}")
    print(f"📍 Python path: {sys.path}")
    VOICE_ENABLED = False
except Exception as e:
    print(f"❌ Ошибка загрузки Voice Service: {e}")
    print(f"🔍 Traceback: {traceback.format_exc()}")
    VOICE_ENABLED = False

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "artyom_integrator_secret_2025")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN отсутствует!")

print(f"✅ Токен бота получен: {TELEGRAM_BOT_TOKEN[:20]}...")

# === ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ ДЛЯ ТЕСТИРОВАНИЯ РЕЖИМОВ ===
# Хранит состояние режима тестирования для каждого пользователя
# Формат: {user_id: "admin" | "user" | None}
# None означает использование реального режима
admin_test_mode = {}

# === СИСТЕМА СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЕЙ ===
# Хранит состояние ожидания для каждого пользователя
# Формат: {user_id: {"command": "transcript", "waiting_for": "youtube_link", "timestamp": datetime}}
user_waiting_states = {}

# === СОЗДАНИЕ СИНХРОННОГО БОТА (НЕ ASYNC!) ===
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# === ИНИЦИАЛИЗАЦИЯ VOICE SERVICE ===
voice_service = None
if VOICE_ENABLED:  # Убираем требование AI_ENABLED
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            voice_service = VoiceService(TELEGRAM_BOT_TOKEN, openai_api_key)
            print("✅ Voice Service инициализирован")
        else:
            print("⚠️ OPENAI_API_KEY не найден, голосовые сообщения отключены")
    except Exception as e:
        print(f"❌ Ошибка инициализации Voice Service: {e}")
        voice_service = None

# === ЛОГИРОВАНИЕ ===
import logging.handlers

# Создаем директорию для логов если её нет
os.makedirs("logs", exist_ok=True)

# Настраиваем логирование в файл и консоль
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Формат логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Файловый хендлер с ротацией
file_handler = logging.handlers.RotatingFileHandler(
    filename="logs/bot.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Консольный хендлер
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Добавляем хендлеры к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Логируем запуск приложения
logger.info("🚀 Webhook server started")
logger.info(f"📁 Logs directory: {os.path.abspath('logs')}")
logger.info(f"🤖 Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")
logger.info(f"🔄 AI Agent enabled: {AI_ENABLED}")

# === ФУНКЦИЯ ДЛЯ BUSINESS API ===
def send_business_message(chat_id, text, business_connection_id):
    """
    Отправка сообщения через Business API используя прямой HTTP запрос
    (pyTelegramBotAPI не поддерживает business_connection_id)
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "business_connection_id": business_connection_id
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Business API: сообщение отправлено через HTTP API")
            return result.get("result")
        else:
            logger.error(f"❌ Business API ошибка: {result}")
            return None
    except Exception as e:
        logger.error(f"❌ Business API HTTP ошибка: {e}")
        return None

# === FASTAPI ПРИЛОЖЕНИЕ ===
app = FastAPI(
    title="🤖 Artyom Integrator Bot", 
    description="Webhook-only режим для Textile Pro консультанта Елены"
)

# Хранилище последних updates для отладки
from collections import deque
last_updates = deque(maxlen=10)
update_counter = 0

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        bot_info = bot.get_me()
        return {
            "status": "🟢 ONLINE", 
            "service": "Artyom Integrator Webhook",
            "bot": f"@{bot_info.username}",
            "bot_id": bot_info.id,
            "mode": "WEBHOOK_ONLY",
            "ai_status": "✅ ENABLED" if AI_ENABLED else "❌ DISABLED",
            "voice_status": "✅ ENABLED" if voice_service else "❌ DISABLED",
            "social_media_status": "✅ ENABLED" if SOCIAL_MEDIA_ENABLED else "❌ DISABLED",
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "admin_configured": bool(os.getenv('ADMIN_USER_ID')),
            "endpoints": {
                "webhook_info": "/webhook/info",
                "set_webhook": "/webhook/set",
                "delete_webhook": "/webhook (DELETE method)",
                "social_media_debug": "/debug/social-media-status",
                "test_mode_debug": "/debug/test-mode-status"
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
        webhook_url = "https://artyom-integrator-production.up.railway.app/webhook"
        
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

@app.get("/debug/last-updates")
async def get_last_updates():
    """Показать последние полученные updates для отладки"""
    return {
        "total_received": update_counter,
        "last_10_updates": list(last_updates),
        "current_time": datetime.now().isoformat()
    }

@app.get("/debug/zep-status")
async def get_zep_status():
    """Проверить статус Zep Memory"""
    zep_info = {
        "zep_api_key_set": bool(os.getenv('ZEP_API_KEY')),
        "zep_api_key_length": len(os.getenv('ZEP_API_KEY', '')) if os.getenv('ZEP_API_KEY') else 0,
        "ai_agent_available": AI_ENABLED,
        "zep_client_initialized": False,
        "memory_mode": "unknown"
    }
    
    if AI_ENABLED:
        try:
            zep_info["zep_client_initialized"] = agent.zep_client is not None
            zep_info["memory_mode"] = "Zep Cloud" if agent.zep_client else "Local Fallback"
            zep_info["local_sessions_count"] = len(agent.user_sessions)
            zep_info["local_session_ids"] = list(agent.user_sessions.keys())
        except Exception as e:
            zep_info["error"] = str(e)
    
    return zep_info

@app.get("/debug/memory/{session_id}")
async def get_session_memory(session_id: str):
    """Получить память конкретной сессии"""
    if not AI_ENABLED:
        return {"error": "AI не включен"}
    
    try:
        memory_info = {
            "session_id": session_id,
            "zep_memory": None,
            "local_memory": None,
            "zep_available": agent.zep_client is not None
        }
        
        # Пробуем получить из Zep
        if agent.zep_client:
            try:
                context = await agent.get_zep_memory_context(session_id)
                messages = await agent.get_zep_recent_messages(session_id)
                memory_info["zep_memory"] = {
                    "context": context,
                    "recent_messages": messages
                }
            except Exception as e:
                memory_info["zep_error"] = str(e)
        
        # Получаем локальную память
        if session_id in agent.user_sessions:
            memory_info["local_memory"] = agent.user_sessions[session_id]
        
        return memory_info
        
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.post("/test/business-send")
async def test_business_send(request: Request):
    """Тестовая отправка через Business API"""
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        connection_id = data.get("business_connection_id")
        text = data.get("text", "🧪 Тестовое сообщение Business API")
        
        if not chat_id:
            return {"error": "chat_id обязателен"}
        
        if connection_id:
            result = send_business_message(chat_id, text, connection_id)
            if result:
                return {"status": "✅ Отправлено через Business API", "connection_id": connection_id, "result": result}
            else:
                return {"status": "❌ Ошибка отправки через Business API"}
        else:
            bot.send_message(chat_id, text)
            return {"status": "✅ Отправлено как обычное сообщение"}
            
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug/recent-logs")
async def get_recent_logs():
    """Получить последние логи из файла для диагностики"""
    try:
        log_data = {
            "log_file_exists": os.path.exists("logs/bot.log"),
            "log_file_size": 0,
            "recent_logs": [],
            "error": None
        }
        
        if os.path.exists("logs/bot.log"):
            # Получаем размер файла
            log_data["log_file_size"] = os.path.getsize("logs/bot.log")
            
            # Читаем последние 50 строк
            with open("logs/bot.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
                log_data["recent_logs"] = [line.strip() for line in lines[-50:]]
                log_data["total_lines"] = len(lines)
        else:
            log_data["error"] = "Файл логов не найден"
        
        return log_data
        
    except Exception as e:
        return {
            "error": str(e), 
            "traceback": traceback.format_exc(),
            "log_file_exists": False,
            "recent_logs": []
        }

@app.get("/debug/social-media-status")
async def get_social_media_status():
    """Получить статус SocialMedia сервиса для диагностики"""
    try:
        social_status = {
            "SOCIAL_MEDIA_ENABLED": SOCIAL_MEDIA_ENABLED,
            "service_available": social_media_service is not None if SOCIAL_MEDIA_ENABLED else False,
            "current_time": datetime.now().isoformat()
        }
        
        if SOCIAL_MEDIA_ENABLED and social_media_service:
            try:
                service_status = social_media_service.get_service_status()
                social_status.update(service_status)
            except Exception as e:
                social_status["service_error"] = str(e)
        
        # Проверяем конфигурацию
        from bot.config import ADMIN_USER_ID, ADMIN_USERNAMES, YOUTUBE_API_KEY, INSTAGRAM_API_KEY, TIKTOK_API_KEY
        
        social_status["admin_config"] = {
            "admin_user_id": ADMIN_USER_ID,
            "admin_usernames": ADMIN_USERNAMES,
            "admin_configured": bool(ADMIN_USER_ID)
        }
        
        social_status["api_keys"] = {
            "youtube_configured": bool(YOUTUBE_API_KEY),
            "instagram_configured": bool(INSTAGRAM_API_KEY),
            "tiktok_configured": bool(TIKTOK_API_KEY)
        }
        
        return social_status
        
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug/voice-status")
async def get_voice_status():
    """Получить статус Voice Service для диагностики"""
    try:
        voice_status = {
            "VOICE_ENABLED": VOICE_ENABLED,
            "AI_ENABLED": AI_ENABLED,
            "voice_service_initialized": voice_service is not None,
            "voice_service_type": str(type(voice_service)),
            "openai_api_key_set": bool(os.getenv('OPENAI_API_KEY')),
            "openai_api_key_length": len(os.getenv('OPENAI_API_KEY', '')),
            "telegram_token_set": bool(os.getenv('TELEGRAM_BOT_TOKEN')),
            "current_time": datetime.now().isoformat()
        }
        
        if voice_service:
            try:
                voice_status["service_info"] = voice_service.get_service_info()
            except Exception as e:
                voice_status["service_info_error"] = str(e)
        
        # Тест has_attachments с голосовым сообщением
        test_voice_msg = {
            "voice": {
                "duration": 3,
                "file_id": "test_voice_id",
                "file_size": 15234
            }
        }
        
        attachments, attachments_details = has_attachments(test_voice_msg)
        voice_status["test_attachments"] = attachments
        voice_status["test_details"] = attachments_details
        voice_status["test_condition"] = 'voice' in attachments and voice_service is not None
        
        return voice_status
        
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug/test-mode-status")
async def get_test_mode_status():
    """Получить статус тестового режима для диагностики"""
    try:
        test_mode_status = {
            "admin_test_mode": admin_test_mode,
            "active_test_users": len(admin_test_mode),
            "current_time": datetime.now().isoformat()
        }
        
        # Добавляем информацию о каждом пользователе в тестовом режиме
        for user_id, mode in admin_test_mode.items():
            test_mode_status[f"user_{user_id}"] = {
                "test_mode": mode,
                "real_admin": is_admin(user_id) if SOCIAL_MEDIA_ENABLED else False
            }
        
        return test_mode_status
        
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug/prompt")
async def get_prompt_status():
    """Получить текущий промпт и статус инструкций"""
    if not AI_ENABLED:
        return {"error": "AI не включен"}
    
    try:
        prompt_info = {
            "instruction_file": agent.instruction,
            "last_updated": agent.instruction.get('last_updated', 'неизвестно'),
            "system_instruction_length": len(agent.instruction.get('system_instruction', '')),
            "welcome_message_length": len(agent.instruction.get('welcome_message', '')),
            "current_time": datetime.now().isoformat(),
            "status": "✅ Активен"
        }
        
        # Показываем первые 200 символов системной инструкции
        system_instruction = agent.instruction.get('system_instruction', '')
        if system_instruction:
            prompt_info["system_instruction_preview"] = system_instruction[:200] + "..." if len(system_instruction) > 200 else system_instruction
        
        return prompt_info
        
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.post("/admin/reload-prompt")
async def reload_prompt():
    """Перезагрузить промпт из файла (для админ панели)"""
    if not AI_ENABLED:
        return {"error": "AI не включен"}
    
    try:
        old_updated = agent.instruction.get('last_updated', 'неизвестно')
        agent.reload_instruction()
        new_updated = agent.instruction.get('last_updated', 'неизвестно')
        
        return {
            "status": "✅ Промпт перезагружен",
            "old_updated": old_updated,
            "new_updated": new_updated,
            "changed": old_updated != new_updated,
            "current_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка перезагрузки промпта: {e}")
        return {"error": str(e), "traceback": traceback.format_exc()}

async def handle_admin_command(command: str, user_id: int, user_name: str) -> str:
    """
    Обработка админских команд
    
    Args:
        command: Команда (например, "/youtube test")
        user_id: ID пользователя
        user_name: Имя пользователя
        
    Returns:
        str: Ответ для пользователя
    """
    try:
        # Разбираем команду
        parts = command.split(' ', 1)
        cmd = parts[0].lower()
        query = parts[1] if len(parts) > 1 else ''
        
        logger.info(f"🔑 Админская команда: {cmd}, запрос: '{query}'")
        
        # YouTube команды с интерактивным режимом
        if cmd == '/youtube':
            if not query:
                # Устанавливаем состояние ожидания
                user_waiting_states[user_id] = {
                    'command': 'youtube',
                    'waiting_for': 'search_query',
                    'timestamp': datetime.now()
                }
                return "🎥 Жду поисковый запрос для YouTube\n\n💡 Отправьте запрос или /cancel для отмены"
            
            results = await social_media_service.search('youtube', query, 'videos', 10)
            return telegram_formatter.format_search_results(results, 'youtube', query)
        
        elif cmd == '/channel':
            if not query:
                # Устанавливаем состояние ожидания
                user_waiting_states[user_id] = {
                    'command': 'channel',
                    'waiting_for': 'channel_name',
                    'timestamp': datetime.now()
                }
                return "📺 Жду название канала YouTube\n\n💡 Отправьте название канала или /cancel для отмены"
            
            results = await social_media_service.search('youtube', query, 'channel_videos', 10)
            return telegram_formatter.format_search_results(results, 'youtube', f"канал {query}")
        
        elif cmd == '/youtube_channel':
            if not query:
                # Устанавливаем состояние ожидания
                user_waiting_states[user_id] = {
                    'command': 'youtube_channel',
                    'waiting_for': 'channel_name',
                    'timestamp': datetime.now()
                }
                return "📺 Жду название канала для поиска\n\n💡 Отправьте название канала или /cancel для отмены"
            
            results = await social_media_service.search('youtube', query, 'channels', 5)
            return telegram_formatter.format_search_results(results, 'youtube', f"каналы {query}")
        
        # YouTube Transcript команда
        elif cmd == '/transcript':
            if not query:
                # Устанавливаем состояние ожидания
                user_waiting_states[user_id] = {
                    'command': 'transcript',
                    'waiting_for': 'youtube_link',
                    'timestamp': datetime.now()
                }
                return "🎬 Жду ссылку на видео YouTube\n\n💡 Отправьте ссылку на видео или /cancel для отмены"
            
            if YOUTUBE_TRANSCRIPT_ENABLED:
                # Обрабатываем транскрипцию
                result = youtube_transcript_service.get_transcript(query)
                
                if result['success']:
                    # Сохраняем в файл
                    video_info = result.get('video_info', {})
                    file_path = youtube_transcript_service.save_transcript_to_file(
                        result['text'], 
                        result['video_id'], 
                        video_info.get('title')
                    )
                    
                    # Отправляем файл
                    await send_transcript_file(user_id, file_path, result)
                    return youtube_transcript_service.format_transcript_message(result)
                else:
                    return youtube_transcript_service.format_transcript_message(result)
            else:
                return "❌ YouTube Transcript Service не доступен"
        
        # Instagram команды
        elif cmd == '/instagram':
            if not query:
                return "❌ Укажите поисковый запрос.\n\n💡 Пример: `/instagram travel`"
            
            results = await social_media_service.search('instagram', query, 'videos', 10)
            return telegram_formatter.format_search_results(results, 'instagram', query)
        
        elif cmd == '/insta_user':
            if not query:
                return "❌ Укажите username.\n\n💡 Пример: `/insta_user natgeo`"
            
            results = await social_media_service.search('instagram', query, 'user_posts', 10)
            return telegram_formatter.format_search_results(results, 'instagram', f"пользователь {query}")
        
        # TikTok команды
        elif cmd == '/tiktok':
            if not query:
                return "❌ Укажите поисковый запрос.\n\n💡 Пример: `/tiktok dance`"
            
            results = await social_media_service.search('tiktok', query, 'videos', 10)
            return telegram_formatter.format_search_results(results, 'tiktok', query)
        
        elif cmd == '/tiktok_user':
            if not query:
                return "❌ Укажите username.\n\n💡 Пример: `/tiktok_user charlidamelio`"
            
            results = await social_media_service.search('tiktok', query, 'user_posts', 10)
            return telegram_formatter.format_search_results(results, 'tiktok', f"пользователь {query}")
        
        # Админские команды управления
        elif cmd == '/admin_status':
            status = social_media_service.get_service_status()
            return telegram_formatter.format_admin_status(status)
        
        elif cmd == '/social_config':
            from bot.config import YOUTUBE_API_KEY, INSTAGRAM_API_KEY, TIKTOK_API_KEY
            
            config_info = f"""⚙️ **Конфигурация SocialMedia API**

**🎥 YouTube API:**
{'✅ Настроен' if YOUTUBE_API_KEY else '❌ Не настроен'}
{f'🔑 Ключ: {YOUTUBE_API_KEY[:20]}...' if YOUTUBE_API_KEY else ''}

**📸 Instagram API:**
{'✅ Настроен' if INSTAGRAM_API_KEY else '❌ Не настроен'}
{f'🔑 Ключ: {INSTAGRAM_API_KEY[:20]}...' if INSTAGRAM_API_KEY else ''}

**🎵 TikTok API:**
{'✅ Настроен' if TIKTOK_API_KEY else '❌ Не настроен'}
{f'🔑 Ключ: {TIKTOK_API_KEY[:20]}...' if TIKTOK_API_KEY else ''}

📊 **Доступные платформы:** {', '.join(social_media_service.get_available_platforms())}"""
            
            return config_info
        
        elif cmd == '/help_admin':
            return telegram_formatter.format_admin_command_help()
        
        # Команды тестирования режимов
        elif cmd == '/test_user':
            admin_test_mode[user_id] = "user"
            return f"🧪 **Тестовый режим: ПОЛЬЗОВАТЕЛЬ**\n\n✅ Теперь вы будете получать ответы как обычный пользователь.\n\n📝 Используйте `/test_status` для проверки режима\n🔄 Используйте `/test_admin` для возврата в админ режим"
        
        elif cmd == '/test_admin':
            admin_test_mode[user_id] = "admin"
            return f"🧪 **Тестовый режим: АДМИНИСТРАТОР**\n\n✅ Теперь вы снова в админ режиме.\n\n📝 Используйте `/test_status` для проверки режима\n👤 Используйте `/test_user` для тестирования пользовательского режима"
        
        elif cmd == '/test_status':
            current_mode = admin_test_mode.get(user_id, None)
            real_mode = "admin" if is_admin(user_id, user_name) else "user"
            
            if current_mode is None:
                return f"🔍 **Статус тестирования режимов**\n\n📊 **Текущий режим:** {real_mode.upper()} (реальный)\n🧪 **Тестовый режим:** ОТКЛЮЧЕН\n\n💡 Используйте `/test_user` или `/test_admin` для включения тестирования"
            else:
                return f"🔍 **Статус тестирования режимов**\n\n📊 **Реальный режим:** {real_mode.upper()}\n🧪 **Тестовый режим:** {current_mode.upper()}\n\n💡 Используйте `/test_user` или `/test_admin` для смены режима"
        
        # Команды управления состояниями
        elif cmd == '/cancel':
            if user_id in user_waiting_states:
                del user_waiting_states[user_id]
                return "✅ Команда отменена"
            else:
                return "ℹ️ Нет активных команд для отмены"
        
        elif cmd == '/status':
            if user_id in user_waiting_states:
                state = user_waiting_states[user_id]
                return f"⏳ Активная команда: {state['command']}\n🔄 Ожидание: {state['waiting_for']}\n\n💡 Используйте /cancel для отмены"
            else:
                return "ℹ️ Нет активных команд"
        
        else:
            return f"❌ Неизвестная команда: `{cmd}`\n\n💡 Используйте `/help_admin` для списка команд"
    
    except Exception as e:
        logger.error(f"❌ Ошибка обработки админской команды '{command}': {e}")
        return telegram_formatter.format_error_message(str(e))


async def send_transcript_file(user_id: int, file_path: str, result: dict):
    """
    Отправляет файл транскрипции пользователю
    
    Args:
        user_id: ID пользователя
        file_path: Путь к файлу
        result: Результат получения транскрипции
    """
    try:
        # Проверяем режим пользователя для выбора способа отправки
        user_mode = get_user_mode(user_id, test_mode_override=admin_test_mode)
        
        with open(file_path, 'rb') as f:
            if user_mode == "admin":
                # Отправляем напрямую для админа
                bot.send_document(user_id, f, caption="📄 Транскрипция YouTube видео")
            else:
                # Для обычного пользователя отправляем как есть
                bot.send_document(user_id, f, caption="📄 Транскрипция YouTube видео")
        
        logger.info(f"✅ Файл транскрипции отправлен пользователю {user_id}")
        
        # Удаляем временный файл
        import os
        os.remove(file_path)
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки файла транскрипции: {e}")
        raise


def has_attachments(message):
    """Проверяет наличие вложений в сообщении и извлекает их метаданные"""
    attachment_types = [
        'photo', 'document', 'video', 'audio', 'voice', 'video_note',
        'sticker', 'animation', 'contact', 'location', 'venue', 'poll'
    ]
    
    attachments_found = []
    attachments_details = []
    
    for attachment_type in attachment_types:
        if attachment_type in message:
            attachments_found.append(attachment_type)
            
            # Извлекаем детальную информацию о вложении
            attachment_data = message[attachment_type]
            detail = {"type": attachment_type}
            
            # Для разных типов вложений извлекаем разную информацию
            if attachment_type == 'photo':
                # Фото может быть массивом разных размеров
                if isinstance(attachment_data, list) and len(attachment_data) > 0:
                    largest_photo = max(attachment_data, key=lambda x: x.get('file_size', 0))
                    detail.update({
                        "file_id": largest_photo.get('file_id'),
                        "file_size": largest_photo.get('file_size'),
                        "width": largest_photo.get('width'),
                        "height": largest_photo.get('height')
                    })
            elif attachment_type == 'document':
                detail.update({
                    "file_id": attachment_data.get('file_id'),
                    "file_name": attachment_data.get('file_name'),
                    "file_size": attachment_data.get('file_size'),
                    "mime_type": attachment_data.get('mime_type')
                })
            elif attachment_type in ['video', 'audio', 'voice', 'video_note']:
                detail.update({
                    "file_id": attachment_data.get('file_id'),
                    "file_size": attachment_data.get('file_size'),
                    "duration": attachment_data.get('duration')
                })
                if attachment_type == 'video':
                    detail.update({
                        "width": attachment_data.get('width'),
                        "height": attachment_data.get('height')
                    })
            elif attachment_type == 'sticker':
                detail.update({
                    "file_id": attachment_data.get('file_id'),
                    "width": attachment_data.get('width'),
                    "height": attachment_data.get('height'),
                    "emoji": attachment_data.get('emoji')
                })
            elif attachment_type == 'contact':
                detail.update({
                    "phone_number": attachment_data.get('phone_number'),
                    "first_name": attachment_data.get('first_name'),
                    "last_name": attachment_data.get('last_name')
                })
            elif attachment_type == 'location':
                detail.update({
                    "latitude": attachment_data.get('latitude'),
                    "longitude": attachment_data.get('longitude')
                })
            else:
                # Для других типов просто сохраняем file_id если есть
                if hasattr(attachment_data, 'get') and attachment_data.get('file_id'):
                    detail["file_id"] = attachment_data.get('file_id')
            
            attachments_details.append(detail)
    
    return attachments_found, attachments_details

@app.post("/webhook")
async def process_webhook(request: Request):
    """Главный обработчик webhook"""
    global update_counter
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
        
        # Сохраняем update для отладки
        update_counter += 1
        debug_update = {
            "id": update_counter,
            "timestamp": datetime.now().isoformat(),
            "type": "unknown",
            "data": update_dict
        }
        
        # Определяем тип update
        if "message" in update_dict:
            debug_update["type"] = "message"
        elif "business_message" in update_dict:
            debug_update["type"] = "business_message"
        elif "business_connection" in update_dict:
            debug_update["type"] = "business_connection"
        elif "edited_business_message" in update_dict:
            debug_update["type"] = "edited_business_message"
        elif "deleted_business_messages" in update_dict:
            debug_update["type"] = "deleted_business_messages"
        else:
            debug_update["type"] = f"other: {list(update_dict.keys())}"
            
        last_updates.append(debug_update)
        logger.info(f"📊 Update #{update_counter} тип: {debug_update['type']}")
        
        # === ОБЫЧНЫЕ СООБЩЕНИЯ ===
        if "message" in update_dict:
            msg = update_dict["message"]
            chat_id = msg["chat"]["id"]
            # Извлекаем текст из text или caption (для изображений и медиафайлов)
            text = msg.get("text", "") or msg.get("caption", "")
            user_id = msg.get("from", {}).get("id", "unknown")
            user_name = msg.get("from", {}).get("first_name", "Пользователь")
            
            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ СООБЩЕНИЯ
            print(f"\n=== MESSAGE PROCESSING START ===")
            print(f"📨 USER: {user_name} (ID: {user_id})")
            print(f"💬 CHAT: {chat_id}")
            print(f"📝 TEXT: '{text}'")
            print(f"📋 MSG KEYS: {list(msg.keys())}")
            logger.info(f"📨 Обработка сообщения от {user_name} ({user_id}) в чате {chat_id}")
            logger.info(f"📝 Текст: '{text}'")
            logger.info(f"📋 Ключи сообщения: {list(msg.keys())}")
            
            # Проверяем наличие вложений
            attachments, attachments_details = has_attachments(msg)
            
            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ВЛОЖЕНИЙ
            print(f"📎 ATTACHMENTS: {attachments}")
            print(f"📄 DETAILS: {attachments_details}")
            
            try:
                # Логируем информацию о сообщении
                if attachments:
                    logger.info(f"📎 Сообщение с вложениями: {attachments}, текст: '{text}'")
                    logger.info(f"📋 Источник текста: {'text' if msg.get('text') else 'caption' if msg.get('caption') else 'none'}")
                    # Детальное логирование вложений
                    for detail in attachments_details:
                        logger.info(f"   📄 {detail['type']}: {detail}")
                
                # === ОБРАБОТКА ГОЛОСОВЫХ СООБЩЕНИЙ ===
                print(f"\n--- VOICE CHECK ---")
                print(f"🔍 attachments: {attachments}")
                print(f"🔍 voice_service: {voice_service is not None}")
                print(f"🔍 VOICE_ENABLED: {VOICE_ENABLED}")
                print(f"🔍 'voice' in attachments: {'voice' in attachments if attachments else False}")
                print(f"🔍 voice_service type: {type(voice_service)}")
                logger.info(f"🔍 Проверка голосовых: attachments={attachments}, voice_service={voice_service is not None}, VOICE_ENABLED={VOICE_ENABLED}")
                
                if 'voice' in attachments and voice_service:
                    print(f"🎤 VOICE PROCESSING STARTED!")
                    print(f"🎤 Voice attachments found: {[d for d in attachments_details if d['type'] == 'voice']}")
                    logger.info(f"🎤 Получено голосовое сообщение от {user_name}, текст='{text}'")
                    
                    try:
                        # Отправляем индикатор записи голоса
                        bot.send_chat_action(chat_id, 'record_voice')
                        
                        # Находим данные голосового сообщения
                        voice_data = None
                        for detail in attachments_details:
                            if detail['type'] == 'voice':
                                voice_data = detail
                                break
                        
                        if voice_data:
                            # Обрабатываем голосовое сообщение
                            print(f"🎤 Processing voice data: {voice_data}")
                            try:
                                # Простой подход - запускаем в отдельном thread
                                import threading
                                import queue
                                
                                result_queue = queue.Queue()
                                
                                def run_voice_processing():
                                    try:
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        try:
                                            result = loop.run_until_complete(
                                                voice_service.process_voice_message(
                                                    voice_data, 
                                                    str(user_id), 
                                                    str(msg.get('message_id', 'unknown'))
                                                )
                                            )
                                            result_queue.put(('success', result))
                                        finally:
                                            loop.close()
                                    except Exception as e:
                                        result_queue.put(('error', str(e)))
                                
                                thread = threading.Thread(target=run_voice_processing)
                                thread.start()
                                thread.join(timeout=30)  # 30 секунд таймаут
                                
                                if thread.is_alive():
                                    print(f"⏰ Таймаут обработки голоса")
                                    voice_result = {'success': False, 'error': 'Voice processing timeout'}
                                else:
                                    try:
                                        status, result = result_queue.get_nowait()
                                        if status == 'success':
                                            voice_result = result
                                        else:
                                            voice_result = {'success': False, 'error': result}
                                    except queue.Empty:
                                        voice_result = {'success': False, 'error': 'No result from voice processing'}
                                        
                            except Exception as voice_proc_error:
                                print(f"❌ Ошибка обработки голоса: {voice_proc_error}")
                                voice_result = {'success': False, 'error': str(voice_proc_error)}
                            
                            if voice_result['success']:
                                # Получили транскрипцию - передаем агенту для обработки
                                transcribed_text = voice_result['text']
                                logger.info(f"✅ Голос транскрибирован: {transcribed_text[:100]}...")
                                print(f"🎤 Voice transcribed: {transcribed_text[:100]}...")
                                
                                # Заменяем пустой текст на транскрибированный
                                text = transcribed_text
                                logger.info(f"🎤 Голосовое сообщение будет обработано агентом как текст: {text[:100]}...")
                                print(f"🎤 Voice message will be processed by agent as text: {text[:100]}...")
                                # НЕ возвращаем, продолжаем обработку как обычное текстовое сообщение
                            else:
                                # Ошибка обработки голоса - только логируем
                                logger.error(f"❌ Ошибка обработки голоса: {voice_result['error']}")
                                print(f"❌ Voice processing error: {voice_result['error']}")
                                # НЕ отправляем сообщение об ошибке пользователю
                                return {"ok": True, "action": "voice_error_silent"}
                        else:
                            logger.error("❌ Не найдены данные голосового сообщения")
                            
                    except Exception as voice_error:
                        logger.error(f"❌ Критическая ошибка обработки голоса: {voice_error}")
                        print(f"❌ Critical voice error: {voice_error}")
                        # НЕ отправляем сообщение об ошибке пользователю
                        return {"ok": True, "action": "voice_critical_error_silent"}
                
                
                # Пытаемся отправить индикатор набора текста
                try:
                    bot.send_chat_action(chat_id, 'typing')
                except Exception as typing_error:
                    logger.warning(f"⚠️ Не удалось отправить typing индикатор: {typing_error}")
                
                # === ОБРАБОТКА КОМАНД И ТЕКСТА ===
                print(f"\n--- TEXT PROCESSING ---")
                print(f"📝 Processing text: '{text}'")
                print(f"🤖 AI_ENABLED: {AI_ENABLED}")
                
                # Определяем режим пользователя с учетом тестового режима
                user_mode = get_user_mode(user_id, msg.get("from", {}).get("username"), admin_test_mode) if SOCIAL_MEDIA_ENABLED else "user"
                is_admin_user = (user_mode == "admin")
                
                print(f"🔑 User mode: {user_mode} (admin: {is_admin_user})")
                
                # Обрабатываем команды
                if text.startswith("/start"):
                    print(f"🚀 START command detected")
                    if SOCIAL_MEDIA_ENABLED and is_admin_user:
                        response = format_admin_welcome_message(user_id, msg.get("from", {}).get("username"), admin_test_mode)
                    elif AI_ENABLED:
                        response = agent.get_welcome_message()
                    else:
                        response = format_user_welcome_message(user_name, user_id, admin_test_mode) if SOCIAL_MEDIA_ENABLED else f"👋 Привет, {user_name}! Меня зовут Елена, я менеджер компании Textile Pro.\n\nКакой у вас вопрос?"
                
                elif text.startswith("/help"):
                    print(f"❓ HELP command detected")
                    if SOCIAL_MEDIA_ENABLED and is_admin_user:
                        response = telegram_formatter.format_admin_command_help()
                    else:
                        response = """ℹ️ Помощь:
/start - начать работу
/help - показать помощь

Просто напишите ваш вопрос о текстильном производстве, и я с радостью помогу!

📞 Для срочных вопросов: +86 123 456 789"""
                
                # === ПРОВЕРКА СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЕЙ ===
                elif user_id in user_waiting_states and not text.startswith("/"):
                    print(f"⏳ User {user_id} в состоянии ожидания: {user_waiting_states[user_id]}")
                    
                    state = user_waiting_states[user_id]
                    command = state['command']
                    waiting_for = state['waiting_for']
                    
                    # Очищаем состояние
                    del user_waiting_states[user_id]
                    
                    # Обрабатываем в зависимости от команды
                    if command == 'transcript' and waiting_for == 'youtube_link':
                        if YOUTUBE_TRANSCRIPT_ENABLED:
                            print(f"🎬 Обработка транскрипции для: {text}")
                            result = youtube_transcript_service.get_transcript(text)
                            
                            if result['success']:
                                # Сохраняем в файл
                                video_info = result.get('video_info', {})
                                file_path = youtube_transcript_service.save_transcript_to_file(
                                    result['text'], 
                                    result['video_id'], 
                                    video_info.get('title')
                                )
                                
                                # Отправляем файл
                                await send_transcript_file(user_id, file_path, result)
                                response = youtube_transcript_service.format_transcript_message(result)
                            else:
                                response = youtube_transcript_service.format_transcript_message(result)
                        else:
                            response = "❌ YouTube Transcript Service не доступен"
                    
                    elif command == 'youtube' and waiting_for == 'search_query':
                        if SOCIAL_MEDIA_ENABLED:
                            print(f"🎥 Поиск на YouTube: {text}")
                            try:
                                results = await social_media_service.search('youtube', text, 'videos', 10)
                                response = telegram_formatter.format_search_results(results, 'youtube', text)
                            except Exception as e:
                                response = telegram_formatter.format_error_message(str(e), 'youtube')
                        else:
                            response = "❌ SocialMedia сервис не доступен"
                    
                    elif command == 'channel' and waiting_for == 'channel_name':
                        if SOCIAL_MEDIA_ENABLED:
                            print(f"📺 Поиск видео канала: {text}")
                            try:
                                results = await social_media_service.search('youtube', text, 'channel_videos', 10)
                                response = telegram_formatter.format_search_results(results, 'youtube', f"канал {text}")
                            except Exception as e:
                                response = telegram_formatter.format_error_message(str(e), 'youtube')
                        else:
                            response = "❌ SocialMedia сервис не доступен"
                    
                    elif command == 'youtube_channel' and waiting_for == 'channel_name':
                        if SOCIAL_MEDIA_ENABLED:
                            print(f"📺 Поиск каналов: {text}")
                            try:
                                results = await social_media_service.search('youtube', text, 'channels', 5)
                                response = telegram_formatter.format_search_results(results, 'youtube', f"каналы {text}")
                            except Exception as e:
                                response = telegram_formatter.format_error_message(str(e), 'youtube')
                        else:
                            response = "❌ SocialMedia сервис не доступен"
                    
                    else:
                        response = "❌ Неизвестная команда или состояние"
                
                # === АДМИНСКИЕ КОМАНДЫ ===
                elif SOCIAL_MEDIA_ENABLED and is_admin_user and text.startswith("/"):
                    print(f"🔑 Admin command detected: {text}")
                    try:
                        response = await handle_admin_command(text, user_id, user_name)
                    except Exception as admin_error:
                        logger.error(f"❌ Ошибка админской команды: {admin_error}")
                        response = telegram_formatter.format_error_message(str(admin_error))
                
                # === КОМАНДЫ ТЕСТИРОВАНИЯ ДЛЯ РЕАЛЬНЫХ АДМИНОВ ===
                elif SOCIAL_MEDIA_ENABLED and is_admin(user_id, msg.get("from", {}).get("username")) and text.startswith("/test_"):
                    print(f"🧪 Test command detected: {text}")
                    try:
                        response = await handle_admin_command(text, user_id, user_name)
                    except Exception as test_error:
                        logger.error(f"❌ Ошибка команды тестирования: {test_error}")
                        response = telegram_formatter.format_error_message(str(test_error))
                
                elif text.startswith("/") and SOCIAL_MEDIA_ENABLED and not is_admin_user:
                    # Неадминские команды - отказ в доступе
                    response = """🚫 Команда недоступна
                    
👤 Эта команда доступна только администратору системы.
💬 Для консультации просто напишите ваш вопрос."""
                
                # Если есть текст (с вложениями или без) - обрабатываем через AI
                elif text and AI_ENABLED:
                    print(f"🤖 AI processing text: '{text[:50]}...'")
                    print(f"📎 With attachments: {attachments}")
                    try:
                        session_id = f"user_{user_id}"
                        # Создаем пользователя в Zep если нужно
                        if agent.zep_client:
                            await agent.ensure_user_exists(f"user_{user_id}", {
                                'first_name': user_name,
                                'email': f'{user_id}@telegram.user'
                            })
                            await agent.ensure_session_exists(session_id, f"user_{user_id}")
                        
                        # Проверяем намерение социальных медиа для админов
                        if SOCIAL_MEDIA_ENABLED and is_admin_user:
                            social_intent = await agent.detect_social_media_intent(text)
                            print(f"🔍 Social media intent detected: {social_intent}")
                            
                            if social_intent['has_social_intent']:
                                platform = social_intent['platform']
                                query = social_intent['query']
                                
                                if query:  # Есть поисковый запрос
                                    print(f"🎯 Executing social media search: {platform} '{query}'")
                                    try:
                                        search_type = 'channel_videos' if social_intent['is_channel'] else 'videos'
                                        results = await social_media_service.search(platform, query, search_type, 10)
                                        response = telegram_formatter.format_search_results(results, platform, query)
                                        response += f"\n\n💡 Найдено автоматически. Используйте /{platform} для прямых запросов."
                                    except Exception as search_error:
                                        logger.error(f"❌ Ошибка автоматического поиска: {search_error}")
                                        response = await agent.generate_response(text, session_id, user_name)
                                        response += f"\n\n💡 Для поиска на {platform.upper()} используйте /{platform} <запрос>"
                                else:
                                    # Нет конкретного запроса, отвечаем через AI с подсказкой
                                    response = await agent.generate_response(text, session_id, user_name)
                                    response += f"\n\n💡 Для поиска на {platform.upper()} используйте /{platform} <запрос>"
                            else:
                                # Обычный AI ответ
                                response = await agent.generate_response(text, session_id, user_name)
                        else:
                            # Обычный AI ответ для неадминов
                            response = await agent.generate_response(text, session_id, user_name)
                        
                        # Дополнительное логирование для случая с вложениями
                        if attachments:
                            logger.info(f"✅ AI ответил на ТЕКСТ (вложения проигнорированы): {attachments}")
                            for detail in attachments_details:
                                logger.info(f"   📄 Вложение проигнорировано {detail['type']}: {detail}")
                        
                    except Exception as ai_error:
                        logger.error(f"Ошибка AI генерации: {ai_error}")
                        response = f"Извините, произошла техническая ошибка. Попробуйте позже или напишите вопрос снова.\n\nПо любым срочным вопросам обращайтесь напрямую.\n\nЕлена, Textile Pro"
                    
                # Если есть только вложения без текста - НЕ отвечаем
                elif attachments and not text:
                    print(f"📎 Attachments received but no response sent: {attachments}")
                    logger.info(f"📎 Вложения получены без текста, ответ НЕ отправляется: {attachments}")
                    # НЕ обрабатываем и НЕ отвечаем на вложения без текста
                    return {"ok": True, "action": "attachments_ignored"}
                
                elif text:
                    # Fallback если AI не доступен
                    print(f"💬 Text fallback (AI disabled): '{text}'")
                    response = f"👋 {user_name}, получила ваш вопрос!\n\nПодготовлю детальный ответ по текстильному производству. Минуточку!\n\nЕлена, Textile Pro"
                
                elif attachments and not text:
                    # Fallback для вложений без AI - НЕ отвечаем
                    print(f"📎 Attachments ignored (AI disabled): {attachments}")
                    logger.info(f"📎 Вложения проигнорированы (AI отключен): {attachments}")
                    return {"ok": True, "action": "attachments_ignored_no_ai"}
                
                else:
                    # Этот случай не должен происходить
                    print(f"⚠️ UNEXPECTED: No text and no attachments")
                    print(f"📋 MSG STRUCTURE: {json.dumps(msg, ensure_ascii=False, indent=2)}")
                    logger.warning(f"⚠️ Неожиданный случай: нет текста и нет вложений")
                    logger.warning(f"📋 Структура сообщения: {json.dumps(msg, ensure_ascii=False)}")
                    return {"ok": True, "action": "no_action"}
                    
                # Отправляем ответ только если он определен
                if 'response' in locals() and response:
                    print(f"\n--- SENDING RESPONSE ---")
                    print(f"📤 Response: '{response[:100]}...'")
                    print(f"💬 To chat: {chat_id}")
                    bot.send_message(chat_id, response)
                    logger.info(f"✅ Ответ отправлен в чат {chat_id}")
                    print(f"✅ Response sent to {user_name}")
                else:
                    print(f"\n--- NO RESPONSE ---")
                    print(f"🔇 No response generated (attachments ignored)")
                    logger.info(f"🔇 Ответ НЕ отправлен (вложения проигнорированы)")
                print(f"=== MESSAGE PROCESSING END ===\n")
                
            except Exception as e:
                print(f"\n❌ CRITICAL ERROR in message processing:")
                print(f"❌ Error: {e}")
                print(f"❌ Traceback: {traceback.format_exc()}")
                print(f"❌ Message data: {json.dumps(msg, ensure_ascii=False, indent=2)}")
                logger.error(f"❌ Ошибка обработки сообщения: {e}")
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                logger.error(f"❌ Данные сообщения: {json.dumps(msg, ensure_ascii=False)}")
                try:
                    bot.send_message(chat_id, "Извините, произошла непредвиденная ошибка. Попробуйте написать снова.\n\nЕлена, Textile Pro")
                    print(f"✅ Error message sent")
                except Exception as send_error:
                    print(f"❌ Failed to send error message: {send_error}")
                    logger.error(f"❌ Не удалось отправить сообщение об ошибке: {send_error}")
        
        # === BUSINESS СООБЩЕНИЯ ===
        elif "business_message" in update_dict:
            bus_msg = update_dict["business_message"]
            
            # Детальное логирование структуры business_message
            logger.info(f"📨 Business message полная структура: {json.dumps(bus_msg, ensure_ascii=False)[:500]}...")
            
            chat_id = bus_msg["chat"]["id"]
            # Извлекаем текст из text или caption (для изображений и медиафайлов)
            text = bus_msg.get("text", "") or bus_msg.get("caption", "")
            user_id = bus_msg.get("from", {}).get("id", "unknown")
            business_connection_id = bus_msg.get("business_connection_id")
            user_name = bus_msg.get("from", {}).get("first_name", "Клиент")
            
            # Логируем business_connection_id для отладки
            logger.info(f"📊 Business message - connection_id: '{business_connection_id}' (тип: {type(business_connection_id)})")
            
            # Проверяем наличие business_connection_id
            if not business_connection_id:
                logger.warning(f"⚠️ Business message без connection_id от {user_name} ({user_id})")
            
            # Проверяем наличие вложений в business сообщении
            attachments, attachments_details = has_attachments(bus_msg)
            
            # Логируем информацию о сообщении
            if attachments:
                logger.info(f"📎 Business сообщение с вложениями: {attachments}, текст: '{text}'")
                logger.info(f"📋 Источник текста: {'text' if bus_msg.get('text') else 'caption' if bus_msg.get('caption') else 'none'}")
                # Детальное логирование вложений
                for detail in attachments_details:
                    logger.info(f"   📄 {detail['type']}: {detail}")
            
            
            # Обрабатываем business сообщения с текстом (с вложениями или без)
            if text:
                try:
                    logger.info(f"🔄 Начинаю обработку business message: text='{text}', chat_id={chat_id}")
                    
                    # Определяем режим пользователя для business сообщений с учетом тестового режима
                    user_mode = get_user_mode(user_id, bus_msg.get("from", {}).get("username"), admin_test_mode) if SOCIAL_MEDIA_ENABLED else "user"
                    is_admin_user = (user_mode == "admin")
                    
                    logger.info(f"🔑 Business user mode: {user_mode} (admin: {is_admin_user})")
                    
                    # Пытаемся отправить typing, но не критично если не получится для business чатов
                    try:
                        bot.send_chat_action(chat_id, 'typing')
                        logger.info(f"✅ Отправлен typing индикатор")
                    except Exception as typing_error:
                        # Business чаты могут не поддерживать typing через обычный API
                        logger.warning(f"⚠️ Не удалось отправить typing для business чата: {typing_error}")
                        logger.info(f"ℹ️ Продолжаем без typing индикатора")
                    
                    # === ПРОВЕРКА СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЕЙ В BUSINESS СООБЩЕНИЯХ ===
                    if user_id in user_waiting_states and not text.startswith("/"):
                        logger.info(f"⏳ Business user {user_id} в состоянии ожидания: {user_waiting_states[user_id]}")
                        
                        state = user_waiting_states[user_id]
                        command = state['command']
                        waiting_for = state['waiting_for']
                        
                        # Очищаем состояние
                        del user_waiting_states[user_id]
                        
                        # Обрабатываем в зависимости от команды
                        if command == 'transcript' and waiting_for == 'youtube_link':
                            if YOUTUBE_TRANSCRIPT_ENABLED:
                                logger.info(f"🎬 Business обработка транскрипции для: {text}")
                                result = youtube_transcript_service.get_transcript(text)
                                
                                if result['success']:
                                    # Сохраняем в файл
                                    video_info = result.get('video_info', {})
                                    file_path = youtube_transcript_service.save_transcript_to_file(
                                        result['text'], 
                                        result['video_id'], 
                                        video_info.get('title')
                                    )
                                    
                                    # Отправляем файл через business API
                                    try:
                                        with open(file_path, 'rb') as f:
                                            # Сначала отправляем файл
                                            bot.send_document(chat_id, f, caption="📄 Транскрипция YouTube видео")
                                            
                                        # Затем отправляем описание
                                        response = youtube_transcript_service.format_transcript_message(result)
                                        
                                        # Удаляем временный файл
                                        import os
                                        os.remove(file_path)
                                        
                                    except Exception as file_error:
                                        logger.error(f"❌ Ошибка отправки файла транскрипции: {file_error}")
                                        response = youtube_transcript_service.format_transcript_message(result)
                                        response += f"\n\n❌ Ошибка отправки файла: {str(file_error)}"
                                else:
                                    response = youtube_transcript_service.format_transcript_message(result)
                            else:
                                response = "❌ YouTube Transcript Service не доступен"
                        
                        elif command == 'youtube' and waiting_for == 'search_query':
                            if SOCIAL_MEDIA_ENABLED:
                                logger.info(f"🎥 Business поиск на YouTube: {text}")
                                try:
                                    results = await social_media_service.search('youtube', text, 'videos', 10)
                                    response = telegram_formatter.format_search_results(results, 'youtube', text)
                                except Exception as e:
                                    response = telegram_formatter.format_error_message(str(e), 'youtube')
                            else:
                                response = "❌ SocialMedia сервис не доступен"
                        
                        elif command == 'channel' and waiting_for == 'channel_name':
                            if SOCIAL_MEDIA_ENABLED:
                                logger.info(f"📺 Business поиск видео канала: {text}")
                                try:
                                    results = await social_media_service.search('youtube', text, 'channel_videos', 10)
                                    response = telegram_formatter.format_search_results(results, 'youtube', f"канал {text}")
                                except Exception as e:
                                    response = telegram_formatter.format_error_message(str(e), 'youtube')
                            else:
                                response = "❌ SocialMedia сервис не доступен"
                        
                        elif command == 'youtube_channel' and waiting_for == 'channel_name':
                            if SOCIAL_MEDIA_ENABLED:
                                logger.info(f"📺 Business поиск каналов: {text}")
                                try:
                                    results = await social_media_service.search('youtube', text, 'channels', 5)
                                    response = telegram_formatter.format_search_results(results, 'youtube', f"каналы {text}")
                                except Exception as e:
                                    response = telegram_formatter.format_error_message(str(e), 'youtube')
                            else:
                                response = "❌ SocialMedia сервис не доступен"
                        
                        else:
                            response = "❌ Неизвестная команда или состояние"
                    
                    # Обработка админских команд в business сообщениях
                    elif SOCIAL_MEDIA_ENABLED and is_admin_user and text.startswith("/"):
                        logger.info(f"🔑 Business admin command: {text}")
                        response = await handle_admin_command(text, user_id, user_name)
                    elif AI_ENABLED:
                        # Используем AI для Business сообщений
                        logger.info(f"🤖 AI включен, генерирую ответ...")
                        session_id = f"business_{user_id}"
                        # Создаем пользователя в Zep если нужно
                        if agent.zep_client:
                            await agent.ensure_user_exists(f"business_{user_id}", {
                                'first_name': user_name,
                                'email': f'{user_id}@business.telegram.user'
                            })
                            await agent.ensure_session_exists(session_id, f"business_{user_id}")
                        response = await agent.generate_response(text, session_id, user_name)
                        logger.info(f"✅ AI ответ сгенерирован: {response[:100]}...")
                        
                        # Дополнительное логирование для случая с вложениями
                        if attachments:
                            logger.info(f"✅ AI ответил на business ТЕКСТ (вложения проигнорированы): {attachments}")
                            for detail in attachments_details:
                                logger.info(f"   📄 Business вложение проигнорировано {detail['type']}: {detail}")
                    else:
                        logger.info(f"🤖 AI отключен, использую стандартный ответ")
                        response = f"👋 Здравствуйте, {user_name}!\n\nМеня зовут Елена, я менеджер компании Textile Pro.\n\nПодготовлю ответ на ваш вопрос о текстильном производстве. Минуточку!"
                    
                    # Для business_message используем специальную функцию
                    logger.info(f"📤 Пытаюсь отправить ответ...")
                    if business_connection_id:
                        logger.info(f"📤 Отправляю через Business API с connection_id='{business_connection_id}'")
                        result = send_business_message(chat_id, response, business_connection_id)
                        if result:
                            logger.info(f"✅ Business ответ отправлен в чат {chat_id} с connection_id='{business_connection_id}'")
                        else:
                            logger.error(f"❌ Не удалось отправить через Business API")
                    else:
                        # Если connection_id отсутствует, логируем это как критическую ошибку
                        logger.error(f"❌ КРИТИЧНО: Получен business_message без connection_id! chat_id={chat_id}, user={user_name}")
                        # Пробуем отправить как обычное сообщение
                        bot.send_message(chat_id, response)
                        logger.warning(f"⚠️ Отправлено как обычное сообщение (fallback)")
                    
                    print(f"✅ Business ответ отправлен пользователю {user_name}")
                    
                except Exception as e:
                    # Детальное логирование ошибки с traceback
                    error_info = {
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "business_connection_id": business_connection_id,
                        "chat_id": chat_id,
                        "text": text
                    }
                    logger.error(f"❌ Ошибка обработки business сообщения: {e}")
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
                    logger.error(f"Business connection_id: '{business_connection_id}'")
                    
                    # Сохраняем ошибку в debug данные
                    last_updates.append({
                        "id": f"error_{update_counter}",
                        "timestamp": datetime.now().isoformat(),
                        "type": "business_message_error",
                        "error_info": error_info
                    })
                    
                    # ВАЖНО: Отправляем ошибку ТОЖЕ через Business API!
                    try:
                        error_message = "Извините, произошла техническая ошибка. Попробуйте написать снова или обратитесь ко мне напрямую.\n\nЕлена, Textile Pro"
                        
                        # Если есть business_connection_id - используем его
                        if business_connection_id:
                            result = send_business_message(chat_id, error_message, business_connection_id)
                            if result:
                                logger.info(f"✅ Сообщение об ошибке отправлено через Business API")
                            else:
                                # Если Business API не сработал, пробуем обычный способ
                                bot.send_message(chat_id, error_message)
                                logger.warning(f"⚠️ Business API не сработал, отправлено обычным способом")
                        else:
                            # Fallback: если нет connection_id, отправляем обычное сообщение
                            bot.send_message(chat_id, error_message)
                            logger.warning(f"⚠️ Сообщение об ошибке отправлено БЕЗ Business API (нет connection_id)")
                            
                    except Exception as send_error:
                        logger.error(f"❌ Не удалось отправить сообщение об ошибке: {send_error}")
            
            # === ОБРАБОТКА ГОЛОСОВЫХ BUSINESS СООБЩЕНИЙ ===
            elif 'voice' in attachments and voice_service:
                logger.info(f"🎤 Business голосовое сообщение от {user_name}, текст='{text}'")
                print(f"🎤 BUSINESS VOICE PROCESSING STARTED!")
                
                try:
                    # Отправляем индикатор записи голоса
                    try:
                        bot.send_chat_action(chat_id, 'record_voice')
                        logger.info(f"✅ Отправлен voice typing индикатор для business чата")
                    except Exception as typing_error:
                        logger.warning(f"⚠️ Не удалось отправить voice typing для business чата: {typing_error}")
                    
                    # Находим данные голосового сообщения
                    voice_data = None
                    for detail in attachments_details:
                        if detail['type'] == 'voice':
                            voice_data = detail
                            break
                    
                    if voice_data:
                        logger.info(f"🎤 Processing business voice data: {voice_data}")
                        
                        # Обрабатываем голосовое сообщение (аналогично обычным сообщениям)
                        import threading
                        import queue
                        
                        result_queue = queue.Queue()
                        
                        def run_business_voice_processing():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    result = loop.run_until_complete(
                                        voice_service.process_voice_message(
                                            voice_data, 
                                            str(user_id), 
                                            str(bus_msg.get('message_id', 'unknown'))
                                        )
                                    )
                                    result_queue.put(('success', result))
                                finally:
                                    loop.close()
                            except Exception as e:
                                result_queue.put(('error', str(e)))
                        
                        thread = threading.Thread(target=run_business_voice_processing)
                        thread.start()
                        thread.join(timeout=30)  # 30 секунд таймаут
                        
                        if thread.is_alive():
                            logger.warning(f"⏰ Таймаут обработки business голоса")
                            voice_result = {'success': False, 'error': 'Voice processing timeout'}
                        else:
                            try:
                                status, result = result_queue.get_nowait()
                                if status == 'success':
                                    voice_result = result
                                else:
                                    voice_result = {'success': False, 'error': result}
                            except queue.Empty:
                                voice_result = {'success': False, 'error': 'No result from voice processing'}
                        
                        if voice_result['success']:
                            # Получили транскрипцию - передаем агенту для обработки
                            transcribed_text = voice_result['text']
                            logger.info(f"✅ Business голос транскрибирован: {transcribed_text[:100]}...")
                            
                            # Определяем режим пользователя для business голосовых сообщений
                            user_mode = get_user_mode(user_id, bus_msg.get("from", {}).get("username"), admin_test_mode) if SOCIAL_MEDIA_ENABLED else "user"
                            is_admin_user = (user_mode == "admin")
                            
                            logger.info(f"🔑 Business voice user mode: {user_mode} (admin: {is_admin_user})")
                            
                            # Обработка админских команд в голосовых business сообщениях
                            if SOCIAL_MEDIA_ENABLED and is_admin_user and transcribed_text.startswith("/"):
                                logger.info(f"🔑 Business voice admin command: {transcribed_text}")
                                response = await handle_admin_command(transcribed_text, user_id, user_name)
                            elif AI_ENABLED:
                                # Используем AI для Business голосовых сообщений
                                logger.info(f"🤖 AI включен для business voice, генерирую ответ...")
                                session_id = f"business_{user_id}"
                                # Создаем пользователя в Zep если нужно
                                if agent.zep_client:
                                    await agent.ensure_user_exists(f"business_{user_id}", {
                                        'first_name': user_name,
                                        'email': f'{user_id}@business.telegram.user'
                                    })
                                    await agent.ensure_session_exists(session_id, f"business_{user_id}")
                                response = await agent.generate_response(transcribed_text, session_id, user_name)
                                logger.info(f"✅ AI business voice ответ сгенерирован: {response[:100]}...")
                            else:
                                logger.info(f"🤖 AI отключен для business voice, использую стандартный ответ")
                                response = f"👋 Здравствуйте, {user_name}!\n\nМеня зовут Елена, я менеджер компании Textile Pro.\n\nВы сказали: {transcribed_text}\n\nПодготовлю ответ на ваш вопрос!"
                            
                            # Отправляем ответ через Business API
                            logger.info(f"📤 Отправляю business voice ответ...")
                            if business_connection_id:
                                logger.info(f"📤 Отправляю через Business API с connection_id='{business_connection_id}'")
                                result = send_business_message(chat_id, response, business_connection_id)
                                if result:
                                    logger.info(f"✅ Business voice ответ отправлен в чат {chat_id}")
                                else:
                                    logger.error(f"❌ Не удалось отправить business voice ответ через Business API")
                            else:
                                logger.error(f"❌ КРИТИЧНО: Business voice без connection_id! chat_id={chat_id}")
                                # Fallback: отправляем как обычное сообщение
                                bot.send_message(chat_id, response)
                                logger.warning(f"⚠️ Business voice ответ отправлен как обычное сообщение")
                        
                        else:
                            # Ошибка обработки голоса
                            logger.error(f"❌ Ошибка обработки business голоса: {voice_result['error']}")
                            error_message = "Извините, не удалось обработать голосовое сообщение. Попробуйте написать текстом.\n\nЕлена, Textile Pro"
                            
                            if business_connection_id:
                                result = send_business_message(chat_id, error_message, business_connection_id)
                                if result:
                                    logger.info(f"✅ Business voice error отправлено через Business API")
                                else:
                                    bot.send_message(chat_id, error_message)
                                    logger.warning(f"⚠️ Business voice error отправлено как обычное сообщение")
                            else:
                                bot.send_message(chat_id, error_message)
                                logger.warning(f"⚠️ Business voice error отправлено БЕЗ Business API")
                    else:
                        logger.error("❌ Не найдены данные business голосового сообщения")
                        
                except Exception as business_voice_error:
                    logger.error(f"❌ Критическая ошибка обработки business голоса: {business_voice_error}")
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            # Business вложения без текста (кроме голосовых) - ИГНОРИРУЕМ
            elif attachments:
                logger.info(f"📎 Business вложения проигнорированы (не отвечаем): {attachments}")
                print(f"📎 Business attachments ignored: {attachments}")
                # НЕ отправляем никаких ответов на business вложения (кроме голосовых)
        
        # === BUSINESS CONNECTION ===
        elif "business_connection" in update_dict:
            conn = update_dict["business_connection"]
            is_enabled = conn.get("is_enabled", False)
            user_name = conn.get("user", {}).get("first_name", "Пользователь")
            
            status = "✅ Подключен" if is_enabled else "❌ Отключен"
            logger.info(f"{status} к Business аккаунту: {user_name}")
        
        return {"ok": True, "status": "processed", "update_id": update_counter}
        
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return {"ok": False, "error": str(e)}

@app.on_event("startup")
async def startup():
    """Запуск сервера"""
    print("\n" + "="*50)
    print("🚀 ARTYOM INTEGRATOR WEBHOOK SERVER")
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
        print(f"🎤 Voice Service: {'✅ ВКЛЮЧЕН' if voice_service else '❌ ОТКЛЮЧЕН'}")
        print(f"📱 SocialMedia: {'✅ ВКЛЮЧЕН' if SOCIAL_MEDIA_ENABLED else '❌ ОТКЛЮЧЕН'}")
        print(f"🔑 OpenAI API: {'✅ Настроен' if os.getenv('OPENAI_API_KEY') else '❌ Не настроен'}")
        print(f"🔑 Admin: {'✅ Настроен' if os.getenv('ADMIN_USER_ID') else '❌ Не настроен'}")
        print(f"🔑 VOICE_ENABLED: {VOICE_ENABLED}")
        print(f"🔑 voice_service object: {voice_service}")
        
        # Информация о SocialMedia
        if SOCIAL_MEDIA_ENABLED:
            print(f"📊 SocialMedia платформы: {social_media_service.get_available_platforms()}")
            print(f"🎥 YouTube: {'✅' if social_media_service.youtube_enabled else '❌'}")
            print(f"📸 Instagram: {'✅' if social_media_service.instagram_enabled else '❌'}")
            print(f"🎵 TikTok: {'✅' if social_media_service.tiktok_enabled else '❌'}")
        
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
            webhook_url = os.getenv("WEBHOOK_URL", "https://artyom-integrator-production.up.railway.app/webhook")
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
    logger.info("🛑 Остановка Artyom Integrator Webhook Server")
    print("🛑 Сервер остановлен")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)