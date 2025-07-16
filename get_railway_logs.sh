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

# Получаем логи с разными опциями
echo -e "${BLUE}📊 Получение логов сервиса web...${NC}"
echo "=================================================="

# Логи деплоя (последние 50 строк с таймаутом)
echo -e "${YELLOW}🔍 Последние логи развертывания:${NC}"
timeout 30s railway logs --service web 2>/dev/null || {
    echo -e "${YELLOW}⏰ Таймаут или ошибка получения логов${NC}"
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
echo -e "${BLUE}🔍 Для поиска ошибок Voice Service ищите:${NC}"
echo -e "   • ${YELLOW}VOICE_ENABLED: false${NC}"
echo -e "   • ${YELLOW}No module named 'voice'${NC}"
echo -e "   • ${YELLOW}voice/ директория отсутствует${NC}"
echo -e "   • ${YELLOW}ImportError${NC}"
echo ""
echo -e "${BLUE}🎤 Для голосовых сообщений ищите:${NC}"
echo -e "   • ${YELLOW}'voice' in attachments${NC}"
echo -e "   • ${YELLOW}Voice Service инициализирован${NC}"
echo -e "   • ${YELLOW}Voice processing started${NC}"
echo ""
echo -e "${BLUE}📱 Debug endpoints:${NC}"
echo -e "   • ${GREEN}https://web-production-84d8.up.railway.app/debug/voice-status${NC}"
echo -e "   • ${GREEN}https://web-production-84d8.up.railway.app/debug/last-updates${NC}"
echo -e "   • ${GREEN}https://web-production-84d8.up.railway.app/${NC}"