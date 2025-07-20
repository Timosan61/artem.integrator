# Руководство по тестированию MCP (Model Context Protocol)

## Обзор

Это руководство описывает, как тестировать интеграцию MCP с Telegram ботом Artyom Integrator.

## Варианты тестирования

### 1. Локальное тестирование с Docker Compose

#### Подготовка
1. Скопируйте файл окружения:
   ```bash
   cp .env.test.example .env.test
   ```

2. Заполните переменные в `.env.test`:
   - `TELEGRAM_BOT_TOKEN` - токен тестового бота
   - `OPENAI_API_KEY` - ключ OpenAI
   - `ANTHROPIC_API_KEY` - ключ Anthropic (для MCP)
   - `NGROK_AUTH_TOKEN` - токен ngrok для внешнего доступа

#### Запуск
```bash
./start_local_test.sh
```

Скрипт автоматически:
- Запустит все сервисы через Docker Compose
- Создаст туннель через ngrok
- Покажет URL для webhook
- Выведет команды для управления

#### Полезные команды
```bash
# Логи всех сервисов
docker-compose -f docker-compose.test.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.test.yml logs -f artem-bot
docker-compose -f docker-compose.test.yml logs -f mcp-mock

# Остановить все сервисы
docker-compose -f docker-compose.test.yml down
```

### 2. Автоматическое тестирование

Запустите скрипт автоматического тестирования:
```bash
python test_telegram_mcp.py
```

Скрипт выполнит серию тестов:
- Базовые команды бота
- MCP функции Supabase
- MCP функции DigitalOcean
- MCP функции Context7

Результаты сохраняются в `test_report_*.json`.

### 3. Тестирование через Debug Endpoints

#### MCP Status
```bash
curl http://localhost:8000/debug/mcp-status
```

#### Тест конкретной MCP функции
```bash
curl -X POST http://localhost:8000/debug/mcp-test \
  -H "Content-Type: application/json" \
  -d '{
    "service": "supabase",
    "function": "list_projects",
    "parameters": {}
  }'
```

#### Ping всех MCP серверов
```bash
curl -X POST http://localhost:8000/debug/mcp-ping
```

### 4. Тестирование через Telegram

После настройки webhook отправьте боту команды:

#### Supabase команды
- `/mcp list projects` - список проектов
- `/sql SELECT version()` - SQL запрос
- `/db show tables` - список таблиц

#### DigitalOcean команды
- `/mcp do apps` - список приложений
- `/logs app_123` - логи приложения
- `/deploy app_123` - деплой приложения

#### Context7 команды
- `/docs react hooks` - поиск документации
- `/mcp context7 examples vue` - примеры кода

## Развертывание на DigitalOcean

### 1. Создание Droplet

```bash
# Создать Droplet через doctl
doctl compute droplet create artem-mcp-test \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-2gb \
  --region nyc1 \
  --ssh-keys YOUR_SSH_KEY_ID
```

### 2. Настройка сервера

SSH на сервер и выполните:
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Клонирование репозитория
git clone https://github.com/your-repo/artem.integrator.git
cd artem.integrator

# Настройка окружения
cp .env.test.example .env.test
nano .env.test  # Заполните переменные

# Запуск
docker compose -f docker-compose.test.yml up -d
```

### 3. Настройка домена (опционально)

Для постоянного URL webhook:
1. Добавьте A-запись в DNS
2. Настройте nginx как reverse proxy
3. Получите SSL сертификат через Let's Encrypt

## Мониторинг

### Adminer (управление БД)
http://localhost:8080
- Сервер: `postgres`
- Пользователь: `postgres`
- Пароль: `postgres`
- База: `artem_test`

### Ngrok Dashboard
http://localhost:4040
- Просмотр всех запросов
- Повтор запросов
- Инспекция тела запросов

### MCP Mock Server
http://localhost:9000
- `/health` - статус сервера
- `/supabase/status` - статус Supabase mock
- `/digitalocean/status` - статус DigitalOcean mock
- `/context7/status` - статус Context7 mock

## Troubleshooting

### Проблема: MCP Manager не инициализирован
**Решение**: Проверьте переменную `MCP_ENABLED=true` в окружении

### Проблема: Не работает webhook
**Решение**: 
1. Проверьте ngrok туннель: `docker-compose logs ngrok`
2. Убедитесь, что webhook установлен правильно
3. Проверьте логи бота: `docker-compose logs artem-bot`

### Проблема: MCP функции возвращают ошибки
**Решение**:
1. Проверьте MCP Mock Server: `curl http://localhost:9000/health`
2. Посмотрите логи: `docker-compose logs mcp-mock`
3. Проверьте конфигурацию в `data/mcp_config.json`

## CI/CD

GitHub Actions автоматически запускает тесты при:
- Push в ветки `MCP` или `develop`
- Pull request в `main`
- Ручном запуске workflow

Настройте секреты в репозитории:
- `TEST_BOT_TOKEN` - токен тестового бота
- `OPENAI_API_KEY` - ключ OpenAI
- `ANTHROPIC_API_KEY` - ключ Anthropic
- `NOTIFICATION_BOT_TOKEN` - токен для уведомлений
- `NOTIFICATION_CHAT_ID` - chat ID для уведомлений