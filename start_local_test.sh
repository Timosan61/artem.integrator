#!/bin/bash
# Скрипт для запуска локального тестирования с Docker Compose

echo "🚀 Запуск локального тестирования Artem Bot + MCP"
echo "================================================"

# Проверка наличия .env.test
if [ ! -f .env.test ]; then
    echo "❌ Файл .env.test не найден!"
    echo "📝 Создайте его на основе .env.test.example:"
    echo "   cp .env.test.example .env.test"
    echo "   Затем заполните необходимые переменные"
    exit 1
fi

# Загрузка переменных окружения
export $(cat .env.test | grep -v '^#' | xargs)

# Остановка старых контейнеров
echo "🛑 Остановка старых контейнеров..."
docker-compose -f docker-compose.test.yml down

# Сборка образов
echo "🔨 Сборка Docker образов..."
docker-compose -f docker-compose.test.yml build

# Запуск сервисов
echo "🚀 Запуск сервисов..."
docker-compose -f docker-compose.test.yml up -d

# Ожидание запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка статуса
echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.test.yml ps

# Получение Ngrok URL
echo ""
echo "🌐 Получение Ngrok URL..."
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

if [ -z "$NGROK_URL" ]; then
    echo "❌ Не удалось получить Ngrok URL"
    echo "Проверьте логи: docker-compose -f docker-compose.test.yml logs ngrok"
else
    echo "✅ Ngrok URL: $NGROK_URL"
    echo ""
    echo "📝 Используйте этот URL для настройки webhook в Telegram:"
    echo "   $NGROK_URL/webhook"
    echo ""
    echo "🔧 Установка webhook:"
    echo "   curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=$NGROK_URL/webhook"
fi

echo ""
echo "📋 Полезные команды:"
echo "   Логи всех сервисов:    docker-compose -f docker-compose.test.yml logs -f"
echo "   Логи бота:             docker-compose -f docker-compose.test.yml logs -f artem-bot"
echo "   Логи MCP mock:         docker-compose -f docker-compose.test.yml logs -f mcp-mock"
echo "   Adminer (БД):          http://localhost:8080"
echo "   Ngrok Dashboard:       http://localhost:4040"
echo "   Остановить все:        docker-compose -f docker-compose.test.yml down"

echo ""
echo "🧪 Запуск тестов:"
echo "   python test_telegram_mcp.py"

echo ""
echo "✅ Локальное окружение запущено!"