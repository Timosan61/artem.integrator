#!/usr/bin/env python3
"""
Скрипт автоматической настройки MCP для Claude Code SDK

Автоматически:
1. Устанавливает необходимые MCP пакеты
2. Создает конфигурацию для Claude Code SDK
3. Настраивает переменные окружения
4. Копирует конфигурацию в системную директорию
"""

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

def print_status(message: str, status: str = "info"):
    """Выводит цветное сообщение статуса"""
    colors = {
        "info": "\033[94m",     # Blue
        "success": "\033[92m",  # Green
        "warning": "\033[93m",  # Yellow
        "error": "\033[91m",    # Red
        "reset": "\033[0m"      # Reset
    }
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    color = colors.get(status, colors["info"])
    icon = icons.get(status, "ℹ️")
    reset = colors["reset"]
    
    print(f"{color}{icon} {message}{reset}")

def check_requirements() -> bool:
    """Проверяет наличие необходимых инструментов"""
    print_status("Проверка требований...")
    
    # Проверяем Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"Node.js найден: {result.stdout.strip()}", "success")
        else:
            print_status("Node.js не найден. Установите Node.js 18+", "error")
            return False
    except FileNotFoundError:
        print_status("Node.js не найден. Установите Node.js 18+", "error")
        return False
    
    # Проверяем npm
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"npm найден: {result.stdout.strip()}", "success")
        else:
            print_status("npm не найден. Переустановите Node.js", "error")
            return False
    except FileNotFoundError:
        print_status("npm не найден. Переустановите Node.js", "error")
        return False
    
    # Проверяем Claude CLI
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"Claude CLI найден: {result.stdout.strip()}", "success")
        else:
            print_status("Claude CLI не найден. Установится автоматически", "warning")
    except FileNotFoundError:
        print_status("Claude CLI не найден. Установится автоматически", "warning")
    
    return True

