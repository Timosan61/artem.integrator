#!/usr/bin/env python3
"""
Прямой тест DigitalOcean MCP без SDK
"""

import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

# Проверяем наличие токена
token = os.getenv("DIGITALOCEAN_API_TOKEN")
print(f"DigitalOcean Token: {'✅' if token else '❌'}")

if token:
    # Пробуем запустить MCP сервер напрямую
    cmd = ["npx", "-y", "@anysphere/digitalocean-mcp"]
    env = os.environ.copy()
    env["DIGITALOCEAN_API_TOKEN"] = token
    
    print("\n🚀 Запуск DigitalOcean MCP сервера...")
    print(f"Команда: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        print(f"\nКод возврата: {result.returncode}")
        print(f"Stdout: {result.stdout[:500]}")
        print(f"Stderr: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout - сервер запустился (это нормально для MCP)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")