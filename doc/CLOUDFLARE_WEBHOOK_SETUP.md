# Настройка Webhook через Cloudflare Tunnel

## Обзор

Cloudflare Tunnel предоставляет безопасный способ создания публичного URL для локально запущенного бота без необходимости настройки портов или использования ngrok.

## Преимущества Cloudflare Tunnel

- ✅ **Бесплатный** для базового использования
- ✅ **Стабильный** - URL не меняется при перезапуске
- ✅ **Безопасный** - трафик проходит через CDN Cloudflare
- ✅ **Быстрый** - глобальная сеть Cloudflare
- ✅ **Простой** - не требует сложной настройки

## Установка cloudflared

### 1. Скачивание cloudflared

```bash
# Для Linux amd64
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64

# Сделать исполняемым
chmod +x cloudflared

# Проверить версию
./cloudflared --version
```

### 2. Альтернативная установка через скрипт

В проекте есть готовый скрипт установки:

```bash
bash scripts/setup_cloudflare.sh
```

## Настройка Cloudflare Tunnel

### Быстрый запуск (Quick Tunnel)

Для тестирования можно использовать Quick Tunnel без аккаунта Cloudflare:

```bash
# Запустить туннель для локального порта 8000
./cloudflared tunnel --url http://localhost:8000
```

Вывод покажет публичный URL вида:
```
https://broadcasting-sewing-hoped-horror.trycloudflare.com
```

### Production настройка (с аккаунтом Cloudflare)

1. **Добавить API токен в .env:**
```env
CLOUDFLARE_API_TOKEN=ваш_токен_здесь
```

2. **Создать именованный туннель:**
```bash
# Авторизация
cloudflared tunnel login

# Создание туннеля
cloudflared tunnel create artem-integrator

# Получить токен туннеля
cloudflared tunnel token artem-integrator
```

3. **Добавить токен в .env:**
```env
CLOUDFLARE_TUNNEL_TOKEN=полученный_токен
```

## Установка Webhook в Telegram

### Автоматическая установка

Если настроен `CloudflareTunnelService`, webhook установится автоматически при запуске бота.

### Ручная установка

```bash
# Установить webhook
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-tunnel-url.trycloudflare.com/webhook",
    "secret_token": "ваш_секретный_токен",
    "allowed_updates": ["message", "callback_query", "business_message", "business_connection"]
  }'
```

### Проверка webhook

```bash
# Получить информацию о webhook
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo | jq .
```

Успешный ответ:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-tunnel-url.trycloudflare.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40,
    "ip_address": "104.16.231.132"
  }
}
```

## Запуск бота с Cloudflare Tunnel

### 1. Запустить бота локально:
```bash
python run_bot.py
# или
python -m bot.webhook.app
```

### 2. Запустить Cloudflare туннель:
```bash
# В отдельном терминале
./cloudflared tunnel --url http://localhost:8000
```

### 3. Установить webhook (если не установлен автоматически)

## Проверка работы

### 1. Проверить статус бота:
```bash
curl http://localhost:8000/
```

### 2. Проверить последние обновления:
```bash
curl http://localhost:8000/debug/last-updates | jq .
```

### 3. Проверить логи:
```bash
# Просмотр логов бота
tail -f *.log

# Проверить логи Cloudflare туннеля
# (выводятся в консоль где запущен cloudflared)
```

## Systemd сервис (опционально)

Для автозапуска можно создать systemd сервисы:

### cloudflared.service
```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
ExecStart=/usr/local/bin/cloudflared tunnel --url http://localhost:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### artem-bot.service
```ini
[Unit]
Description=Artem Integrator Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 run_bot.py
Restart=always
RestartSec=10
Environment="PYTHONPATH=/path/to/project"

[Install]
WantedBy=multi-user.target
```

## Решение проблем

### Webhook не устанавливается
- Проверьте, что туннель запущен и доступен
- Убедитесь, что URL правильный (с /webhook в конце)
- Проверьте токен бота

### Бот не получает сообщения
- Проверьте `getWebhookInfo` - должен показывать установленный URL
- Проверьте `pending_update_count` - если больше 0, есть необработанные сообщения
- Проверьте логи cloudflared на предмет входящих запросов

### Ошибка "invalid webhook URL"
- URL должен быть HTTPS
- URL должен быть публично доступен
- Проверьте, что туннель работает: `curl https://your-tunnel-url.trycloudflare.com/`

## Безопасность

1. **Секретный токен**: Всегда используйте `secret_token` при установке webhook
2. **HTTPS**: Cloudflare автоматически обеспечивает HTTPS
3. **IP фильтрация**: Можно ограничить доступ только с IP Telegram (необязательно)

## Альтернативы

- **ngrok**: Популярная альтернатива, но требует аккаунт для стабильного URL
- **localtunnel**: Бесплатный, но менее стабильный
- **Собственный VPS**: Полный контроль, но требует настройки