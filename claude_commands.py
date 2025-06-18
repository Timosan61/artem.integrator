#!/usr/bin/env python3
"""
Команды для интеграции с Claude Code
Позволяет автоматически управлять деплоем через Portainer API
"""

import subprocess
import sys
import json
import time
from typing import Dict, Any

def run_portainer_command(command: str) -> Dict[str, Any]:
    """Выполнить команду portainer_deploy.py и вернуть результат"""
    try:
        result = subprocess.run(
            [sys.executable, "portainer_deploy.py", command],
            capture_output=True,
            text=True,
            cwd="/home/coder/Desktop/2202/Textill_PRO_BOT"
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command
        }

def deploy_bot() -> str:
    """Выполнить деплой бота"""
    print("🚀 Начинаем автоматический деплой бота...")
    
    # 1. Проверить текущий статус
    print("📊 Проверка текущего статуса...")
    status_result = run_portainer_command("status")
    
    if status_result["success"]:
        print("✅ Связь с Portainer установлена")
        try:
            status_data = json.loads(status_result["stdout"])
            if status_data.get("containers"):
                print(f"📦 Найдено контейнеров: {len(status_data['containers'])}")
        except:
            pass
    else:
        print("⚠️ Возможно, стек еще не создан")
    
    # 2. Обновить из Git
    print("🔄 Обновление из Git репозитория...")
    update_result = run_portainer_command("update")
    
    if update_result["success"]:
        print("✅ Обновление из Git выполнено")
    else:
        print("⚠️ Ошибка обновления, попробуем создать новый стек...")
        create_result = run_portainer_command("create")
        if create_result["success"]:
            print("✅ Новый стек создан")
        else:
            print("❌ Ошибка создания стека:", create_result.get("stderr", ""))
            return "❌ Деплой не удался"
    
    # 3. Подождать и проверить статус
    print("⏳ Ожидание запуска контейнеров...")
    time.sleep(10)
    
    final_status = run_portainer_command("status")
    if final_status["success"]:
        try:
            status_data = json.loads(final_status["stdout"])
            containers = status_data.get("containers", [])
            running_containers = [c for c in containers if "running" in c.get("state", "").lower()]
            
            if running_containers:
                print(f"✅ Деплой завершен! Запущено контейнеров: {len(running_containers)}")
                print("🤖 Бот готов к работе: @textilprofi_bot")
                return "✅ Деплой успешно завершен!"
            else:
                print("⚠️ Контейнеры не запустились, проверяем логи...")
                logs_result = run_portainer_command("logs")
                if logs_result["success"]:
                    print("📝 Последние логи:")
                    print(logs_result["stdout"][-500:])  # Последние 500 символов
                return "⚠️ Деплой завершен, но есть проблемы"
        except Exception as e:
            print(f"❌ Ошибка парсинга статуса: {e}")
            return "⚠️ Деплой завершен, но статус неясен"
    else:
        print("❌ Не удалось получить финальный статус")
        return "⚠️ Деплой завершен, но статус неясен"

def check_bot_status() -> str:
    """Проверить статус бота"""
    print("📊 Проверка статуса бота...")
    
    result = run_portainer_command("status")
    
    if not result["success"]:
        return f"❌ Ошибка подключения к Portainer: {result.get('stderr', 'Неизвестная ошибка')}"
    
    try:
        status_data = json.loads(result["stdout"])
        
        if "error" in status_data:
            return f"❌ {status_data['error']}"
        
        containers = status_data.get("containers", [])
        if not containers:
            return "⚠️ Контейнеры не найдены. Возможно, стек не создан."
        
        status_info = []
        status_info.append(f"📦 Стек: {status_data.get('stack_name', 'unknown')}")
        status_info.append(f"🆔 ID: {status_data.get('stack_id', 'unknown')}")
        status_info.append(f"📊 Статус стека: {status_data.get('status', 'unknown')}")
        status_info.append("")
        
        for container in containers:
            name = container.get("name", "unknown")
            state = container.get("state", "unknown")
            status = container.get("status", "unknown")
            
            if "running" in state.lower():
                emoji = "✅"
            elif "exited" in state.lower():
                emoji = "❌"
            else:
                emoji = "⚠️"
            
            status_info.append(f"{emoji} {name}: {state} ({status})")
        
        return "\n".join(status_info)
    
    except json.JSONDecodeError:
        return f"⚠️ Получен некорректный ответ от API:\n{result['stdout'][:200]}..."
    except Exception as e:
        return f"❌ Ошибка обработки статуса: {e}"

def show_bot_logs() -> str:
    """Показать логи бота"""
    print("📝 Получение логов бота...")
    
    result = run_portainer_command("logs")
    
    if not result["success"]:
        return f"❌ Ошибка получения логов: {result.get('stderr', 'Неизвестная ошибка')}"
    
    logs = result["stdout"]
    if not logs.strip():
        return "📝 Логи пусты или недоступны"
    
    # Возвращаем последние 1000 символов логов
    return f"📝 Последние логи бота:\n\n{logs[-1000:]}"

def restart_bot() -> str:
    """Перезапустить бота"""
    print("🔄 Перезапуск бота...")
    
    result = run_portainer_command("restart")
    
    if result["success"]:
        print("✅ Команда перезапуска отправлена")
        print("⏳ Ожидание перезапуска...")
        time.sleep(15)
        
        # Проверяем статус после перезапуска
        status = check_bot_status()
        return f"🔄 Перезапуск выполнен\n\n{status}"
    else:
        return f"❌ Ошибка перезапуска: {result.get('stderr', 'Неизвестная ошибка')}"

# Команды для Claude Code
def execute_claude_command(command: str) -> str:
    """Выполнить команду от Claude Code"""
    
    command = command.lower().strip()
    
    if command in ["deploy", "деплой", "обнови", "update"]:
        return deploy_bot()
    
    elif command in ["status", "статус", "проверь"]:
        return check_bot_status()
    
    elif command in ["logs", "логи", "покажи логи"]:
        return show_bot_logs()
    
    elif command in ["restart", "перезапуск", "перезапусти"]:
        return restart_bot()
    
    else:
        return f"""❌ Неизвестная команда: {command}

Доступные команды:
🚀 deploy/деплой - выполнить деплой
📊 status/статус - проверить статус  
📝 logs/логи - показать логи
🔄 restart/перезапуск - перезапустить бота"""

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        result = execute_claude_command(command)
        print(result)
    else:
        print("Использование: python claude_commands.py <команда>")
        print("Пример: python claude_commands.py deploy")