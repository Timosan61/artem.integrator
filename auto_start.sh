#!/bin/bash

# Скрипт для полностью автоматического запуска бота
# Без необходимости открывать терминал или вводить Telegram ID

set -e

echo "🚀 Автоматический запуск Artem Integrator..."

# 0. Активация виртуального окружения если есть
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 1. Проверка зависимостей
echo "📦 Проверка зависимостей..."
if ! python -m pip show claude-code-sdk > /dev/null 2>&1; then
    echo "📥 Установка claude-code-sdk..."
    python -m pip install claude-code-sdk==0.0.13 --no-deps
fi

# 2. Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env с необходимыми настройками"
    exit 1
fi

# Проверка токенов
source .env
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Отсутствуют необходимые токены в .env файле!"
    echo "Убедитесь что установлены TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY"
    exit 1
fi

# 3. Создание auto_admins.json если не существует
if [ ! -f data/auto_admins.json ]; then
    echo "📝 Создание файла auto_admins.json..."
    mkdir -p data
    echo '{"admins": []}' > data/auto_admins.json
fi

# 4. Запуск бота в фоне
echo "🤖 Запуск бота..."
nohup python -m uvicorn bot.webhook.app:create_app --factory --host 0.0.0.0 --port 8000 > bot.log 2>&1 &

BOT_PID=$!
echo "✅ Бот запущен с PID: $BOT_PID"

# 5. Ожидание запуска
echo "⏳ Ожидание запуска сервера..."
sleep 5

# 6. Проверка статуса
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ Сервер запущен успешно!"
else
    echo "❌ Ошибка запуска сервера"
    exit 1
fi

# 7. Настройка webhook через Cloudflare Tunnel или ngrok
if [ ! -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo "🌐 Используется Cloudflare Tunnel"
    echo "✅ Webhook будет установлен автоматически при запуске бота"
    echo "ℹ️  Убедитесь, что Cloudflare Tunnel настроен и запущен"
    
elif [ ! -z "$NGROK_API_KEY" ]; then
    echo "🌐 Настройка ngrok..."
    # Сохраняем API ключ
    ngrok config add-authtoken $NGROK_API_KEY
    
    # Запускаем ngrok в фоне
    nohup ngrok http 8000 > ngrok.log 2>&1 &
    NGROK_PID=$!
    
    echo "⏳ Ожидание запуска ngrok..."
    sleep 5
    
    # Получаем URL
    WEBHOOK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4)
    
    if [ ! -z "$WEBHOOK_URL" ]; then
        echo "✅ Ngrok URL: $WEBHOOK_URL"
        
        # Устанавливаем webhook
        echo "📡 Установка webhook..."
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$WEBHOOK_URL/webhook\", \"secret_token\": \"$WEBHOOK_SECRET_TOKEN\"}" \
            | jq '.'
            
        echo "✅ Webhook установлен!"
    else
        echo "❌ Не удалось получить ngrok URL"
    fi
else
    echo "⚠️  Ни CLOUDFLARE_TUNNEL_TOKEN, ни NGROK_API_KEY не установлены в .env"
    echo "Настройте один из способов для публичного доступа к боту:"
    echo "1. Cloudflare Tunnel: запустите ./scripts/setup_cloudflare.sh"
    echo "2. Ngrok: добавьте NGROK_API_KEY в .env файл"
fi

# 8. Информация для пользователя
echo ""
echo "========================================="
echo "✅ БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ!"
echo "========================================="
echo ""
echo "📱 Откройте Telegram и найдите вашего бота"
echo "🤖 Отправьте команду /start"
echo ""
echo "Первый пользователь автоматически станет администратором!"
echo ""
echo "📋 Доступные команды:"
echo "  /start - Начать работу (первый пользователь станет админом)"
echo "  /help - Показать помощь"
echo "  /mcp_enable - Активировать MCP функции (для обычных пользователей)"
echo ""
echo "📊 Мониторинг:"
echo "  Логи бота: tail -f bot.log"
echo "  Логи ngrok: tail -f ngrok.log"
echo "  Статус: http://localhost:8000/"
echo ""
echo "🛑 Остановка:"
echo "  kill $BOT_PID  # Остановить бота"
if [ ! -z "$NGROK_PID" ]; then
    echo "  kill $NGROK_PID  # Остановить ngrok"
fi
echo ""
echo "========================================="