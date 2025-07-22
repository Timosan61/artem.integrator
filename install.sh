#!/bin/bash

# ================================================
# 🚀 Artem Integrator - Полная установка
# ================================================
# Этот скрипт выполняет полную установку и настройку
# бота для полноценного запуска с MCP функциями
# ================================================

set -e

echo "================================================"
echo "🚀 Установка Artem Integrator с MCP"
echo "================================================"
echo ""

# Проверка Python
echo "🐍 Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен!"
    echo "Установите Python 3.8+ и попробуйте снова"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION найден"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
echo ""
echo "📦 Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo ""
echo "📦 Установка зависимостей..."
pip install -r requirements.txt

# Установка claude-code-sdk
echo ""
echo "🔌 Установка Claude Code SDK для MCP..."
pip install claude-code-sdk==0.0.13 --no-deps || {
    echo "⚠️  Установка с предупреждениями о зависимостях - это нормально"
}

# Проверка .env файла
echo ""
if [ ! -f .env ]; then
    echo "📝 Создание файла .env..."
    
    # Запрашиваем токены у пользователя
    echo ""
    echo "Для работы бота необходимы следующие данные:"
    echo ""
    
    read -p "1. Telegram Bot Token (получить у @BotFather): " TELEGRAM_BOT_TOKEN
    read -p "2. Anthropic API Key (получить на console.anthropic.com): " ANTHROPIC_API_KEY
    read -p "3. Ngrok API Key (опционально, для HTTPS туннеля): " NGROK_API_KEY
    
    # Генерируем случайный secret token
    WEBHOOK_SECRET_TOKEN=$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')
    
    # Создаем .env файл
    cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
WEBHOOK_SECRET_TOKEN=$WEBHOOK_SECRET_TOKEN

# Anthropic API Configuration
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# Ngrok Configuration (optional)
NGROK_API_KEY=$NGROK_API_KEY

# Debug Mode
DEBUG=True

# Voice Service
VOICE_ENABLED=true
EOF
    
    echo "✅ Файл .env создан"
else
    echo "✅ Файл .env уже существует"
    
    # Проверяем наличие необходимых токенов
    source .env
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "❌ В файле .env отсутствуют необходимые токены!"
        echo "Пожалуйста, заполните TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY"
        exit 1
    fi
fi

# Создание необходимых директорий
echo ""
echo "📁 Создание директорий..."
mkdir -p data
mkdir -p logs

# Создание файла auto_admins.json
if [ ! -f data/auto_admins.json ]; then
    echo '{"admins": []}' > data/auto_admins.json
    echo "✅ Создан файл auto_admins.json"
fi

# Настройка ngrok если есть ключ
if [ ! -z "$NGROK_API_KEY" ]; then
    echo ""
    echo "🌐 Настройка ngrok..."
    
    # Установка ngrok если не установлен
    if ! command -v ngrok &> /dev/null; then
        echo "📥 Установка ngrok..."
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt update && sudo apt install ngrok
    fi
    
    # Настройка API ключа
    ngrok config add-authtoken $NGROK_API_KEY
    echo "✅ Ngrok настроен"
fi

# Создание скрипта автозапуска
echo ""
echo "📝 Создание скрипта автозапуска..."
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Запуск Artem Integrator..."
python -m uvicorn bot.webhook.app:create_app --factory --host 0.0.0.0 --port 8000
EOF
chmod +x start.sh

# Опционально: создание systemd сервиса
echo ""
read -p "Создать systemd сервис для автозапуска? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔧 Создание systemd сервиса..."
    
    SERVICE_FILE="/etc/systemd/system/artem-integrator.service"
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Artem Integrator Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python -m uvicorn bot.webhook.app:create_app --factory --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
Environment="PATH=$CURRENT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable artem-integrator
    echo "✅ Systemd сервис создан"
    echo ""
    echo "Команды управления сервисом:"
    echo "  sudo systemctl start artem-integrator    # Запустить"
    echo "  sudo systemctl stop artem-integrator     # Остановить"
    echo "  sudo systemctl status artem-integrator   # Статус"
    echo "  sudo journalctl -u artem-integrator -f   # Логи"
fi

# Финальная информация
echo ""
echo "================================================"
echo "✅ УСТАНОВКА ЗАВЕРШЕНА!"
echo "================================================"
echo ""
echo "📋 Дальнейшие шаги:"
echo ""
echo "1. Запустите бота одним из способов:"
echo "   - ./start.sh                              # Обычный запуск"
echo "   - ./auto_start.sh                         # Автоматический запуск с ngrok"
echo "   - sudo systemctl start artem-integrator   # Через systemd (если установлен)"
echo ""
echo "2. Откройте веб-интерфейс настройки:"
echo "   http://localhost:8000/setup"
echo ""
echo "3. В Telegram:"
echo "   - Найдите вашего бота"
echo "   - Отправьте /start"
echo "   - Вы автоматически станете администратором!"
echo ""
echo "📌 Полезные команды:"
echo "   /help        - Список всех команд"
echo "   /mcp_enable  - Активировать MCP функции"
echo "   /mcp         - Использовать MCP"
echo "   /db          - Работа с базами данных"
echo "   /docs        - Поиск документации"
echo ""
echo "🔍 Мониторинг:"
echo "   http://localhost:8000/        - Статус бота"
echo "   http://localhost:8000/debug   - Отладочная информация"
echo ""
echo "================================================"
echo "🎉 Удачной работы с Artem Integrator!"
echo "================================================"