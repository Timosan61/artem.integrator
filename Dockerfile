FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости (Final test version: 2025-06-18-v6)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Устанавливаем переменную окружения для Python
ENV PYTHONPATH=/app

# Запускаем бота
CMD ["python", "bot/main.py"]