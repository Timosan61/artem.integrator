#!/bin/bash

# Deploy Artem Integrator to DigitalOcean Droplet
# Использует MCP DigitalOcean для управления деплоем

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
DROPLET_IP="104.248.39.106"
DROPLET_USER="coder"
APP_PATH="/home/coder/artem-integrator"
SERVICE_NAME="artem-integrator"
GITHUB_REPO="https://github.com/anetov/artem.integrator.git"
DOMAIN="artem.example.com"  # Измените на ваш домен

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

# Проверка наличия SSH ключа
check_ssh_key() {
    print_status "Проверка SSH доступа к droplet..."
    
    if ssh -o ConnectTimeout=5 -o BatchMode=yes ${DROPLET_USER}@${DROPLET_IP} exit 2>/dev/null; then
        print_success "SSH доступ настроен"
        return 0
    else
        print_error "SSH доступ не настроен"
        print_warning "Добавьте ваш SSH ключ на droplet или используйте ssh-copy-id"
        return 1
    fi
}

# Функция для выполнения команд на droplet
remote_exec() {
    ssh ${DROPLET_USER}@${DROPLET_IP} "$@"
}

# Копирование файлов на droplet
copy_to_droplet() {
    local source=$1
    local dest=$2
    scp -r "$source" ${DROPLET_USER}@${DROPLET_IP}:"$dest"
}

# Установка зависимостей на droplet
install_dependencies() {
    print_status "Установка зависимостей на droplet..."
    
    remote_exec << 'EOF'
    # Обновление системы
    sudo apt-get update
    sudo apt-get upgrade -y
    
    # Установка Python 3.10+
    sudo apt-get install -y python3.10 python3.10-venv python3-pip
    
    # Установка Node.js для MCP
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # Установка дополнительных инструментов
    sudo apt-get install -y git nginx certbot python3-certbot-nginx supervisor
    
    # Установка Claude Code CLI
    sudo npm install -g @anthropic/claude-code-cli
EOF
    
    print_success "Зависимости установлены"
}

# Настройка приложения
setup_application() {
    print_status "Настройка приложения..."
    
    remote_exec << EOF
    # Создание директории приложения
    mkdir -p ${APP_PATH}
    cd ${APP_PATH}
    
    # Клонирование или обновление репозитория
    if [ -d ".git" ]; then
        git pull origin main
    else
        git clone ${GITHUB_REPO} .
    fi
    
    # Создание виртуального окружения
    python3.10 -m venv venv
    
    # Активация и установка зависимостей
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Создание директорий
    mkdir -p logs
    mkdir -p data
EOF
    
    print_success "Приложение настроено"
}

# Копирование конфигурационных файлов
setup_configs() {
    print_status "Настройка конфигурации..."
    
    # Создание .env файла на droplet
    cat > /tmp/.env.production << 'EOF'
# Telegram Settings
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
TELEGRAM_WEBHOOK_URL=https://${DOMAIN}/webhook

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
    
    copy_to_droplet /tmp/.env.production ${APP_PATH}/.env
    rm /tmp/.env.production
    
    # Копирование MCP конфигурации
    if [ -f "data/mcp-servers.json" ]; then
        copy_to_droplet data/mcp-servers.json ${APP_PATH}/data/
    fi
    
    print_success "Конфигурация скопирована"
    print_warning "Не забудьте обновить .env файл с реальными токенами!"
}

# Настройка systemd сервиса
setup_systemd() {
    print_status "Настройка systemd сервиса..."
    
    remote_exec << EOF
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << 'SERVICE'
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
SERVICE

    # Перезагрузка systemd и запуск сервиса
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    sudo systemctl restart ${SERVICE_NAME}
EOF
    
    print_success "Systemd сервис настроен"
}

