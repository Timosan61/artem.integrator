#!/bin/bash
# 🚀 Автоматический скрипт для деплоя и проверки логов
# Использование: ./deploy_and_check.sh "commit message"

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Автоматический деплой и проверка логов${NC}"
echo "======================================================"

# Проверяем, что передано сообщение коммита
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Ошибка: Необходимо передать сообщение коммита${NC}"
    echo -e "${YELLOW}Использование: ./deploy_and_check.sh \"commit message\"${NC}"
    exit 1
fi

COMMIT_MESSAGE="$1"

# Добавляем все изменения
echo -e "${BLUE}📦 Добавление изменений в git...${NC}"
git add .

# Создаем коммит
echo -e "${BLUE}💾 Создание коммита...${NC}"
git commit -m "$COMMIT_MESSAGE

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Отправляем на GitHub
echo -e "${BLUE}🔄 Отправка на GitHub...${NC}"
git push origin whisper_golos

echo -e "${GREEN}✅ Изменения отправлены на GitHub${NC}"
echo ""

# Ждем 2 минуты для завершения деплоя
echo -e "${YELLOW}⏰ Ожидание 2 минуты для завершения деплоя Railway...${NC}"
echo "======================================================"

# Обратный отсчет по 30-секундным интервалам
for i in {4..1}; do
    remaining=$((i * 30))
    echo -e "${YELLOW}⏱️ Осталось ${remaining} секунд...${NC}"
    sleep 30
done

echo -e "${GREEN}⏰ Время ожидания завершено!${NC}"
echo ""

# Автоматически запускаем проверку логов
echo -e "${BLUE}🔍 Автоматическая проверка логов деплоя...${NC}"
echo "======================================================"

./get_railway_logs.sh

echo ""
echo "======================================================"
echo -e "${GREEN}✅ Деплой и проверка логов завершены!${NC}"
echo ""
echo -e "${BLUE}📝 Что делать дальше:${NC}"
echo -e "   • Проверьте статус деплоя выше"
echo -e "   • Если деплой FAILED - исправьте ошибки и повторите"
echo -e "   • Если деплой SUCCESS - протестируйте функциональность"
echo -e "   • Для повторной проверки: ${YELLOW}./get_railway_logs.sh${NC}"