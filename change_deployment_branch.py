#!/usr/bin/env python3
"""
Скрипт для изменения ветки деплоя приложения DigitalOcean через API

Изменяет ветку с main на refactoring для развертывания очищенной версии
"""

import json
import os
import sys
import requests
from typing import Dict, Any

# Конфигурация
APP_ID = "38929bac-dfee-41b5-8b8c-ad710efd81aa"
NEW_BRANCH = "refactoring"
OLD_BRANCH = "main"

def get_digitalocean_token():
    """Получает токен DigitalOcean из переменных окружения или файла"""
    token = os.getenv('DIGITALOCEAN_TOKEN')
    if token:
        return token
    
    # Пробуем прочитать из локального файла
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('DIGITALOCEAN_TOKEN='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    
    return None

def get_app_spec(app_id: str, token: str) -> Dict[str, Any]:
    """Получает текущую спецификацию приложения"""
    url = f"https://api.digitalocean.com/v2/apps/{app_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"📥 Получаем текущую конфигурацию приложения {app_id}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Ошибка получения приложения: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    app_data = response.json()
    print(f"✅ Конфигурация получена успешно")
    
    return app_data["app"]

def update_app_branch(app_id: str, token: str, app_spec: Dict[str, Any], new_branch: str) -> bool:
    """Обновляет ветку в спецификации приложения"""
    # Находим сервис с GitHub репозиторием
    updated = False
    
    for service in app_spec["spec"]["services"]:
        if "github" in service:
            old_branch = service["github"]["branch"]
            service["github"]["branch"] = new_branch
            print(f"🔄 Изменяем ветку сервиса '{service['name']}': {old_branch} → {new_branch}")
            updated = True
    
    if not updated:
        print("❌ Не найден сервис с GitHub интеграцией")
        return False
    
    # Отправляем обновленную спецификацию
    url = f"https://api.digitalocean.com/v2/apps/{app_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Подготавливаем данные для обновления (только spec нужен)
    update_data = {
        "spec": app_spec["spec"]
    }
    
    print(f"📤 Отправляем обновленную конфигурацию...")
    response = requests.put(url, headers=headers, json=update_data)
    
    if response.status_code != 200:
        print(f"❌ Ошибка обновления приложения: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print(f"✅ Приложение успешно обновлено!")
    return True

def get_deployment_status(app_id: str, token: str) -> Dict[str, Any]:
    """Получает статус деплоя приложения"""
    url = f"https://api.digitalocean.com/v2/apps/{app_id}/deployments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Ошибка получения деплоев: {response.status_code}")
        return None
    
    deployments = response.json()["deployments"]
    if deployments:
        latest = deployments[0]  # Самый новый деплой
        return {
            "id": latest["id"],
            "phase": latest["phase"],
            "cause": latest.get("cause", "Unknown"),
            "created_at": latest["created_at"],
            "commit_hash": latest["services"][0].get("source_commit_hash", "Unknown") if latest["services"] else "Unknown"
        }
    
    return None

def wait_for_deployment(app_id: str, token: str, timeout_minutes: int = 10):
    """Ожидает завершения деплоя"""
    import time
    
    print(f"⏳ Ожидаем завершения деплоя (таймаут: {timeout_minutes} минут)...")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while time.time() - start_time < timeout_seconds:
        status = get_deployment_status(app_id, token)
        if not status:
            print("❌ Не удалось получить статус деплоя")
            break
        
        phase = status["phase"]
        print(f"📊 Статус деплоя: {phase} (ID: {status['id'][:8]}...)")
        
        if phase == "ACTIVE":
            print(f"✅ Деплой успешно завершен!")
            print(f"📝 Commit: {status['commit_hash'][:8]}...")
            return True
        elif phase == "ERROR":
            print(f"❌ Деплой завершился с ошибкой")
            return False
        
        time.sleep(30)  # Проверяем каждые 30 секунд
    
    print(f"⏰ Таймаут ожидания деплоя ({timeout_minutes} минут)")
    return False

def main():
    """Основная функция"""
    print("🚀 Изменение ветки деплоя DigitalOcean App Platform")
    print("=" * 60)
    
    # Проверяем наличие токена
    token = get_digitalocean_token()
    if not token:
        print("❌ DIGITALOCEAN_TOKEN не найден в переменных окружения или .env файле")
        print("💡 Установите токен:")
        print("   export DIGITALOCEAN_TOKEN=your_token_here")
        sys.exit(1)
    
    print(f"🔐 Токен DigitalOcean найден")
    print(f"📱 ID приложения: {APP_ID}")
    print(f"🌿 Текущая ветка: {OLD_BRANCH}")
    print(f"🌿 Новая ветка: {NEW_BRANCH}")
    print()
    
    # Получаем текущую конфигурацию
    app_spec = get_app_spec(APP_ID, token)
    if not app_spec:
        sys.exit(1)
    
    # Показываем текущую ветку
    current_branch = None
    for service in app_spec["spec"]["services"]:
        if "github" in service:
            current_branch = service["github"]["branch"]
            print(f"📋 Текущая ветка сервиса '{service['name']}': {current_branch}")
    
    if current_branch == NEW_BRANCH:
        print(f"✅ Приложение уже использует ветку '{NEW_BRANCH}'")
        return
    
    # Подтверждение от пользователя
    print(f"\n⚠️  ВНИМАНИЕ: Изменение ветки запустит новый деплой!")
    print(f"   Приложение будет пересобрано из ветки '{NEW_BRANCH}'")
    
    confirm = input(f"\n❓ Продолжить изменение ветки с '{current_branch}' на '{NEW_BRANCH}'? (y/N): ")
    if confirm.lower() not in ['y', 'yes', 'да']:
        print("❌ Операция отменена пользователем")
        return
    
    print()
    
    # Обновляем ветку
    if update_app_branch(APP_ID, token, app_spec, NEW_BRANCH):
        print(f"🎉 Ветка успешно изменена на '{NEW_BRANCH}'!")
        print(f"🔄 Автоматический деплой должен начаться в течение минуты...")
        
        # Ожидаем завершения деплоя
        if wait_for_deployment(APP_ID, token):
            print(f"\n🎯 Деплой завершен успешно!")
            print(f"🌐 Приложение доступно по адресу:")
            print(f"   https://artemintegrator-nahdj.ondigitalocean.app")
            print(f"\n📊 Теперь приложение работает с очищенной версией из ветки '{NEW_BRANCH}'")
        else:
            print(f"\n⚠️  Деплой не завершился в ожидаемое время")
            print(f"🔍 Проверьте статус вручную через ./get_digitalocean_logs.sh")
    else:
        print(f"❌ Не удалось изменить ветку")
        sys.exit(1)

if __name__ == "__main__":
    main()