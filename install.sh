#!/bin/bash

# Artem Integrator - Автоматическая установка
# Скрипт для быстрой установки и настройки бота для покупателей

set -e  # Останавливаемся при ошибках

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Иконки
SUCCESS="✅"
ERROR="❌"
WARNING="⚠️"
INFO="ℹ️"

echo -e "${BLUE}🚀 Установка Artem Integrator Bot${NC}"
echo "=================================================="

# Функция для вывода сообщений
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}${SUCCESS} ${message}${NC}"
            ;;
        "error")
            echo -e "${RED}${ERROR} ${message}${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}${WARNING} ${message}${NC}"
            ;;
        "info")
            echo -e "${BLUE}${INFO} ${message}${NC}"
            ;;
    esac
}

# Проверка операционной системы
check_os() {
    print_status "info" "Проверка операционной системы..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_status "success" "Обнаружен Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_status "success" "Обнаружен macOS"
    else
        print_status "error" "Неподдерживаемая ОС: $OSTYPE"
        exit 1
    fi
}

# Проверка и установка зависимостей
install_dependencies() {
    print_status "info" "Проверка зависимостей..."
    
    # Проверяем Python 3.8+
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
        print_status "success" "Python найден: $(python3 --version)"
    else
        print_status "error" "Python 3.8+ не найден"
        
        if [[ "$OS" == "linux" ]]; then
            print_status "info" "Установка Python..."
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv
        elif [[ "$OS" == "macos" ]]; then
            print_status "info" "Установите Python через Homebrew: brew install python"
            exit 1
        fi
    fi
    
    # Проверяем Node.js
    if command -v node &> /dev/null; then
        print_status "success" "Node.js найден: $(node --version)"
    else
        print_status "error" "Node.js не найден"
        
        if [[ "$OS" == "linux" ]]; then
            print_status "info" "Установка Node.js..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt-get install -y nodejs
        elif [[ "$OS" == "macos" ]]; then
            print_status "info" "Установите Node.js: brew install node"
            exit 1
        fi
    fi
    
    # Проверяем Git
    if command -v git &> /dev/null; then
        print_status "success" "Git найден: $(git --version)"
    else
        print_status "error" "Git не найден"
        
        if [[ "$OS" == "linux" ]]; then
            sudo apt install -y git
        elif [[ "$OS" == "macos" ]]; then
            print_status "info" "Установите Git: xcode-select --install"
            exit 1
        fi
    fi
}

# Настройка виртуального окружения Python
setup_python_env() {
    print_status "info" "Настройка Python окружения..."
    
    # Создаем виртуальное окружение
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "success" "Виртуальное окружение создано"
    fi
    
    # Активируем окружение
    source venv/bin/activate
    
    # Обновляем pip
    pip install --upgrade pip
    
    # Устанавливаем зависимости
    if [ -f "requirements.txt" ]; then
        print_status "info" "Установка Python зависимостей..."
        pip install -r requirements.txt
        print_status "success" "Python зависимости установлены"
    else
        print_status "warning" "Файл requirements.txt не найден"
    fi
}

# Создание .env файла
setup_env_file() {
    print_status "info" "Настройка переменных окружения..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "success" "Скопирован .env.example в .env"
        else
            # Создаем базовый .env файл
            cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_SECRET_TOKEN=auto_generated_secret_token

# Anthropic API
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# MCP Settings
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

# Debug & Features
DEBUG=false
VOICE_ENABLED=true
EOF
            print_status "success" "Создан базовый .env файл"
        fi
        
        print_status "warning" "⚠️  ВАЖНО: Заполните переменные в .env файле!"
        print_status "info" "Откройте .env файл и добавьте ваши API ключи"
    else
        print_status "info" ".env файл уже существует"
    fi
}

# Настройка MCP серверов
setup_mcp() {
    print_status "info" "Настройка MCP серверов..."
    
    # Активируем виртуальное окружение
    source venv/bin/activate
    
    # Запускаем скрипт настройки MCP
    if [ -f "scripts/setup_mcp.py" ]; then
        python3 scripts/setup_mcp.py
    else
        print_status "warning" "Скрипт setup_mcp.py не найден, пропускаем настройку MCP"
    fi
}

# Проверка настройки
validate_installation() {
    print_status "info" "Проверка установки..."
    
    # Проверяем .env файл
    if [ -f ".env" ]; then
        if grep -q "your_.*_here" .env; then
            print_status "warning" "В .env файле остались placeholder значения"
            print_status "info" "Не забудьте заполнить реальные API ключи!"
        else
            print_status "success" ".env файл настроен"
        fi
    fi
    
    # Проверяем виртуальное окружение
    if [ -d "venv" ]; then
        print_status "success" "Python окружение готово"
    fi
    
    # Проверяем основные файлы
    required_files=("run_bot.py" "bot/webhook/app.py" "data/mcp-servers.json")
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            print_status "success" "Файл $file найден"
        else
            print_status "error" "Отсутствует файл: $file"
        fi
    done
}

# Создание системного сервиса (опционально)
create_service() {
    if [ "$OS" != "linux" ]; then
        return
    fi
    
    read -p "Создать systemd сервис для автозапуска? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "info" "Создание systemd сервиса..."
        
        SERVICE_FILE="/etc/systemd/system/artem-integrator.service"
        CURRENT_DIR=$(pwd)
        USER=$(whoami)
        
        sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Artem Integrator Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable artem-integrator.service
        
        print_status "success" "Systemd сервис создан и включен"
        print_status "info" "Команды управления:"
        print_status "info" "  sudo systemctl start artem-integrator"
        print_status "info" "  sudo systemctl stop artem-integrator"
        print_status "info" "  sudo systemctl status artem-integrator"
    fi
}

# Показать инструкции по запуску
show_instructions() {
    echo
    echo "=================================================="
    print_status "success" "🎉 Установка завершена!"
    echo "=================================================="
    echo
    print_status "info" "Следующие шаги:"
    echo
    echo "1. Заполните .env файл вашими API ключами:"
    echo "   nano .env"
    echo
    echo "2. Активируйте виртуальное окружение:"
    echo "   source venv/bin/activate"
    echo
    echo "3. Запустите бота:"
    echo "   python run_bot.py"
    echo
    echo "4. Или запустите как сервис (Linux):"
    echo "   sudo systemctl start artem-integrator"
    echo
    print_status "info" "Документация: doc/MCP_SETUP.md"
    print_status "info" "Поддержка: README.md"
    echo
}

# Основная функция
main() {
    # Проверяем, что мы в корне проекта
    if [ ! -f "run_bot.py" ] && [ ! -f "bot/webhook/app.py" ]; then
        print_status "error" "Запустите скрипт из корневой директории проекта"
        exit 1
    fi
    
    check_os
    install_dependencies
    setup_python_env
    setup_env_file
    setup_mcp
    validate_installation
    create_service
    show_instructions
}

# Запуск установки
main "$@"