#!/bin/bash

# Скрипт для запуска Artem Integrator с Docker и Cloudflare Tunnel

set -e

echo "🚀 Запуск Artem Integrator с Docker и Cloudflare Tunnel..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Проверка наличия docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Проверка .env файла
if [ ! -f .env ]; then
    echo "⚠️ Файл .env не найден!"
    echo "📝 Копирую .env.docker в .env..."
    cp .env.docker .env
    echo "✅ Файл .env создан. Отредактируйте его и добавьте необходимые токены:"
    echo "- TELEGRAM_BOT_TOKEN"
    echo "- ANTHROPIC_API_KEY" 
    echo "- CLOUDFLARE_TUNNEL_TOKEN (получите через ./scripts/setup_cloudflare.sh)"
    exit 1
fi

# Загрузка переменных окружения
source .env

# Проверка необходимых токенов
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Отсутствуют необходимые токены в .env файле!"
    echo "Убедитесь что установлены:"
    echo "- TELEGRAM_BOT_TOKEN"
    echo "- ANTHROPIC_API_KEY"
    exit 1
fi

# Проверка Cloudflare токена
if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo "⚠️ CLOUDFLARE_TUNNEL_TOKEN не установлен!"
    echo "Запустите ./scripts/setup_cloudflare.sh для настройки Cloudflare Tunnel"
    echo ""
    read -p "Продолжить без Cloudflare Tunnel? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Создание директорий для MCP серверов
echo "📁 Создание директорий..."
mkdir -p docker/mcp/servers/{supabase,digitalocean,context7,cloudflare}
mkdir -p data/mcp
mkdir -p logs

# Построение базового образа для MCP
echo "🏗️ Построение базового образа MCP..."
docker build -f docker/mcp/Dockerfile.base -t artem-mcp-base:latest .

# Запуск Docker Compose
echo "🚀 Запуск контейнеров..."
docker-compose up -d

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка статуса контейнеров
echo "📊 Статус контейнеров:"
docker-compose ps

# Проверка логов бота
echo ""
echo "📋 Последние логи бота:"
docker-compose logs --tail=20 bot

# Проверка здоровья
echo ""
echo "🏥 Проверка здоровья сервисов..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Бот работает!"
else
    echo "❌ Бот не отвечает"
fi

# Информация для пользователя
echo ""
echo "========================================="
echo "✅ ARTEM INTEGRATOR ЗАПУЩЕН В DOCKER!"
echo "========================================="
echo ""
echo "📱 Откройте Telegram и найдите вашего бота"
echo "🤖 Отправьте команду /start"
echo ""
echo "🌐 Веб-интерфейсы:"
echo "  - http://localhost:8000/ - Статус бота"
echo "  - http://localhost:8000/setup - Настройка"
echo "  - http://localhost:8000/debug - Отладка"
echo ""
echo "📊 Управление Docker:"
echo "  docker-compose logs -f         # Просмотр логов"
echo "  docker-compose ps              # Статус контейнеров"
echo "  docker-compose restart bot     # Перезапуск бота"
echo "  docker-compose down            # Остановка всех контейнеров"
echo ""
echo "🔧 MCP серверы:"
echo "  docker-compose logs mcp-supabase      # Логи Supabase MCP"
echo "  docker-compose logs mcp-digitalocean  # Логи DigitalOcean MCP"
echo "  docker-compose logs mcp-context7      # Логи Context7 MCP"
echo "  docker-compose logs mcp-cloudflare    # Логи Cloudflare MCP"
echo ""
echo "========================================="