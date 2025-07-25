FROM python:3.12-slim

# Обновляем систему и устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Claude Code SDK (версия синхронизирована с requirements.txt)
RUN pip install claude-code-sdk==0.0.14

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/data

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Проверяем наличие модулей
RUN python -c "import bot; print('✅ Bot module loaded')"
RUN python -c "from bot.webhook.app import create_app; print('✅ Webhook app loaded')"

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["python", "-m", "uvicorn", "bot.webhook.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]