# Troubleshooting Webhook Issues

## Общие проблемы и решения

### 1. Webhook не устанавливается

#### Симптомы:
- Ошибка "Invalid webhook URL"
- Бот не получает сообщения
- getWebhookInfo показывает пустой URL

#### Решения:

**Для локальной разработки (Cloudflare Tunnel):**
```bash
# 1. Убедитесь что cloudflared запущен
ps aux | grep cloudflared

# 2. Перезапустите туннель
pkill cloudflared
./cloudflared tunnel --url http://localhost:8000

# 3. Проверьте что туннель работает
curl https://your-tunnel.trycloudflare.com/

# 4. Переустановите webhook
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-tunnel.trycloudflare.com/webhook",
    "secret_token": "your_secret_token"
  }'
```

**Для production (Railway):**
```bash
# 1. Проверьте что Railway деплой успешен
railway logs --service web

# 2. Проверьте доступность сервиса
curl https://your-app.up.railway.app/

# 3. Переустановите webhook
curl https://your-app.up.railway.app/webhook/set
```

### 2. Бот не отвечает на сообщения

#### Симптомы:
- Webhook установлен, но бот молчит
- В логах нет входящих запросов
- pending_update_count растет

#### Решения:

```bash
# 1. Проверьте webhook info
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo | jq .

# 2. Проверьте last_error_message
# Если есть ошибки - исправьте их

# 3. Проверьте secret_token
# В .env должен быть:
WEBHOOK_SECRET_TOKEN=your_secret_token

# 4. Проверьте логи бота
tail -f webhook*.log
# или для Railway:
railway logs --service web --tail
```

### 3. Ошибки HTML парсинга

#### Симптомы:
- В логах: "Can't parse entities"
- Сообщения не отправляются
- Ошибки с символами < и >

#### Решения:

```python
# В коде бота экранируйте HTML:
def escape_html(text):
    return text.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')

# Или используйте markdown вместо HTML:
parse_mode="Markdown"  # вместо "HTML"
```

### 4. Проблемы с Cloudflare Tunnel

#### Симптомы:
- Туннель постоянно переподключается
- URL меняется при перезапуске
- Соединение нестабильное

#### Решения:

```bash
# 1. Используйте именованный туннель (требует аккаунт Cloudflare)
cloudflared tunnel login
cloudflared tunnel create artem-bot
cloudflared tunnel run artem-bot

# 2. Проверьте версию cloudflared
./cloudflared --version
# Обновите если старая версия

# 3. Используйте systemd для автозапуска
sudo cp cloudflared.service /etc/systemd/system/
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### 5. Webhook timeout

#### Симптомы:
- last_error_message: "Wrong response from the webhook: 504 Gateway Time-out"
- Бот обрабатывает сообщения слишком долго

#### Решения:

```python
# 1. Используйте background tasks
from fastapi import BackgroundTasks

@app.post("/webhook")
async def webhook(update: dict, background_tasks: BackgroundTasks):
    # Быстро отвечаем Telegram
    background_tasks.add_task(process_update, update)
    return {"ok": True}

# 2. Оптимизируйте обработку
# - Кешируйте частые запросы
# - Используйте async/await правильно
# - Уменьшите количество API вызовов
```

### 6. Дублирование сообщений

#### Симптомы:
- Бот отвечает несколько раз
- Одно сообщение обрабатывается многократно

#### Решения:

```python
# 1. Проверяйте update_id
processed_updates = set()

@app.post("/webhook")
async def webhook(update: dict):
    update_id = update.get("update_id")
    if update_id in processed_updates:
        return {"ok": True}
    processed_updates.add(update_id)
    
    # Обработка...

# 2. Правильно отвечайте на webhook
# Всегда возвращайте 200 OK
return {"ok": True}
```

### 7. Business API не работает

#### Симптомы:
- Бот не отвечает в Business чатах
- business_connection не приходит

#### Решения:

```bash
# 1. Проверьте allowed_updates при установке webhook
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-url.com/webhook",
    "secret_token": "token",
    "allowed_updates": ["message", "callback_query", "business_message", "business_connection"]
  }'

# 2. Проверьте что бот подключен к Business аккаунту
# Settings → Business → Chatbots
```

## Диагностические команды

### Базовая диагностика
```bash
# 1. Статус бота
curl https://your-app.up.railway.app/

# 2. Webhook info
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo | jq .

# 3. Последние обновления (debug endpoint)
curl https://your-app.up.railway.app/debug/last-updates | jq .

# 4. Проверка Voice Service
curl https://your-app.up.railway.app/debug/voice-status
```

### Логирование
```bash
# Локальные логи
tail -f webhook*.log bot*.log mcp*.log

# Railway логи
railway logs --service web --tail

# Поиск ошибок
grep -i "error\|exception\|failed" *.log | tail -50
```

### Тестирование webhook
```bash
# Отправить тестовый update
curl -X POST https://your-url.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your_secret_token" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {"id": 123, "first_name": "Test"},
      "chat": {"id": 123, "type": "private"},
      "date": 1234567890,
      "text": "/start"
    }
  }'
```

## Полезные ссылки

- [Telegram Bot API - Webhooks](https://core.telegram.org/bots/webhooks)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Railway Troubleshooting](https://docs.railway.app/troubleshoot/deployment)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)