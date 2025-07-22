#!/bin/bash

# Скрипт для настройки Cloudflare Tunnel
# Заменяет ngrok на более надежное решение

set -e

echo "🌐 Настройка Cloudflare Tunnel для Artem Integrator..."

# Проверка наличия cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "📥 Установка cloudflared..."
    
    # Определяем ОС и архитектуру
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    if [ "$ARCH" = "x86_64" ]; then
        ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ]; then
        ARCH="arm64"
    fi
    
    # Скачиваем cloudflared
    DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-${OS}-${ARCH}"
    
    echo "📥 Скачивание cloudflared..."
    curl -L -o cloudflared "$DOWNLOAD_URL"
    chmod +x cloudflared
    
    # Перемещаем в PATH
    sudo mv cloudflared /usr/local/bin/
    
    echo "✅ cloudflared установлен"
fi

# Проверка версии
echo "📌 Версия cloudflared:"
cloudflared --version

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с необходимыми настройками"
    exit 1
fi

# Загружаем переменные окружения
source .env

# Проверка наличия токена Cloudflare
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo "⚠️  CLOUDFLARE_API_TOKEN не установлен в .env"
    echo ""
    echo "📝 Для получения токена:"
    echo "1. Перейдите на https://dash.cloudflare.com/profile/api-tokens"
    echo "2. Создайте новый токен с правами 'Cloudflare Tunnel:Edit'"
    echo "3. Добавьте токен в .env файл"
    echo ""
    read -p "Продолжить без автоматической настройки? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Создание туннеля
echo "🚇 Создание Cloudflare Tunnel..."

if [ ! -z "$CLOUDFLARE_API_TOKEN" ]; then
    # Авторизация
    cloudflared tunnel login
    
    # Создание туннеля
    TUNNEL_NAME="artem-integrator-$(date +%s)"
    cloudflared tunnel create "$TUNNEL_NAME"
    
    # Получаем ID туннеля
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    
    if [ -z "$TUNNEL_ID" ]; then
        echo "❌ Не удалось создать туннель"
        exit 1
    fi
    
    echo "✅ Туннель создан: $TUNNEL_NAME (ID: $TUNNEL_ID)"
    
    # Создаем конфигурацию
    cat > ~/.cloudflared/config.yml <<EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: artem-bot.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF
    
    echo "✅ Конфигурация создана"
    
    # Добавляем DNS запись (если есть домен)
    if [ ! -z "$CLOUDFLARE_ZONE_ID" ] && [ ! -z "$CLOUDFLARE_DOMAIN" ]; then
        echo "🌐 Добавление DNS записи..."
        cloudflared tunnel route dns "$TUNNEL_ID" "artem-bot.$CLOUDFLARE_DOMAIN"
    fi
    
    # Генерируем токен для Docker
    TUNNEL_TOKEN=$(cloudflared tunnel token "$TUNNEL_ID")
    
    echo ""
    echo "✅ Cloudflare Tunnel настроен!"
    echo ""
    echo "📝 Добавьте в .env файл:"
    echo "CLOUDFLARE_TUNNEL_TOKEN=$TUNNEL_TOKEN"
    echo ""
    
else
    echo "⚠️  Ручная настройка Cloudflare Tunnel"
    echo ""
    echo "1. Создайте туннель вручную:"
    echo "   cloudflared tunnel create artem-integrator"
    echo ""
    echo "2. Настройте маршрутизацию:"
    echo "   cloudflared tunnel route dns <TUNNEL_ID> artem-bot.yourdomain.com"
    echo ""
    echo "3. Получите токен:"
    echo "   cloudflared tunnel token <TUNNEL_ID>"
    echo ""
    echo "4. Добавьте токен в .env файл"
fi

# Создание systemd сервиса для cloudflared (опционально)
echo ""
read -p "Создать systemd сервис для автозапуска? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo cat > /etc/systemd/system/cloudflared-artem.service <<EOF
[Unit]
Description=Cloudflare Tunnel for Artem Integrator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=/usr/local/bin/cloudflared tunnel run
Restart=always
RestartSec=10
Environment="TUNNEL_TOKEN=$TUNNEL_TOKEN"

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable cloudflared-artem
    echo "✅ Systemd сервис создан: cloudflared-artem"
fi

echo ""
echo "========================================="
echo "✅ НАСТРОЙКА CLOUDFLARE TUNNEL ЗАВЕРШЕНА!"
echo "========================================="
echo ""
echo "🚀 Для запуска с Docker:"
echo "   docker-compose up -d"
echo ""
echo "🚀 Для запуска без Docker:"
echo "   cloudflared tunnel run"
echo ""
echo "📊 Проверка статуса:"
echo "   cloudflared tunnel info"
echo ""
echo "========================================="