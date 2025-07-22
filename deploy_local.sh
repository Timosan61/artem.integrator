#!/bin/bash

# Локальный деплой Artem Integrator (запускается прямо на сервере)

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
APP_PATH="/home/coder/artem-integrator"
SERVICE_NAME="artem-integrator"
GITHUB_REPO="https://github.com/Timosan61/artem.integrator.git"
CURRENT_IP=$(curl -s ifconfig.me)

# Функция для вывода статуса
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Установка зависимостей
install_dependencies() {
    print_status "Установка системных зависимостей..."
    
    # Обновление системы
    sudo apt-get update
    
    # Установка необходимых пакетов
    sudo apt-get install -y \
        python3-venv \
        nginx \
        certbot \
        python3-certbot-nginx \
        supervisor
    
    # Проверка Node.js (уже установлен)
    if ! command -v node &> /dev/null; then
        print_status "Установка Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    else
        print_success "Node.js уже установлен: $(node --version)"
    fi
    
    print_success "Зависимости установлены"
}

# Настройка приложения
setup_application() {
    print_status "Настройка приложения..."
    
    # Создание директории приложения
    mkdir -p ${APP_PATH}
    cd ${APP_PATH}
    
    # Клонирование или обновление репозитория
    if [ -d ".git" ]; then
        print_status "Обновление существующего репозитория..."
        git pull origin main
    else
        print_status "Клонирование репозитория..."
        git clone ${GITHUB_REPO} .
    fi
    
    # Переключение на ветку MCP
    git checkout MCP || git checkout -b MCP origin/MCP
    
    # Создание виртуального окружения
    if [ ! -d "venv" ]; then
        print_status "Создание виртуального окружения..."
        python3 -m venv venv
    fi
    
    # Активация и установка зависимостей
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Создание директорий
    mkdir -p logs
    mkdir -p data
    
    print_success "Приложение настроено"
}

# Настройка конфигурации
setup_config() {
    print_status "Настройка конфигурации..."
    
    if [ ! -f "${APP_PATH}/.env" ]; then
        print_status "Создание .env файла..."
        cat > ${APP_PATH}/.env << EOF
# Telegram Settings
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
TELEGRAM_WEBHOOK_URL=https://${CURRENT_IP}/webhook

# OpenAI Settings
OPENAI_API_KEY=your_openai_key_here

# Anthropic Settings (для MCP)
ANTHROPIC_API_KEY=your_anthropic_key_here
ANTHROPIC_ENABLED=true

# MCP Settings
MCP_ENABLED=true

# Supabase MCP
SUPABASE_ENABLED=true
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# DigitalOcean MCP
DIGITALOCEAN_ENABLED=true
DIGITALOCEAN_TOKEN=your_do_token

# Context7 MCP
CONTEXT7_ENABLED=true

# Voice Service
VOICE_ENABLED=true

# Admin Users
ADMIN_IDS=your_telegram_id_here

# Server Settings
APP_HOST=0.0.0.0
APP_PORT=8000
ENVIRONMENT=production
EOF
        print_warning "Не забудьте обновить .env файл с реальными токенами!"
    else
        print_success ".env файл уже существует"
    fi
}

# Настройка systemd сервиса
setup_systemd() {
    print_status "Настройка systemd сервиса..."
    
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Artem Integrator Telegram Bot
After=network.target

[Service]
Type=simple
User=coder
WorkingDirectory=${APP_PATH}
Environment="PATH=${APP_PATH}/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=${APP_PATH}/venv/bin/python -m uvicorn bot.webhook:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Логирование
StandardOutput=append:${APP_PATH}/logs/bot.log
StandardError=append:${APP_PATH}/logs/bot_error.log

# Ограничения
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    # Перезагрузка systemd и запуск сервиса
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    
    print_success "Systemd сервис настроен"
}

# Настройка Nginx
setup_nginx() {
    print_status "Настройка Nginx..."
    
    # Создание конфигурации Nginx
    sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null << EOF
server {
    listen 80;
    server_name ${CURRENT_IP};

    location /webhook {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Таймауты для длинных запросов
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Активация конфигурации
    sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx
    
    print_success "Nginx настроен"
}

# Главная функция
main() {
    echo "🚀 Начинаем локальный деплой Artem Integrator"
    echo "=============================================="
    echo "Сервер IP: ${CURRENT_IP}"
    echo ""
    
    # Основные шаги деплоя
    install_dependencies
    setup_application
    setup_config
    setup_systemd
    setup_nginx
    
    echo ""
    echo "✅ Деплой завершен!"
    echo ""
    echo "📋 Дальнейшие шаги:"
    echo "1. Обновите .env файл с реальными токенами:"
    echo "   nano ${APP_PATH}/.env"
    echo ""
    echo "2. Запустите сервис:"
    echo "   sudo systemctl start ${SERVICE_NAME}"
    echo ""
    echo "3. Проверьте статус:"
    echo "   sudo systemctl status ${SERVICE_NAME}"
    echo ""
    echo "4. Настройте webhook в Telegram после запуска бота"
    echo ""
    echo "📊 Полезные команды:"
    echo "   Логи: tail -f ${APP_PATH}/logs/bot.log"
    echo "   Статус: sudo systemctl status ${SERVICE_NAME}"
    echo "   Рестарт: sudo systemctl restart ${SERVICE_NAME}"
    echo "   Nginx логи: sudo tail -f /var/log/nginx/error.log"
}

# Запуск скрипта
main "$@"