# 🚀 Deployment Guide

## Обзор

Это руководство описывает процесс развертывания Artyom Integrator на различных платформах. Рекомендуемая платформа - Railway.app, но бот также может быть развернут на Heroku, DigitalOcean, AWS или любом VPS.

## Требования

- Python 3.11+
- PostgreSQL (для Zep Memory)
- Redis (опционально, для кеширования)
- SSL сертификат (автоматически на Railway/Heroku)

## Railway (Рекомендуется)

### 1. Подготовка

1. Создайте аккаунт на [Railway.app](https://railway.app)
2. Установите Railway CLI (опционально):
```bash
npm install -g @railway/cli
```

### 2. Создание проекта

#### Через GitHub:
1. Fork репозиторий на GitHub
2. В Railway Dashboard нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш fork репозитория
5. Railway автоматически обнаружит Dockerfile

#### Через CLI:
```bash
railway login
railway init
railway link [project-id]
railway up
```

### 3. Настройка переменных окружения

В Railway Dashboard → Variables добавьте:

```env
# Обязательные
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_ID=your_telegram_id
OPENAI_API_KEY=your_openai_key
ZEP_API_KEY=your_zep_key

# Telegram Business
WEBHOOK_SECRET_TOKEN=generate-strong-token
BOT_USERNAME=@your_bot_username

# Опциональные
ANTHROPIC_API_KEY=your_anthropic_key
VOICE_ENABLED=true
MCP_ENABLED=true

# MCP серверы
SUPABASE_ENABLED=true
DIGITALOCEAN_ENABLED=true
DIGITALOCEAN_TOKEN=your_do_token
CONTEXT7_ENABLED=true
```

### 4. Настройка домена

Railway автоматически предоставляет домен:
```
https://your-app-name.up.railway.app
```

Или настройте собственный домен в Settings → Domains.

### 5. Деплой

Railway автоматически деплоит при push в main ветку:
```bash
git add .
git commit -m "Deploy to Railway"
git push origin main
```

### 6. Проверка

1. Откройте `https://your-app.up.railway.app/`
2. Проверьте webhook: `https://your-app.up.railway.app/webhook/info`
3. Просмотрите логи в Railway Dashboard

## Docker

### 1. Сборка образа

```bash
docker build -t artyom-integrator .
```

### 2. Запуск контейнера

```bash
docker run -d \
  --name artyom-bot \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  artyom-integrator
```

### 3. Docker Compose

```yaml
version: '3.8'

services:
  bot:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: zep
      POSTGRES_USER: zep
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Heroku

### 1. Подготовка

```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini
```

### 2. Настройка

```bash
# Установка buildpack
heroku buildpacks:set heroku/python

# Переменные окружения
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set ADMIN_USER_ID=your_id
# ... остальные переменные
```

### 3. Деплой

```bash
git push heroku main
```

## VPS (Ubuntu/Debian)

### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx postgresql redis-server -y

# Создание пользователя
sudo useradd -m -s /bin/bash botuser
sudo su - botuser
```

### 2. Клонирование и настройка

```bash
git clone https://github.com/Timosan61/artem.integrator.git
cd artem.integrator

# Виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Зависимости
pip install -r requirements.txt

# Копирование .env
cp .env.example .env
nano .env  # Редактирование переменных
```

### 3. Systemd сервис

Создайте `/etc/systemd/system/artyom-bot.service`:

```ini
[Unit]
Description=Artyom Integrator Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/artem.integrator
Environment="PATH=/home/botuser/artem.integrator/venv/bin"
ExecStart=/home/botuser/artem.integrator/venv/bin/uvicorn webhook:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable artyom-bot
sudo systemctl start artyom-bot
```

### 4. Nginx конфигурация

Создайте `/etc/nginx/sites-available/artyom-bot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/artyom-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL сертификат

```bash
sudo certbot --nginx -d your-domain.com
```

## Kubernetes

### 1. Deployment манифест

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: artyom-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: artyom-bot
  template:
    metadata:
      labels:
        app: artyom-bot
    spec:
      containers:
      - name: bot
        image: your-registry/artyom-integrator:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: bot-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: artyom-bot-service
spec:
  selector:
    app: artyom-bot
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### 2. Secrets

```bash
kubectl create secret generic bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN=your_token \
  --from-literal=OPENAI_API_KEY=your_key \
  --from-literal=ADMIN_USER_ID=your_id
```

### 3. Деплой

```bash
kubectl apply -f k8s/
```

## Мониторинг

### 1. Логи

```bash
# Railway
railway logs

# Docker
docker logs -f artyom-bot

# Systemd
journalctl -u artyom-bot -f

# Kubernetes
kubectl logs -f deployment/artyom-bot
```

### 2. Метрики

Бот экспортирует метрики в формате Prometheus:
```
http://your-app/metrics
```

### 3. Health Checks

```bash
# Проверка статуса
curl https://your-app.up.railway.app/

# Webhook info
curl https://your-app.up.railway.app/webhook/info
```

## Локальная разработка с Cloudflare Tunnel

### Быстрый старт

Для локальной разработки с публичным webhook используйте Cloudflare Tunnel:

1. **Установка cloudflared:**
```bash
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
```

2. **Запуск туннеля:**
```bash
./cloudflared tunnel --url http://localhost:8000
```

3. **Установка webhook:**
```bash
# Используйте URL из вывода cloudflared
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-tunnel.trycloudflare.com/webhook",
    "secret_token": "your-secret-token"
  }'
```

Подробнее см. [Cloudflare Webhook Setup Guide](../CLOUDFLARE_WEBHOOK_SETUP.md)

## Troubleshooting

### Webhook не работает

1. Проверьте URL webhook:
```bash
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

2. Переустановите webhook:
```bash
curl https://your-app.up.railway.app/webhook/set
```

3. Для локальной разработки используйте Cloudflare Tunnel (см. выше)

### Ошибки памяти

1. Увеличьте лимиты памяти
2. Включите swap на VPS
3. Оптимизируйте размер кеша

### SSL ошибки

1. Проверьте сертификат:
```bash
openssl s_client -connect your-domain.com:443
```

2. Обновите сертификат:
```bash
sudo certbot renew
```

## Backup и восстановление

### 1. Backup базы данных

```bash
# PostgreSQL
pg_dump -U postgres zep > backup.sql

# Redis
redis-cli BGSAVE
```

### 2. Восстановление

```bash
# PostgreSQL
psql -U postgres zep < backup.sql

# Redis
cp dump.rdb /var/lib/redis/
```

## Обновление

### 1. Zero-downtime обновление

```bash
# Railway - автоматически
git push origin main

# Docker
docker build -t artyom-integrator:new .
docker stop artyom-bot
docker run -d --name artyom-bot-new ... artyom-integrator:new
# Проверка
docker rm artyom-bot
docker rename artyom-bot-new artyom-bot
```

### 2. Миграции

При обновлении проверяйте:
- Новые переменные окружения
- Изменения в структуре БД
- Обновления зависимостей

## Безопасность

### 1. Основные правила

- Используйте сильные пароли
- Регулярно обновляйте зависимости
- Ограничьте доступ по IP
- Используйте файрвол

### 2. Секреты

- Никогда не коммитьте секреты
- Используйте переменные окружения
- Ротируйте токены регулярно

### 3. Мониторинг безопасности

- Проверяйте логи на подозрительную активность
- Настройте алерты на ошибки авторизации
- Используйте fail2ban на VPS