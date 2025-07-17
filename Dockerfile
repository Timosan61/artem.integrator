FROM python:3.12-slim

# FORCE REBUILD - MCP VERSION: 2025-07-17-mcp-v1
# Cache bust timestamp: 2025-07-17T20:26:00Z
ARG CACHE_BUST=2025-07-17-mcp-v1

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект включая voice модуль
COPY . .

# Проверяем наличие важных директорий
RUN ls -la /app/voice || echo "Voice module not found"

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Устанавливаем переменную окружения для Python
ENV PYTHONPATH=/app

# Запускаем webhook сервер
CMD ["python", "webhook.py"]