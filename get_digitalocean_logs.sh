#!/bin/bash
# 🌊 Автоматический скрипт для получения логов DigitalOcean App Platform
# Использование: ./get_digitalocean_logs.sh

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌊 Получение логов DigitalOcean Artyom Integrator...${NC}"
echo "=================================================="

# Проверяем установку doctl CLI
DOCTL_PATH="./doctl"
if [ -f "$DOCTL_PATH" ]; then
    echo -e "${GREEN}✅ Используем локальный doctl: $DOCTL_PATH${NC}"
    DOCTL="$DOCTL_PATH"
elif command -v doctl &> /dev/null; then
    echo -e "${GREEN}✅ Используем системный doctl${NC}"
    DOCTL="doctl"
else
    echo -e "${RED}❌ DigitalOcean CLI (doctl) не установлен${NC}"
    echo -e "${YELLOW}Установите: https://docs.digitalocean.com/reference/doctl/how-to/install/${NC}"
    echo -e "${YELLOW}Или через snap: sudo snap install doctl${NC}"
    exit 1
fi

# Проверяем аутентификацию
echo -e "${BLUE}🔐 Проверка аутентификации DigitalOcean...${NC}"
if ! $DOCTL account get > /dev/null 2>&1; then
    echo -e "${RED}❌ Ошибка аутентификации DigitalOcean${NC}"
    echo -e "${YELLOW}Выполните: $DOCTL auth init${NC}"
    exit 1
fi

USER_EMAIL=$($DOCTL account get --format Email --no-header 2>/dev/null || echo "неизвестен")
echo -e "${GREEN}✅ Аутентифицирован как: $USER_EMAIL${NC}"

# Получаем список приложений
echo -e "${BLUE}📱 Поиск приложения Artyom Integrator...${NC}"
APP_INFO=$($DOCTL apps list --format ID,Name,Status --no-header 2>/dev/null | grep -i "artem\|integrator" | head -1)

if [ -z "$APP_INFO" ]; then
    echo -e "${YELLOW}⚠️ Приложение не найдено по имени, показываем все приложения:${NC}"
    $DOCTL apps list --format ID,Name,Status 2>/dev/null || {
        echo -e "${RED}❌ Не удалось получить список приложений${NC}"
        exit 1
    }
    echo ""
    echo -e "${YELLOW}Укажите ID приложения вручную или создайте приложение 'artyom-integrator'${NC}"
    exit 1
fi

APP_ID=$(echo "$APP_INFO" | awk '{print $1}')
APP_NAME=$(echo "$APP_INFO" | awk '{print $2}')
APP_STATUS=$(echo "$APP_INFO" | awk '{print $3}')

echo -e "${GREEN}✅ Найдено приложение: $APP_NAME (ID: $APP_ID)${NC}"

# Получаем детальную информацию о приложении
echo -e "${BLUE}📊 Анализ статуса приложения...${NC}"
echo "=================================================="

# Статус приложения
echo -e "${BLUE}🚀 Статус приложения:${NC}"
echo -e "   📦 ID: ${APP_ID}"
echo -e "   📝 Имя: ${APP_NAME}"

case "$APP_STATUS" in
    "ACTIVE")
        echo -e "   ✅ Статус: ${GREEN}АКТИВНО${NC}"
        ;;
    "BUILDING")
        echo -e "   🔨 Статус: ${YELLOW}СБОРКА${NC}"
        ;;
    "DEPLOYING")
        echo -e "   🚀 Статус: ${YELLOW}ДЕПЛОЙ${NC}"
        ;;
    "ERROR")
        echo -e "   ❌ Статус: ${RED}ОШИБКА${NC}"
        ;;
    *)
        echo -e "   ❓ Статус: ${YELLOW}$APP_STATUS${NC}"
        ;;
esac

# Получаем URL приложения
echo -e "${BLUE}🌐 URL приложения:${NC}"
APP_URL=$($DOCTL apps get "$APP_ID" --format LiveURL --no-header 2>/dev/null || echo "не найден")
if [ "$APP_URL" != "не найден" ] && [ -n "$APP_URL" ]; then
    echo -e "   🔗 ${GREEN}$APP_URL${NC}"
else
    echo -e "   ⚠️ ${YELLOW}URL не настроен или приложение не развернуто${NC}"
fi

echo ""
echo "=================================================="

# Логи сборки (Build Logs)
echo -e "${YELLOW}🔨 Логи сборки (Build Logs):${NC}"
timeout 20s $DOCTL apps logs "$APP_ID" --type build --follow=false 2>/dev/null | tail -50 || {
    echo -e "${YELLOW}⏰ Не удалось получить логи сборки или логи пусты${NC}"
}

