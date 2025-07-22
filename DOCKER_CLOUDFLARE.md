# 🐳 Docker и Cloudflare Tunnel для Artem Integrator

## 🎯 Преимущества решения

### Docker
- **Изоляция**: Каждый компонент в своем контейнере
- **Портативность**: Работает одинаково везде
- **Масштабируемость**: Легко добавлять новые MCP серверы
- **Простота**: Один командой запускается вся система

### Cloudflare Tunnel (вместо ngrok)
- **Надежность**: Автоматическое переподключение
- **Постоянный URL**: Не меняется при перезапуске
- **Безопасность**: Нет открытых портов
- **Бесплатно**: Для базового использования

## 🚀 Быстрый старт

### 1. Установка Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# macOS
# Установите Docker Desktop: https://www.docker.com/products/docker-desktop
```

### 2. Настройка Cloudflare Tunnel
```bash
# Запустите скрипт настройки
./scripts/setup_cloudflare.sh

# Следуйте инструкциям для получения CLOUDFLARE_TUNNEL_TOKEN
```

### 3. Конфигурация
```bash
# Скопируйте шаблон конфигурации
cp .env.docker .env

# Отредактируйте .env и добавьте:
# - TELEGRAM_BOT_TOKEN
# - ANTHROPIC_API_KEY
# - CLOUDFLARE_TUNNEL_TOKEN (из шага 2)
```

### 4. Запуск
```bash
# Запустить все контейнеры
./docker_start.sh
```

## 📦 Архитектура Docker

```
artem-integrator/
├── bot/                    # Основной бот (контейнер)
├── cloudflared/           # Cloudflare Tunnel (контейнер)
├── mcp-supabase/         # MCP сервер Supabase
├── mcp-digitalocean/     # MCP сервер DigitalOcean
├── mcp-context7/         # MCP сервер для документации
├── mcp-cloudflare/       # MCP сервер Cloudflare
└── redis/                # Redis для кеширования
```

## 🔧 Управление контейнерами

### Основные команды
```bash
# Просмотр логов всех контейнеров
docker-compose logs -f

# Просмотр логов конкретного контейнера
docker-compose logs -f bot
docker-compose logs -f cloudflared
docker-compose logs -f mcp-supabase

# Перезапуск контейнера
docker-compose restart bot

# Остановка всех контейнеров
docker-compose down

# Запуск с пересборкой
docker-compose up -d --build
```

### Проверка состояния
```bash
# Статус контейнеров
docker-compose ps

# Здоровье сервисов
curl http://localhost:8000/health
curl http://localhost:3001/health  # Supabase MCP
curl http://localhost:3002/health  # DigitalOcean MCP
```

## 🌐 Настройка Cloudflare Tunnel

### Автоматическая настройка
```bash
./scripts/setup_cloudflare.sh
```

### Ручная настройка
1. Установите cloudflared:
   ```bash
   # Linux
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
   chmod +x cloudflared
   sudo mv cloudflared /usr/local/bin/
   
   # macOS
   brew install cloudflare/cloudflare/cloudflared
   ```

2. Создайте туннель:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create artem-integrator
   ```

3. Получите токен:
   ```bash
   cloudflared tunnel token artem-integrator
   ```

4. Добавьте токен в .env:
   ```env
   CLOUDFLARE_TUNNEL_TOKEN=your_token_here
   ```

## 📱 MCP команды в Telegram

### Управление MCP серверами
```
/mcp status          # Статус всех MCP серверов
/mcp start supabase  # Запуск MCP сервера
/mcp stop cloudflare # Остановка MCP сервера
/mcp logs context7   # Просмотр логов
```

### Работа с базами данных (Supabase)
```
/db SELECT * FROM users
/db CREATE TABLE products (id INT, name TEXT)
/db SHOW TABLES
```

### Управление инфраструктурой (DigitalOcean)
```
/mcp apps           # Список приложений
/mcp deployments    # История деплоев
```

### Поиск документации (Context7)
```
/docs react hooks
/docs python asyncio
```

### Cloudflare операции
```
/mcp workers        # Список Workers
/mcp zones          # Список доменов
```

## 🔍 Отладка

### Проблемы с Docker
```bash
# Проверка Docker
docker --version
docker-compose --version

# Права доступа
sudo usermod -aG docker $USER
newgrp docker

# Очистка
docker system prune -a
```

### Проблемы с Cloudflare Tunnel
```bash
# Проверка туннеля
cloudflared tunnel info

# Логи туннеля
docker-compose logs cloudflared

# Перезапуск туннеля
docker-compose restart cloudflared
```

### Проблемы с MCP
```bash
# Проверка MCP сервера
docker-compose logs mcp-supabase

# Тест MCP endpoint
curl http://localhost:3001/mcp/tools

# Перезапуск MCP
docker-compose restart mcp-supabase
```

## 🚀 Продакшн деплой

### 1. На VPS/сервере
```bash
# Клонирование
git clone https://github.com/your-repo/artem-integrator
cd artem-integrator

# Настройка
cp .env.docker .env
# Отредактируйте .env

# Запуск
./docker_start.sh
```

### 2. С автозапуском
```bash
# Создание systemd сервиса
sudo tee /etc/systemd/system/artem-integrator.service > /dev/null <<EOF
[Unit]
Description=Artem Integrator Docker
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/artem-integrator
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Включение автозапуска
sudo systemctl enable artem-integrator
sudo systemctl start artem-integrator
```

## 📊 Мониторинг

### Grafana + Prometheus (опционально)
```yaml
# Добавить в docker-compose.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

### Логирование
```bash
# Настройка централизованного логирования
docker-compose logs -f | tee -a logs/docker.log
```

## 🛡️ Безопасность

### Рекомендации
1. **Используйте secrets** для чувствительных данных
2. **Ограничьте сеть** между контейнерами
3. **Регулярно обновляйте** образы
4. **Мониторьте логи** на подозрительную активность

### Docker secrets
```yaml
# docker-compose.yml
secrets:
  telegram_token:
    external: true
  anthropic_key:
    external: true
```

## 📚 Дополнительные ресурсы

- [Docker документация](https://docs.docker.com/)
- [Cloudflare Tunnel документация](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [MCP спецификация](https://modelcontextprotocol.org/)

---

**С любовью сделано для удобной работы с MCP через Docker и Cloudflare! 🚀**