def install_claude_cli() -> bool:
    """Устанавливает Claude CLI"""
    print_status("Установка Claude CLI...")
    
    try:
        result = subprocess.run([
            "npm", "install", "-g", "@anthropic-ai/claude-code-cli"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_status("Claude CLI успешно установлен", "success")
            return True
        else:
            print_status(f"Ошибка установки Claude CLI: {result.stderr}", "error")
            return False
    except Exception as e:
        print_status(f"Ошибка установки Claude CLI: {e}", "error")
        return False

def install_mcp_packages() -> bool:
    """Устанавливает MCP пакеты"""
    print_status("Установка MCP пакетов...")
    
    packages = [
        "@digitalocean/mcp",
        "@supabase/mcp-server", 
        "@context-labs/context7-mcp",
        "@modelcontextprotocol/server-filesystem",
        "@modelcontextprotocol/server-git"
    ]
    
    for package in packages:
        print_status(f"Установка {package}...")
        try:
            result = subprocess.run([
                "npm", "install", "-g", package
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_status(f"✓ {package} установлен", "success")
            else:
                print_status(f"⚠️ Ошибка установки {package}: {result.stderr}", "warning")
                # Продолжаем, некоторые пакеты могут быть недоступны
        except Exception as e:
            print_status(f"⚠️ Ошибка установки {package}: {e}", "warning")
    
    return True

def load_env_file(env_path: Path) -> Dict[str, str]:
    """Загружает переменные из .env файла"""
    env_vars = {}
    
    if not env_path.exists():
        print_status(f"Файл .env не найден: {env_path}", "warning")
        return env_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Убираем кавычки если есть
                    value = value.strip('"\'')
                    env_vars[key.strip()] = value
        
        print_status(f"Загружено {len(env_vars)} переменных из .env", "success")
        return env_vars
        
    except Exception as e:
        print_status(f"Ошибка чтения .env файла: {e}", "error")
        return {}

def create_mcp_config(project_root: Path, env_vars: Dict[str, str]) -> Dict[str, Any]:
    """Создает конфигурацию MCP с подставленными переменными"""
    
    # Загружаем шаблон
    template_path = project_root / "data" / "mcp-servers.json"
    if not template_path.exists():
        print_status(f"Шаблон конфигурации не найден: {template_path}", "error")
        return {}
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Подставляем переменные
        config_content = template
        for key, value in env_vars.items():
            pattern = f"{{{key}}}"
            config_content = config_content.replace(pattern, value)
        
        # Парсим JSON
        config = json.loads(config_content)
        
        # Фильтруем серверы с пустыми токенами
        filtered_servers = {}
        for server_name, server_config in config.get("mcpServers", {}).items():
            env_section = server_config.get("env", {})
            
            # Проверяем есть ли заполненные переменные
            has_valid_env = any(value.strip() for value in env_section.values()) if env_section else True
            
            if has_valid_env:
                filtered_servers[server_name] = server_config
                print_status(f"✓ Сервер {server_name} добавлен", "success")
            else:
                print_status(f"⚠️ Сервер {server_name} пропущен - нет переменных окружения", "warning")
        
        config["mcpServers"] = filtered_servers
        return config
        
    except Exception as e:
        print_status(f"Ошибка создания конфигурации: {e}", "error")
        return {}

def setup_claude_config(config: Dict[str, Any]) -> bool:
    """Настраивает конфигурацию Claude Code SDK"""
    print_status("Настройка конфигурации Claude Code SDK...")
    
    # Создаем директорию конфигурации
    config_dir = Path.home() / ".config" / "claude-code"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / "mcp.json"
    
    try:
        # Сохраняем конфигурацию
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print_status(f"Конфигурация сохранена: {config_file}", "success")
        
        # Показываем количество серверов
        server_count = len(config.get("mcpServers", {}))
        print_status(f"Настроено {server_count} MCP серверов", "info")
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка сохранения конфигурации: {e}", "error")
        return False

def validate_setup() -> bool:
    """Проверяет корректность настройки"""
    print_status("Проверка настройки...")
    
    config_file = Path.home() / ".config" / "claude-code" / "mcp.json"
    
    if not config_file.exists():
        print_status("Файл конфигурации не найден", "error")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        servers = config.get("mcpServers", {})
        if not servers:
            print_status("Нет настроенных MCP серверов", "warning")
            return False
        
        print_status("Настроенные серверы:", "info")
        for name, server_config in servers.items():
            command = server_config.get("command", "")
            args = " ".join(server_config.get("args", []))
            print(f"  • {name}: {command} {args}")
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка проверки конфигурации: {e}", "error")
        return False

def create_example_env():
    """Создает пример .env файла если его нет"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    example_file = project_root / ".env.example"
    
    if env_file.exists():
        print_status(".env файл уже существует", "info")
        return
    
    if example_file.exists():
        print_status("Копируем .env.example в .env", "info")
        shutil.copy2(example_file, env_file)
        print_status("⚠️ Не забудьте заполнить переменные в .env файле!", "warning")
    else:
        print_status("Создаем базовый .env файл", "info")
        env_content = """# MCP Configuration
MCP_ENABLED=true

# DigitalOcean Settings
DIGITALOCEAN_ENABLED=true
DIGITALOCEAN_TOKEN=your_digitalocean_token_here

# Supabase Settings  
SUPABASE_ENABLED=true
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_service_role_key_here

# Context7 Settings
CONTEXT7_ENABLED=true
CONTEXT7_API_KEY=your_context7_api_key_here

# Anthropic Settings
ANTHROPIC_API_KEY=your_anthropic_api_key_here
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print_status("⚠️ Заполните переменные в .env файле!", "warning")

def main():
    """Главная функция настройки"""
    print_status("🚀 Настройка MCP для Artem Integrator", "info")
    print_status("=" * 50, "info")
    
    # Определяем корневую директорию проекта
    project_root = Path(__file__).parent.parent
    print_status(f"Проект: {project_root}", "info")
    
    # Проверяем требования
    if not check_requirements():
        print_status("Установите требования и запустите скрипт снова", "error")
        sys.exit(1)
    
    # Устанавливаем Claude CLI если нужно
    try:
        subprocess.run(["claude", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        if not install_claude_cli():
            print_status("Не удалось установить Claude CLI", "error")
            sys.exit(1)
    
    # Создаем .env если нужно
    create_example_env()
    
    # Загружаем переменные окружения
    env_file = project_root / ".env"
    env_vars = load_env_file(env_file)
    
    if not env_vars:
        print_status("Заполните .env файл и запустите скрипт снова", "error")
        sys.exit(1)
    
    # Устанавливаем MCP пакеты
    if not install_mcp_packages():
        print_status("Ошибка установки MCP пакетов", "error")
        sys.exit(1)
    
    # Создаем конфигурацию
    config = create_mcp_config(project_root, env_vars)
    if not config:
        print_status("Не удалось создать конфигурацию", "error")
        sys.exit(1)
    
    # Настраиваем Claude Code SDK
    if not setup_claude_config(config):
        print_status("Не удалось настроить Claude Code SDK", "error")
        sys.exit(1)
    
    # Проверяем настройку
    if not validate_setup():
        print_status("Настройка завершена с предупреждениями", "warning")
    else:
        print_status("Настройка успешно завершена!", "success")
    
    print_status("=" * 50, "info")
    print_status("Теперь вы можете использовать MCP команды в боте:", "info")
    print_status("  • /mcp apps - список приложений DigitalOcean", "info")
    print_status("  • /db SELECT * FROM users - SQL запросы к Supabase", "info")
    print_status("  • /docs как использовать API - поиск в Context7", "info")

if __name__ == "__main__":
    main()