echo ""
echo "=================================================="

# Логи деплоя (Deploy Logs)  
echo -e "${YELLOW}🚀 Логи деплоя (Deploy Logs):${NC}"
timeout 20s $DOCTL apps logs "$APP_ID" --type deploy --follow=false 2>/dev/null | tail -30 || {
    echo -e "${YELLOW}⏰ Не удалось получить логи деплоя или логи пусты${NC}"
}

echo ""
echo "=================================================="

# Runtime логи (логи работающего приложения)
echo -e "${YELLOW}🔍 Runtime логи (работающее приложение):${NC}"
timeout 20s $DOCTL apps logs "$APP_ID" --type run --follow=false 2>/dev/null | tail -30 || {
    echo -e "${YELLOW}⏰ Таймаут или ошибка получения runtime логов${NC}"
}

echo ""
echo "=================================================="

# Показываем компоненты приложения
echo -e "${BLUE}📈 Компоненты приложения:${NC}"
$DOCTL apps get "$APP_ID" --format Name,Type,Size 2>/dev/null | grep -v "^$" || echo -e "${YELLOW}⚠️ Не удалось получить информацию о компонентах${NC}"

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Логи получены!${NC}"
echo ""
echo -e "${BLUE}🔍 Диагностика проблем:${NC}"
echo ""
echo -e "${RED}❌ Ошибки сборки (Build Errors):${NC}"
echo -e "   • ${YELLOW}npm/yarn install failed${NC}"
echo -e "   • ${YELLOW}Docker build failed${NC}"
echo -e "   • ${YELLOW}Missing dependencies${NC}"
echo -e "   • ${YELLOW}Port binding errors${NC}"
echo ""
echo -e "${RED}❌ Ошибки деплоя (Deploy Errors):${NC}"
echo -e "   • ${YELLOW}Health check failed${NC}"
echo -e "   • ${YELLOW}Port not accessible${NC}"
echo -e "   • ${YELLOW}Environment variables missing${NC}"
echo -e "   • ${YELLOW}Memory/CPU limits exceeded${NC}"
echo ""
echo -e "${RED}❌ Runtime ошибки:${NC}"
echo -e "   • ${YELLOW}Application crashes${NC}"
echo -e "   • ${YELLOW}HTTP 500/502/503 errors${NC}"
echo -e "   • ${YELLOW}Database connection errors${NC}"
echo -e "   • ${YELLOW}API timeout errors${NC}"
echo ""
echo -e "${GREEN}✅ Успешная работа:${NC}"
echo -e "   • ${YELLOW}✅ Application started${NC}"
echo -e "   • ${YELLOW}✅ Health check passed${NC}"
echo -e "   • ${YELLOW}✅ Webhook received${NC}"
echo -e "   • ${YELLOW}✅ Business message processed${NC}"
echo ""
echo -e "${BLUE}📱 Business API диагностика:${NC}"
echo -e "   • ${YELLOW}📱 Обработка Business сообщения${NC}"
echo -e "   • ${YELLOW}📤 Отправляю Business сообщение${NC}"
echo -e "   • ${YELLOW}✅ Business сообщение отправлено успешно${NC}"
echo -e "   • ${YELLOW}❌ Ошибка отправки Business сообщения${NC}"
echo ""
echo -e "${BLUE}📱 Debug endpoints:${NC}"
if [ "$APP_URL" != "не найден" ] && [ -n "$APP_URL" ]; then
    echo -e "   • ${GREEN}${APP_URL}/debug/last-updates${NC}"
    echo -e "   • ${GREEN}${APP_URL}/debug/voice-status${NC}"
    echo -e "   • ${GREEN}${APP_URL}/${NC}"
else
    echo -e "   • ${YELLOW}Debug endpoints недоступны (нет URL)${NC}"
fi
echo ""
echo -e "${BLUE}🛠️ Команды диагностики:${NC}"
echo -e "   • ${YELLOW}$DOCTL apps list${NC} - список приложений"
echo -e "   • ${YELLOW}$DOCTL apps get $APP_ID${NC} - детали приложения"
echo -e "   • ${YELLOW}$DOCTL apps logs $APP_ID --type run --follow${NC} - логи в реальном времени"
echo -e "   • ${YELLOW}$DOCTL apps logs $APP_ID --type build${NC} - логи сборки"
echo -e "   • ${YELLOW}$DOCTL apps logs $APP_ID --type deploy${NC} - логи деплоя"