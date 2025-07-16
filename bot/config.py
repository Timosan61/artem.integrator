import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ZEP_API_KEY = os.getenv('ZEP_API_KEY')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Админские настройки
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')
ADMIN_USERNAMES = os.getenv('ADMIN_USERNAMES', '').split(',')

# SocialMedia API ключи
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
INSTAGRAM_API_KEY = os.getenv('INSTAGRAM_API_KEY')
TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')

# Абсолютный путь к файлу инструкций
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTRUCTION_FILE = os.path.join(BASE_DIR, 'data', 'instruction.json')
OPENAI_MODEL = 'gpt-4o'

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

# Проверки API ключей (не критичные для запуска)
if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY не найден в переменных окружения")
if not ZEP_API_KEY:
    print("⚠️ ZEP_API_KEY не найден в переменных окружения")

# Проверки админских настроек
if ADMIN_USER_ID:
    print(f"✅ Админ настроен: User ID {ADMIN_USER_ID}")
    ADMIN_USER_ID = int(ADMIN_USER_ID)
else:
    print("⚠️ ADMIN_USER_ID не найден в переменных окружения")
    
# Проверки SocialMedia API ключей
if YOUTUBE_API_KEY:
    print(f"✅ YouTube API ключ настроен: {YOUTUBE_API_KEY[:20]}...")
else:
    print("⚠️ YOUTUBE_API_KEY не найден в переменных окружения")
    
if INSTAGRAM_API_KEY:
    print(f"✅ Instagram API ключ настроен: {INSTAGRAM_API_KEY[:20]}...")
else:
    print("⚠️ INSTAGRAM_API_KEY не найден в переменных окружения")
    
if TIKTOK_API_KEY:
    print(f"✅ TikTok API ключ настроен: {TIKTOK_API_KEY[:20]}...")
else:
    print("⚠️ TIKTOK_API_KEY не найден в переменных окружения")