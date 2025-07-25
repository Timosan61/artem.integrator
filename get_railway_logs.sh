#!/bin/bash
# 🚂 Автоматический скрипт для получения логов Railway
# Использование: ./get_railway_logs.sh

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚂 Получение логов Railway Artyom Integrator...${NC}"
echo "=================================================="

# Устанавливаем токен Railway API
export RAILWAY_API_TOKEN=335a5302-6eb6-430d-be0f-eee35aa16cee

# Проверяем установку Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI не установлен${NC}"
    echo -e "${YELLOW}Установите: npm install -g @railway/cli${NC}"
    exit 1
fi

# Проверяем аутентификацию
echo -e "${BLUE}🔐 Проверка аутентификации...${NC}"
if ! railway whoami > /dev/null 2>&1; then
    echo -e "${RED}❌ Ошибка аутентификации Railway${NC}"
    echo -e "${YELLOW}Проверьте токен: $RAILWAY_API_TOKEN${NC}"
    exit 1
fi

USER=$(railway whoami 2>/dev/null || echo "неизвестен")
echo -e "${GREEN}✅ Аутентифицирован как: $USER${NC}"

# Проверяем связь с проектом
echo -e "${BLUE}🔗 Проверка связи с проектом...${NC}"
if [ ! -f ".railway/railway.toml" ]; then
    echo -e "${YELLOW}⚠️ Проект не привязан, привязываем...${NC}"
    railway link --project artem.integrator > /dev/null 2>&1 || {
        echo -e "${RED}❌ Не удалось привязать проект${NC}"
        exit 1
    }
fi

echo -e "${GREEN}✅ Проект artem.integrator привязан${NC}"

# Получаем информацию о деплоях
echo -e "${BLUE}📊 Анализ деплоя сервиса web...${NC}"
echo "=================================================="

# Проверяем статус последнего деплоя
echo -e "${BLUE}🚀 Статус последнего деплоя:${NC}"
DEPLOYMENT_STATUS=$(timeout 15s railway deployments --service web --json 2>/dev/null | head -1 | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
DEPLOYMENT_ID=$(timeout 15s railway deployments --service web --json 2>/dev/null | head -1 | jq -r '.id // "unknown"' 2>/dev/null || echo "unknown")

echo -e "   📦 Деплой ID: ${DEPLOYMENT_ID}"
case "$DEPLOYMENT_STATUS" in
    "SUCCESS")
        echo -e "   ✅ Статус: ${GREEN}УСПЕШНО${NC}"
        ;;
    "FAILED")
        echo -e "   ❌ Статус: ${RED}ОШИБКА${NC}"
        ;;
    "BUILDING")
        echo -e "   🔨 Статус: ${YELLOW}СБОРКА${NC}"
        ;;
    "DEPLOYING")
        echo -e "   🚀 Статус: ${YELLOW}ДЕПЛОЙ${NC}"
        ;;
    *)
        echo -e "   ❓ Статус: ${YELLOW}$DEPLOYMENT_STATUS${NC}"
        ;;
esac

echo ""
echo "=================================================="

# Логи сборки последнего деплоя
echo -e "${YELLOW}🔨 Логи сборки (Build Logs):${NC}"
if [ "$DEPLOYMENT_ID" != "unknown" ]; then
    timeout 20s railway logs --deployment "$DEPLOYMENT_ID" 2>/dev/null || {
        echo -e "${YELLOW}⏰ Не удалось получить логи сборки${NC}"
    }
else
    echo -e "${YELLOW}⚠️ ID деплоя неизвестен, показываем общие логи сборки${NC}"
    timeout 20s railway logs --service web --since 10m 2>/dev/null | head -30 || {
        echo -e "${YELLOW}⏰ Не удалось получить логи${NC}"
    }
fi

echo ""
echo "=================================================="

# Runtime логи (логи работающего сервиса)
echo -e "${YELLOW}🔍 Runtime логи (работающий сервис):${NC}"
timeout 20s railway logs --service web --since 5m 2>/dev/null | tail -20 || {
    echo -e "${YELLOW}⏰ Таймаут или ошибка получения runtime логов${NC}"
}

echo ""
echo "=================================================="

# Показываем статус проекта
echo -e "${BLUE}📈 Статус проекта:${NC}"
railway status 2>/dev/null || echo -e "${YELLOW}⚠️ Не удалось получить статус${NC}"

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Логи получены!${NC}"
echo ""
echo -e "${BLUE}🔍 Диагностика проблем:${NC}"
echo ""
echo -e "${RED}❌ Ошибки сборки (Build Errors):${NC}"
echo -e "   • ${YELLOW}Dockerfile 'X' does not exist${NC}"
echo -e "   • ${YELLOW}COPY failed${NC}"
echo -e "   • ${YELLOW}RUN command failed${NC}"
echo -e "   • ${YELLOW}Package installation errors${NC}"
echo ""
echo -e "${RED}❌ Ошибки Voice Service:${NC}"
echo -e "   • ${YELLOW}VOICE_ENABLED: false${NC}"
echo -e "   • ${YELLOW}No module named 'voice'${NC}"
echo -e "   • ${YELLOW}voice/ директория отсутствует${NC}"
echo -e "   • ${YELLOW}ImportError${NC}"
echo ""
echo -e "${GREEN}✅ Успешная работа голосовых:${NC}"
echo -e "   • ${YELLOW}'voice' in attachments${NC}"
echo -e "   • ${YELLOW}Voice Service инициализирован${NC}"
echo -e "   • ${YELLOW}Voice processing started${NC}"
echo -e "   • ${YELLOW}Voice transcribed${NC}"
echo ""
echo -e "${BLUE}📱 Debug endpoints:${NC}"
echo -e "   • ${GREEN}https://web-production-84d8.up.railway.app/debug/voice-status${NC}"
echo -e "   • ${GREEN}https://web-production-84d8.up.railway.app/debug/last-updates${NC}"
echo -e "   • ${GREEN}https://web-production-84d8.up.railway.app/${NC}"
echo ""
echo -e "${BLUE}🛠️ Команды диагностики:${NC}"
echo -e "   • ${YELLOW}railway deployments --service web${NC} - список деплоев"
echo -e "   • ${YELLOW}railway logs --deployment <ID>${NC} - логи конкретного деплоя"
echo -e "   • ${YELLOW}railway logs --service web --since 30m${NC} - логи за 30 минут"