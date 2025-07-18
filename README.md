
## 📋 Описание

Telegram бот-консультант для автоматизации клиентских запросов о производстве одежды. Интегрируется с вашим личным Telegram Premium аккаунтом для автоматических ответов от вашего имени.

**Возможности:**
- ✅ Консультации по производству одежды  
- ✅ Информация о ценах и условиях работы
- ✅ Техническая поддержка и FAQ
- ✅ AI-powered ответы (OpenAI + Zep Memory)
- ✅ **Telegram Business API** - отвечает от вашего имени
- ✅ Веб-админка для управления
- ✅ Webhook режим для мгновенных ответов

## 🚀 Быстрый старт

### Основной webhook сервер (Railway)
```bash
# Автоматически запускается в Railway
python webhook.py
```

### Локальное тестирование
```bash
# Проверка Business API
python3 check_business_api.py

# Тест отправки сообщений
python3 test_business_api.py
```

### Админ панель
```bash
# На сервере
python run_admin.py

# SSH туннель с компьютера  
ssh -L 8502:localhost:8501 coder@104.248.39.106

# Браузер: http://localhost:8502
# Пароль: password
```

## 🔧 Конфигурация

### Переменные в Railway:
- `TELEGRAM_BOT_TOKEN` - токен бота
- `OPENAI_API_KEY` - AI ответы (обязательно)
- `ZEP_API_KEY` - память диалогов  
- `WEBHOOK_SECRET_TOKEN` - безопасность webhook
- `BOT_USERNAME` - @artyom_integrator_bot

### Telegram Business настройки:
1. Откройте **Settings → Business → Chatbots**
2. Выберите **@artyom_integrator_bot**
3. Включите **Reply to messages**
4. Бот будет отвечать от вашего имени

## 📁 Структура

```
├── bot/                    # Основной код бота
│   ├── agent.py           # AI логика (OpenAI + Zep)
│   └── config.py          # Конфигурация
├── admin/                  # Streamlit админ панель
├── data/                   # Инструкции и конфигурация
├── webhook.py             # Главный webhook сервер
├── check_business_api.py  # Диагностика Business API
├── test_business_api.py   # Тестирование отправки
├── requirements.txt       # Зависимости Python
└── Dockerfile.complete    # Docker конфигурация
```

## 🚢 Деплой

- **Платформа:** Railway.app
- **Автодеплой:** Git push → Railway redeploy
- **Webhook URL:** https://artyom-integrator-production.up.railway.app/webhook
- **Мониторинг:** 
  - Статус: https://artyom-integrator-production.up.railway.app/
  - Последние события: /debug/last-updates
  - Webhook инфо: /webhook/info

## 📱 Business API

Бот интегрирован с Telegram Business API и может отвечать от имени вашего Premium аккаунта:

1. **Клиент** → пишет в ваши личные сообщения
2. **Telegram** → отправляет `business_message` на webhook бота
3. **Бот** → генерирует AI ответ через OpenAI
4. **Business API** → отправляет ответ от вашего имени
5. **Клиент** → видит ответ как будто это написали вы

Подробнее: [BUSINESS_API_GUIDE.md](./BUSINESS_API_GUIDE.md)

## 🛠 Отладка

При проблемах с Business API:
1. Запустите `python3 check_business_api.py`
2. Проверьте `/debug/last-updates` после тестового сообщения
3. Смотрите логи в Railway Dashboard

## 👥 Команда

Создано для Textil PRO с использованием Claude Code