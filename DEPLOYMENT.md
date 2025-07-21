# Развертывание Artem Integrator на DigitalOcean

## 🚀 Быстрый старт

### Вариант 1: Прямой деплой на Droplet (рекомендуется)

Используйте готовый скрипт для развертывания на вашем droplet:

```bash
./deploy_to_digitalocean.sh
```

Скрипт автоматически:
- ✅ Установит все зависимости (Python, Node.js, Claude Code CLI)
- ✅ Настроит приложение и виртуальное окружение
- ✅ Создаст systemd сервис
- ✅ Настроит Nginx как reverse proxy
- ✅ Установит SSL сертификат (Let's Encrypt)
- ✅ Настроит Telegram webhook

### Вариант 2: Деплой через MCP DigitalOcean

Используйте MCP для управления приложением через App Platform:

```bash
# Проверить MCP статус
python deploy_with_mcp.py status

# Список приложений
python deploy_with_mcp.py list

# Полный деплой
python deploy_with_mcp.py deploy
```

## 📋 Предварительные требования

### Для Droplet деплоя:
1. **DigitalOcean Droplet**:
   - IP: 129.212.141.72
   - OS: Ubuntu 22.04 LTS
   - Минимум: 1 vCPU, 2GB RAM
   - SSH доступ настроен

2. **Домен** (опционально):
   - DNS A-запись указывает на IP droplet
   - Для SSL сертификата

3. **Токены и ключи**:
   - Telegram Bot Token
   - OpenAI API Key
   - Anthropic API Key (для MCP)
   - Supabase URL и Key
   - DigitalOcean Token

### Для MCP деплоя:
1. **Claude Code** установлен локально
2. **MCP серверы** настроены в `data/mcp-servers.json`
3. **Переменные окружения** в `.env`

## 🔧 Конфигурация

### 1. Обновите переменные окружения

После деплоя отредактируйте `.env` на сервере:

```bash
ssh root@129.212.141.72 'nano /opt/artem-integrator/.env'
```

Обязательные переменные:
```env
# Telegram
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_SECRET=your_secret
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# AI Services
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# MCP Servers
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
DIGITALOCEAN_TOKEN=your_do_token

# Admin
ADMIN_IDS=your_telegram_id
```

### 2. Настройте домен (если есть)

Обновите переменную `DOMAIN` в скрипте деплоя:
```bash
DOMAIN="bot.yourdomain.com"
```

### 3. Настройте GitHub (для автодеплоя)

Если используете приватный репозиторий:
```bash
ssh root@129.212.141.72
cd /opt/artem-integrator
git remote set-url origin git@github.com:username/repo.git
```

## 🚀 Процесс деплоя

### Шаг 1: Подготовка
```bash
# Клонируйте репозиторий локально
git clone https://github.com/anetov/artem.integrator.git
cd artem.integrator

# Проверьте SSH доступ к droplet
ssh root@129.212.141.72 'echo "SSH работает"'
```

### Шаг 2: Запустите деплой
```bash
# Сделайте скрипт исполняемым
chmod +x deploy_to_digitalocean.sh

# Запустите деплой
./deploy_to_digitalocean.sh
```

### Шаг 3: Настройте конфигурацию
```bash
# Отредактируйте .env на сервере
ssh root@129.212.141.72 'nano /opt/artem-integrator/.env'

# Перезапустите сервис
ssh root@129.212.141.72 'systemctl restart artem-integrator'
```

### Шаг 4: Проверьте работу
```bash
# Используйте скрипт мониторинга
./monitor_bot.sh

# Или вручную
ssh root@129.212.141.72 'systemctl status artem-integrator'
ssh root@129.212.141.72 'tail -f /opt/artem-integrator/logs/bot.log'
```

## 📊 Мониторинг и управление

### Полезные команды

**Статус сервиса:**
```bash
ssh root@129.212.141.72 'systemctl status artem-integrator'
```

**Логи в реальном времени:**
```bash
ssh root@129.212.141.72 'tail -f /opt/artem-integrator/logs/bot.log'
```

**Перезапуск бота:**
```bash
ssh root@129.212.141.72 'systemctl restart artem-integrator'
```

**Обновление кода:**
```bash
ssh root@129.212.141.72 'cd /opt/artem-integrator && git pull && systemctl restart artem-integrator'
```

**Проверка webhook:**
```bash
ssh root@129.212.141.72 'cd /opt/artem-integrator && source venv/bin/activate && python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv(\"TELEGRAM_TOKEN\")
r = requests.get(f\"https://api.telegram.org/bot{TOKEN}/getWebhookInfo\")
print(r.json()[\"result\"])
"'
```

### MCP команды в боте

После успешного деплоя админы могут использовать:

```
/mcp status - статус MCP серверов
/mcp projects - список Supabase проектов
/db SELECT * FROM users - SQL запросы
/mcp apps - список DigitalOcean приложений
/docs react hooks - поиск документации
```

## 🔒 Безопасность

1. **SSH ключи**: Используйте только SSH ключи, не пароли
2. **Firewall**: Настройте ufw на droplet
3. **SSL**: Всегда используйте HTTPS для webhook
4. **Секреты**: Храните токены только в `.env`
5. **Обновления**: Регулярно обновляйте систему

## 🚨 Решение проблем

### Бот не отвечает
1. Проверьте статус сервиса
2. Проверьте логи на ошибки
3. Проверьте webhook статус
4. Убедитесь что все токены правильные

### MCP не работает
1. Проверьте что MCP_ENABLED=true
2. Проверьте наличие Anthropic API key
3. Проверьте логи Claude Code Service
4. Используйте `/mcp status` для диагностики

### SSL проблемы
1. Убедитесь что домен указывает на сервер
2. Проверьте что порт 80 открыт
3. Запустите certbot вручную

## 📝 Обновление

Для обновления бота на продакшене:

```bash
# Автоматическое обновление
ssh root@129.212.141.72 '
cd /opt/artem-integrator
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart artem-integrator
'

# Или используйте GitHub Actions (если настроено)
git push origin main
```

## 🤝 Поддержка

При проблемах:
1. Проверьте DEBUG_HISTORY.md
2. Изучите логи сервиса
3. Используйте MCP для диагностики
4. Создайте issue в репозитории