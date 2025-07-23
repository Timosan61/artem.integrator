#!/usr/bin/env python3
"""
Тест прямого вызова MCP сервера без SDK
"""
import subprocess
import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def call_digitalocean_mcp():
    """Вызов DigitalOcean MCP напрямую через npx"""
    
    # Получаем токен
    token = os.getenv("DIGITALOCEAN_API_TOKEN")
    if not token:
        print("❌ DIGITALOCEAN_API_TOKEN не найден в .env")
        return
    
    print(f"✅ Токен найден: {token[:10]}...")
    
    # Команда для запуска MCP сервера и вызова функции
    # MCP серверы работают через JSON-RPC
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "mcp__digitalocean__list_apps",
            "arguments": {"query": {}}
        },
        "id": 1
    }
    
    # Запускаем MCP сервер
    env = os.environ.copy()
    env["DIGITALOCEAN_API_TOKEN"] = token
    
    print("\n🚀 Запускаем DigitalOcean MCP сервер...")
    
    try:
        # Проверяем доступность пакета
        check_cmd = ["npx", "-y", "@digitalocean/mcp", "--version"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        print(f"📦 Проверка пакета: {result.stdout.strip() if result.returncode == 0 else result.stderr}")
        
        # Пробуем выполнить команду напрямую
        # MCP серверы обычно принимают команды через stdin
        cmd = ["npx", "-y", "@digitalocean/mcp"]
        
        print(f"\n📨 Отправляем запрос: {json.dumps(mcp_request, indent=2)}")
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Отправляем JSON-RPC запрос
        stdout, stderr = process.communicate(input=json.dumps(mcp_request))
        
        print(f"\n📊 Результат:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        print(f"Return code: {process.returncode}")
        
        # Пробуем распарсить ответ
        if stdout:
            try:
                response = json.loads(stdout)
                print(f"\n✅ Ответ получен: {json.dumps(response, indent=2)}")
            except json.JSONDecodeError:
                print(f"\n⚠️ Не удалось распарсить JSON ответ")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    call_digitalocean_mcp()