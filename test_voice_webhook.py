#!/usr/bin/env python3
"""
Тест симуляции голосового сообщения для отладки webhook
"""

import json
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simulate_voice_message():
    """Симуляция обработки голосового сообщения"""
    
    # Импортируем функции из webhook
    from webhook import has_attachments, voice_service, VOICE_ENABLED, AI_ENABLED
    
    print("=== VOICE MESSAGE SIMULATION ===")
    print(f"🔑 VOICE_ENABLED: {VOICE_ENABLED}")
    print(f"🔑 AI_ENABLED: {AI_ENABLED}")
    print(f"🔑 voice_service: {voice_service}")
    print(f"🔑 voice_service type: {type(voice_service)}")
    
    # Симулируем структуру голосового сообщения как в Telegram
    voice_message = {
        "message_id": 12345,
        "from": {
            "id": 123456789,
            "is_bot": False,
            "first_name": "Тест",
            "username": "test_user",
            "language_code": "ru"
        },
        "chat": {
            "id": 123456789,
            "first_name": "Тест",
            "username": "test_user",
            "type": "private"
        },
        "date": 1642000000,
        "voice": {
            "duration": 3,
            "mime_type": "audio/ogg",
            "file_id": "AwACAgIAAxkBAAICE2KTestVoiceFileId",
            "file_unique_id": "AgADEhNiVoiceTest",
            "file_size": 15234
        }
    }
    
    print(f"\n📨 Симуляция сообщения:")
    print(json.dumps(voice_message, ensure_ascii=False, indent=2))
    
    # Проверяем has_attachments
    print(f"\n🔍 Проверка has_attachments:")
    attachments, attachments_details = has_attachments(voice_message)
    print(f"📎 attachments: {attachments}")
    print(f"📋 attachments_details: {attachments_details}")
    print(f"🎤 'voice' in attachments: {'voice' in attachments}")
    
    # Проверяем условие
    condition_result = 'voice' in attachments and voice_service
    print(f"\n✅ Условие 'voice' in attachments and voice_service: {condition_result}")
    
    if condition_result:
        print("🎉 Голосовое сообщение ДОЛЖНО обрабатываться!")
        # Найдем voice данные
        voice_data = None
        for detail in attachments_details:
            if detail['type'] == 'voice':
                voice_data = detail
                break
        print(f"🎤 Voice data: {voice_data}")
    else:
        print("❌ Голосовое сообщение НЕ будет обрабатываться!")
        if 'voice' not in attachments:
            print("   - 'voice' НЕ найден в attachments")
        if not voice_service:
            print("   - voice_service НЕ инициализирован")
    
    # Дополнительные проверки
    print(f"\n🔧 Дополнительные проверки:")
    try:
        from voice import VoiceService
        print(f"✅ VoiceService импортируется успешно")
        
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if telegram_token and openai_key:
            test_service = VoiceService(telegram_token, openai_key)
            print(f"✅ VoiceService создается успешно")
            info = test_service.get_service_info()
            print(f"📋 Service info: {info}")
        else:
            print(f"❌ Отсутствуют API ключи")
            
    except Exception as e:
        print(f"❌ Ошибка VoiceService: {e}")

if __name__ == "__main__":
    simulate_voice_message()