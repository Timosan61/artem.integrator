#!/usr/bin/env python3
"""
Скрипт для установки локального webhook через ngrok
"""
import os
import requests
import json
import time
import subprocess
import sys

# Конфигурация
TELEGRAM_BOT_TOKEN = "6658269281:AAETA0vTXiRCMPcL1y_DzEeU_Fc6DiqdpFk"
WEBHOOK_SECRET = "79c08d0ee7c19026653b6aa365b731cc2c23699f3a52aec8fc89be28990af77e"
NGROK_API_KEY = "2zWyBoccEWDF7IEs0kp1z7MRldl_5qwwZ9pCYEA9LRwuhKSEh"

def get_ngrok_url():
    """Получает публичный URL от ngrok"""
    try:
        # Проверяем запущен ли ngrok
        response = requests.get("http://localhost:4040/api/tunnels")
        tunnels = response.json()["tunnels"]
        
        for tunnel in tunnels:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        
        # Если нет https, берем http
        if tunnels:
            return tunnels[0]["public_url"]
            
    except:
        return None
    
    return None

def start_ngrok():
    """Запускает ngrok"""
    print("🚀 Запуск ngrok...")
    
    # Устанавливаем API ключ
    os.environ["NGROK_AUTHTOKEN"] = NGROK_API_KEY
    
    # Запускаем ngrok в фоновом режиме
    subprocess.Popen(
        ["ngrok", "http", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Ждем пока ngrok запустится
    for i in range(10):
        time.sleep(2)
        url = get_ngrok_url()
        if url:
            print(f"✅ Ngrok запущен: {url}")
            return url
    
    print("❌ Не удалось запустить ngrok")
    return None

def delete_webhook():
    """Удаляет текущий webhook"""
    print("🗑️ Удаление старого webhook...")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    response = requests.post(url)
    
    if response.ok:
        print("✅ Старый webhook удален")
    else:
        print(f"⚠️ Ошибка удаления webhook: {response.text}")

def set_webhook(webhook_url):
    """Устанавливает новый webhook"""
    print(f"📌 Установка webhook: {webhook_url}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    data = {
        "url": f"{webhook_url}/webhook/telegram",
        "secret_token": WEBHOOK_SECRET,
        "allowed_updates": [
            "message",
            "callback_query",
            "business_message",
            "business_connection"
        ],
        "drop_pending_updates": True
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get("ok"):
        print("✅ Webhook установлен успешно!")
        return True
    else:
        print(f"❌ Ошибка установки webhook: {result}")
        return False

def check_webhook():
    """Проверяет статус webhook"""
    print("\n📊 Проверка webhook...")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    info = response.json()["result"]
    
    print("\n=== Webhook Info ===")
    print(f"URL: {info.get('url', 'Not set')}")
    print(f"Has secret token: {info.get('has_custom_certificate', False)}")
    print(f"Pending updates: {info.get('pending_update_count', 0)}")
    
    if info.get("last_error_message"):
        print(f"❌ Last error: {info['last_error_message']}")
        print(f"   Error date: {info.get('last_error_date', 'Unknown')}")
    
    return info

def main():
    """Главная функция"""
    print("🤖 Artyom Integrator - Local Webhook Setup")
    print("=" * 50)
    
    # Проверяем запущен ли webhook сервер
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code != 200:
            print("❌ Webhook сервер не отвечает на localhost:8000")
            print("   Запустите: python webhook.py")
            sys.exit(1)
        print("✅ Webhook сервер работает на localhost:8000")
    except:
        print("❌ Webhook сервер не запущен!")
        print("   Запустите: python webhook.py")
        sys.exit(1)
    
    # Получаем или запускаем ngrok
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        ngrok_url = start_ngrok()
        if not ngrok_url:
            sys.exit(1)
    
    # Удаляем старый webhook
    delete_webhook()
    time.sleep(1)
    
    # Устанавливаем новый webhook
    if set_webhook(ngrok_url):
        # Проверяем статус
        time.sleep(2)
        info = check_webhook()
        
        print("\n✅ Webhook готов к работе!")
        print(f"\n📱 Теперь можете отправить сообщение боту @artem_integrator_bot")
        print(f"   Ngrok URL: {ngrok_url}")
        print(f"   Webhook URL: {ngrok_url}/webhook/telegram")
        
        print("\n💡 Для мониторинга:")
        print(f"   - Ngrok UI: http://localhost:4040")
        print(f"   - Webhook logs: tail -f webhook.log")
        print(f"   - Debug endpoint: {ngrok_url}/debug/last-updates")
    else:
        print("\n❌ Не удалось установить webhook")
        sys.exit(1)

if __name__ == "__main__":
    main()