# Настройка Nginx
setup_nginx() {
    print_status "Настройка Nginx..."
    
    remote_exec << EOF
    # Создание конфигурации Nginx
    sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null << 'NGINX'
server {
    listen 80;
    server_name ${DOMAIN} ${DROPLET_IP};

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
NGINX

    # Активация конфигурации
    sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
EOF
    
    print_success "Nginx настроен"
}

# Настройка SSL с Let's Encrypt
setup_ssl() {
    print_status "Настройка SSL сертификата..."
    
    if [ "$DOMAIN" != "artem.example.com" ]; then
        remote_exec "sudo certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m admin@${DOMAIN}"
        print_success "SSL сертификат получен"
    else
        print_warning "Пропускаем SSL настройку - используется тестовый домен"
        print_warning "Обновите DOMAIN переменную и запустите: certbot --nginx -d YOUR_DOMAIN"
    fi
}

# Настройка Telegram webhook
setup_webhook() {
    print_status "Настройка Telegram webhook..."
    
    remote_exec << 'EOF'
    cd ${APP_PATH}
    source venv/bin/activate
    
    # Создание скрипта для установки webhook
    cat > set_webhook.py << 'SCRIPT'
#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL')
SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET')

if not all([TOKEN, WEBHOOK_URL]):
    print("❌ Отсутствуют необходимые переменные окружения")
    exit(1)

# Установка webhook
url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
data = {
    "url": WEBHOOK_URL,
    "secret_token": SECRET,
    "allowed_updates": ["message", "callback_query", "business_message", "business_connection"]
}

response = requests.post(url, json=data)
result = response.json()

if result.get("ok"):
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")
else:
    print(f"❌ Ошибка установки webhook: {result}")
SCRIPT

    python set_webhook.py
EOF
    
    print_success "Webhook настроен"
}

# Создание скрипта мониторинга
create_monitoring_script() {
    print_status "Создание скрипта мониторинга..."
    
    cat > monitor_bot.sh << 'EOF'
#!/bin/bash

# Мониторинг статуса бота

DROPLET_IP="104.248.39.106"
SERVICE_NAME="artem-integrator"
DROPLET_USER="coder"
APP_PATH="/home/coder/artem-integrator"

echo "📊 Статус бота Artem Integrator"
echo "================================"

# Проверка статуса сервиса
echo -e "\n🔧 Статус systemd сервиса:"
ssh ${DROPLET_USER}@${DROPLET_IP} "sudo systemctl status ${SERVICE_NAME} --no-pager"

# Проверка логов
echo -e "\n📝 Последние логи:"
ssh ${DROPLET_USER}@${DROPLET_IP} "tail -n 20 ${APP_PATH}/logs/bot.log"

# Проверка webhook
echo -e "\n🌐 Проверка webhook:"
ssh ${DROPLET_USER}@${DROPLET_IP} "cd ${APP_PATH} && source venv/bin/activate && python -c \"
import os, requests
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
r = requests.get(f'https://api.telegram.org/bot{TOKEN}/getWebhookInfo')
info = r.json()['result']
print(f'URL: {info.get(\"url\", \"Not set\")}')
print(f'Pending updates: {info.get(\"pending_update_count\", 0)}')
print(f'Last error: {info.get(\"last_error_message\", \"None\")}')
\""

# Проверка MCP статуса
echo -e "\n🔌 MCP статус:"
ssh ${DROPLET_USER}@${DROPLET_IP} "cd ${APP_PATH} && source venv/bin/activate && python -c \"
from bot.core.config import config
print(f'MCP enabled: {config.mcp.enabled}')
print(f'Supabase: {config.mcp.supabase_enabled}')
print(f'DigitalOcean: {config.mcp.digitalocean_enabled}')
print(f'Context7: {config.mcp.context7_enabled}')
\""
EOF
    
    chmod +x monitor_bot.sh
    print_success "Скрипт мониторинга создан: ./monitor_bot.sh"
}

# Главная функция деплоя
main() {
    echo "🚀 Начинаем развертывание Artem Integrator на DigitalOcean"
    echo "==========================================================="
    echo "Droplet IP: ${DROPLET_IP}"
    echo ""
    
    # Проверка SSH доступа
    if ! check_ssh_key; then
        exit 1
    fi
    
    # Основные шаги деплоя
    install_dependencies
    setup_application
    setup_configs
    setup_systemd
    setup_nginx
    setup_ssl
    setup_webhook
    create_monitoring_script
    
    echo ""
    echo "✅ Развертывание завершено!"
    echo ""
    echo "📋 Дальнейшие шаги:"
    echo "1. Обновите .env файл на сервере с реальными токенами:"
    echo "   ssh ${DROPLET_USER}@${DROPLET_IP} 'nano ${APP_PATH}/.env'"
    echo ""
    echo "2. Перезапустите сервис после обновления конфигурации:"
    echo "   ssh ${DROPLET_USER}@${DROPLET_IP} 'sudo systemctl restart ${SERVICE_NAME}'"
    echo ""
    echo "3. Проверьте статус бота:"
    echo "   ./monitor_bot.sh"
    echo ""
    echo "4. Настройте домен и SSL (если используете свой домен):"
    echo "   - Обновите DNS записи для ${DOMAIN}"
    echo "   - Запустите: ssh ${DROPLET_USER}@${DROPLET_IP} 'certbot --nginx -d ${DOMAIN}'"
    echo ""
    echo "📊 Полезные команды:"
    echo "   Логи: ssh ${DROPLET_USER}@${DROPLET_IP} 'tail -f ${APP_PATH}/logs/bot.log'"
    echo "   Статус: ssh ${DROPLET_USER}@${DROPLET_IP} 'sudo systemctl status ${SERVICE_NAME}'"
    echo "   Рестарт: ssh ${DROPLET_USER}@${DROPLET_IP} 'sudo systemctl restart ${SERVICE_NAME}'"
}

# Запуск скрипта
main "$@"