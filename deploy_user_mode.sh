#!/bin/bash

# Деплой Artem Integrator в пользовательском режиме (без sudo)

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
APP_PATH="/home/coder/artem-integrator"
GITHUB_REPO="https://github.com/Timosan61/artem.integrator.git"
CURRENT_IP=$(curl -s ifconfig.me)
PORT=8000

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

# Проверка зависимостей
check_dependencies() {
    print_status "Проверка зависимостей..."
    
    # Python
    if command -v python3 &> /dev/null; then
        print_success "Python установлен: $(python3 --version)"
    else
        print_error "Python не установлен!"
        exit 1
    fi
    
    # Git
    if command -v git &> /dev/null; then
        print_success "Git установлен: $(git --version)"
    else
        print_error "Git не установлен!"
        exit 1
    fi
    
    # Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js установлен: $(node --version)"
    else
        print_warning "Node.js не установлен (MCP функции могут не работать)"
    fi
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
        git fetch origin
        git checkout MCP
        git pull origin MCP
    else
        print_status "Клонирование репозитория..."
        git clone ${GITHUB_REPO} .
        git checkout MCP || git checkout -b MCP origin/MCP
    fi
    
    # Создание виртуального окружения
    if [ ! -d "venv" ]; then
        print_status "Создание виртуального окружения..."
        python3 -m venv venv
    fi
    
    # Активация и установка зависимостей
    print_status "Установка Python зависимостей..."
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
TELEGRAM_WEBHOOK_URL=http://${CURRENT_IP}:${PORT}/webhook

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
APP_PORT=${PORT}
ENVIRONMENT=production
EOF
        print_warning "ВАЖНО: Обновите .env файл с реальными токенами!"
    else
        print_success ".env файл уже существует"
    fi
}

# Создание скрипта запуска
create_start_script() {
    print_status "Создание скрипта запуска..."
    
    cat > ${APP_PATH}/start_bot.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
python -m uvicorn bot.webhook:app --host 0.0.0.0 --port 8000
EOF
    
    chmod +x ${APP_PATH}/start_bot.sh
    
    # Создание скрипта для запуска в фоне
    cat > ${APP_PATH}/start_bot_background.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
nohup python -m uvicorn bot.webhook:app --host 0.0.0.0 --port 8000 >> logs/bot.log 2>&1 &
echo $! > bot.pid
echo "Bot started with PID: $(cat bot.pid)"
EOF
    
    chmod +x ${APP_PATH}/start_bot_background.sh
    
    # Создание скрипта остановки
    cat > ${APP_PATH}/stop_bot.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Bot stopped (PID: $PID)"
    else
        echo "Bot not running (PID: $PID not found)"
    fi
    rm bot.pid
else
    echo "PID file not found. Bot may not be running."
fi
EOF
    
    chmod +x ${APP_PATH}/stop_bot.sh
    
    print_success "Скрипты запуска созданы"
}

# Создание скрипта мониторинга
create_monitor_script() {
    print_status "Создание скрипта мониторинга..."
    
    cat > ${APP_PATH}/monitor_bot.sh << 'EOF'
#!/bin/bash

cd $(dirname $0)

echo "📊 Статус бота Artem Integrator"
echo "================================"

# Проверка процесса
if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null; then
        echo "✅ Бот запущен (PID: $PID)"
    else
        echo "❌ Бот не запущен (PID файл устарел)"
    fi
else
    echo "❌ Бот не запущен (PID файл не найден)"
fi

# Последние логи
echo -e "\n📝 Последние логи:"
tail -n 20 logs/bot.log

# Проверка портов
echo -e "\n🌐 Проверка порта:"
if netstat -tuln 2>/dev/null | grep -q ":8000"; then
    echo "✅ Порт 8000 открыт"
else
    echo "❌ Порт 8000 не прослушивается"
fi
EOF
    
    chmod +x ${APP_PATH}/monitor_bot.sh
    
    print_success "Скрипт мониторинга создан"
}

# Главная функция
main() {
    echo "🚀 Деплой Artem Integrator (пользовательский режим)"
    echo "===================================================="
    echo "Сервер IP: ${CURRENT_IP}"
    echo "Порт: ${PORT}"
    echo ""
    
    # Основные шаги
    check_dependencies
    setup_application
    setup_config
    create_start_script
    create_monitor_script
    
    echo ""
    echo "✅ Деплой завершен!"
    echo ""
    echo "📋 Дальнейшие шаги:"
    echo ""
    echo "1. Обновите .env файл с реальными токенами:"
    echo "   nano ${APP_PATH}/.env"
    echo ""
    echo "2. Запустите бота:"
    echo "   В интерактивном режиме: ${APP_PATH}/start_bot.sh"
    echo "   В фоновом режиме: ${APP_PATH}/start_bot_background.sh"
    echo ""
    echo "3. Проверьте статус:"
    echo "   ${APP_PATH}/monitor_bot.sh"
    echo ""
    echo "4. Остановите бота (если запущен в фоне):"
    echo "   ${APP_PATH}/stop_bot.sh"
    echo ""
    echo "⚠️  ВАЖНО:"
    echo "- Бот будет доступен по адресу: http://${CURRENT_IP}:${PORT}"
    echo "- Webhook URL: http://${CURRENT_IP}:${PORT}/webhook"
    echo "- Для продакшена рекомендуется настроить Nginx и SSL"
    echo ""
    echo "📊 Полезные команды:"
    echo "   Логи: tail -f ${APP_PATH}/logs/bot.log"
    echo "   Статус процесса: ps aux | grep uvicorn"
    echo "   Порты: netstat -tuln | grep ${PORT}"
}

# Запуск скрипта
main "$@"