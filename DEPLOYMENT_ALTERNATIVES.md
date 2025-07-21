# 🚀 Альтернативные способы деплоя Artem Integrator

Поскольку нет прямого SSH доступа к droplet 129.212.141.72, вот альтернативные способы развертывания:

## 1. 🌊 DigitalOcean App Platform (Рекомендуется)

### Преимущества:
- ✅ Автоматический деплой из GitHub
- ✅ Встроенный SSL
- ✅ Автоматическое масштабирование
- ✅ Простое управление через веб-интерфейс
- ✅ Управление через MCP команды

### Шаги:
1. Перейдите на https://cloud.digitalocean.com/apps
2. Нажмите "Create App"
3. Выберите GitHub репозиторий `Timosan61/artem.integrator`
4. Используйте созданный `digitalocean-app-spec.yaml`
5. Настройте переменные окружения
6. Запустите деплой

### Управление через MCP:
```bash
# В Telegram боте (если MCP настроен):
/mcp apps              # Список приложений
/deploy <app-id>       # Запустить деплой
/logs <app-id>         # Просмотр логов
```

## 2. 🚂 Railway (Альтернатива)

### Преимущества:
- ✅ Еще проще чем DO App Platform
- ✅ Автоматический деплой
- ✅ Бесплатный план для тестирования

### Шаги:
1. Перейдите на https://railway.app/
2. Подключите GitHub
3. Выберите репозиторий
4. Railway автоматически определит тип проекта
5. Добавьте переменные окружения
6. Деплой запустится автоматически

## 3. 🐳 Docker на существующем droplet

Если у вас есть доступ к droplet через DigitalOcean консоль:

### Через DigitalOcean Console:
1. Войдите в https://cloud.digitalocean.com/
2. Найдите droplet 129.212.141.72
3. Нажмите "Access" -> "Launch Droplet Console"
4. В консоли выполните:

```bash
# Клонирование репозитория
git clone https://github.com/Timosan61/artem.integrator.git
cd artem.integrator

# Создание Docker контейнера
docker build -t artem-integrator .
docker run -d \
  --name artem-bot \
  -p 8000:8000 \
  --env-file .env \
  --restart always \
  artem-integrator
```

## 4. 📦 Установка через User Data (при создании нового droplet)

При создании нового droplet в DigitalOcean, используйте User Data:

```bash
#!/bin/bash
# User Data скрипт для автоматической установки

# Обновление системы
apt-get update
apt-get upgrade -y

# Установка зависимостей
apt-get install -y python3.10 python3-pip git nginx certbot python3-certbot-nginx

# Клонирование репозитория
cd /opt
git clone https://github.com/Timosan61/artem.integrator.git
cd artem-integrator

# Установка Python зависимостей
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Создание systemd сервиса
cat > /etc/systemd/system/artem-bot.service << EOF
[Unit]
Description=Artem Integrator Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/artem-integrator
Environment="PATH=/opt/artem-integrator/venv/bin"
ExecStart=/opt/artem-integrator/venv/bin/python -m uvicorn bot.webhook:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Запуск сервиса
systemctl enable artem-bot
systemctl start artem-bot

# Настройка Nginx
# ... (конфигурация nginx)
```

## 5. 🔧 Получение доступа к существующему droplet

Если вам нужен доступ к droplet 129.212.141.72:

### Вариант 1: Через DigitalOcean панель
1. Войдите в DigitalOcean
2. Найдите droplet
3. Settings -> Access -> Add SSH Key
4. Добавьте ваш публичный ключ: `~/.ssh/id_ed25519.pub`

### Вариант 2: Через Recovery Console
1. В DigitalOcean панели выберите droplet
2. Access -> Reset Root Password
3. Используйте Recovery Console для входа
4. Добавьте SSH ключ вручную

### Вариант 3: Через владельца
Попросите владельца droplet добавить ваш SSH ключ:
```bash
ssh-rsa AAAAB3NzaC1... ваш публичный ключ
```

## 📋 Рекомендации

1. **Для быстрого старта**: Используйте DigitalOcean App Platform
2. **Для полного контроля**: Получите SSH доступ к droplet
3. **Для тестирования**: Используйте Railway или локальный ngrok

## 🆘 Помощь

Если нужна помощь с деплоем:
1. Проверьте документацию в `/doc/deployment/`
2. Используйте MCP команды для управления
3. Обратитесь к владельцу droplet для получения доступа