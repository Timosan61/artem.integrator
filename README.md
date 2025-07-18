# 🤖 Artyom Integrator Bot

Современный Telegram бот с AI-powered консультантом для автоматизации клиентских запросов. Интегрируется с Telegram Business API и поддерживает управление внешними сервисами через Model Context Protocol (MCP).

## 🌟 Основные возможности

- **AI Консультант** - интеллектуальные ответы на базе OpenAI/Anthropic
- **Business API** - автоматические ответы от вашего Premium аккаунта
- **Двухрежимная система** - разные возможности для пользователей и администраторов
- **MCP интеграция** - управление Supabase, DigitalOcean, Context7
- **Voice Service** - транскрипция голосовых сообщений
- **Social Media** - интеграция с YouTube, Instagram, TikTok
- **Память диалогов** - через Zep для персонализированных ответов

## 🚀 Быстрый старт

### Основной webhook сервер (Railway)
```bash
# Автоматически запускается в Railway
python webhook.py
```

### Локальное тестирование
```bash
# Проверка Business API
python check_business_api.py

# Тест отправки сообщений
python test_business_api.py
```

### Админ панель
```bash
# Запуск админки
streamlit run admin/mcp_admin.py

# Доступ через браузер
http://localhost:8501
```

## 🔧 Конфигурация

### Основные переменные окружения:
```env
# Telegram (обязательно)
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_ID=your_telegram_id

# AI Providers (минимум один)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Память диалогов
ZEP_API_KEY=your_zep_key
ZEP_API_URL=https://api.getzep.com

# Business API
WEBHOOK_SECRET_TOKEN=your_secret_token
BOT_USERNAME=@artyom_integrator_bot
```

### MCP конфигурация (опционально):
```env
MCP_ENABLED=true
SUPABASE_ENABLED=true
DIGITALOCEAN_ENABLED=true
CONTEXT7_ENABLED=true
DIGITALOCEAN_TOKEN=your_do_token
```

## 📁 Структура проекта

```
├── bot/                    # Основной код бота
│   ├── core/              # Ядро системы
│   │   ├── interfaces.py  # Базовые интерфейсы
│   │   ├── config.py      # Типизированная конфигурация
│   │   ├── agent.py       # Базовый AI агент
│   │   ├── errors.py      # Обработка ошибок
│   │   ├── monitoring.py  # Мониторинг производительности
│   │   └── logging/       # Система логирования
│   ├── webhook/           # Webhook сервер
│   │   ├── app.py         # FastAPI приложение
│   │   ├── handlers.py    # Обработчики Telegram updates
│   │   ├── middleware.py  # Security, logging, errors
│   │   ├── routers/       # API endpoints
│   │   └── services.py    # Бизнес-логика
│   ├── mcp/               # Model Context Protocol
│   │   ├── core/          # Ядро MCP
│   │   ├── servers/       # Реализации серверов
│   │   └── handlers/      # Обработчики команд
│   └── services/          # Внешние сервисы
│       ├── voice_service.py        # Голосовые сообщения
│       ├── social_media_service.py # YouTube, Instagram
│       └── mcp_service.py          # MCP интеграция
├── admin/                  # Веб-интерфейсы
│   └── mcp_admin.py       # Streamlit админка
├── data/                   # Данные и конфигурация
│   ├── instruction.json   # Инструкции для AI
│   └── mcp_config.json    # Конфигурация MCP
├── docs/                   # Документация
│   ├── architecture/      # Архитектурные решения
│   ├── api/              # API документация
│   ├── deployment/       # Руководство по деплою
│   └── development/      # Для разработчиков
└── tests/                 # Тесты
```

## 📱 Telegram Business API

Бот интегрирован с Telegram Business API для автоматических ответов от вашего имени:

### Настройка:
1. Откройте **Settings → Business → Chatbots**
2. Выберите **@artyom_integrator_bot**
3. Включите **Reply to messages**
4. Бот будет отвечать от вашего имени

### Как это работает:
1. **Клиент** → пишет в ваши личные сообщения
2. **Telegram** → отправляет `business_message` на webhook
3. **Бот** → генерирует AI ответ
4. **Business API** → отправляет ответ от вашего имени
5. **Клиент** → видит ответ как будто это написали вы

## 🔌 MCP (Model Context Protocol)

MCP позволяет администраторам управлять внешними сервисами прямо из Telegram:

### Поддерживаемые сервисы:
- **Supabase** - управление базами данных, SQL запросы
- **DigitalOcean** - деплой приложений, мониторинг
- **Context7** - поиск документации, примеры кода

### Команды для администраторов:
```
/mcp status              # Статус всех MCP серверов
/mcp projects            # Список Supabase проектов
/db SELECT * FROM users  # Выполнить SQL запрос
/mcp apps               # Список DigitalOcean приложений
/docs react hooks       # Поиск документации
/mcp help               # Полная справка по командам
```

## 🛠️ Разработка

### Установка для разработки:
```bash
# Клонирование репозитория
git clone https://github.com/Timosan61/artem.integrator.git
cd artem.integrator

# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Зависимости
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Запуск тестов:
```bash
# Все тесты
pytest

# С покрытием
pytest --cov=bot

# Конкретный модуль
pytest tests/test_agent.py
```

### Добавление нового сервиса:
1. Создайте модуль в `bot/services/`
2. Реализуйте интерфейс `BaseService`
3. Зарегистрируйте в конфигурации
4. Добавьте обработчики в webhook

## 🚀 Deployment

### Railway (рекомендуется)
- **Платформа:** Railway.app
- **Автодеплой:** Git push → автоматический деплой
- **Webhook URL:** https://your-app.up.railway.app/webhook
- **Переменные:** настраиваются в Railway Dashboard

### Docker
```bash
# Сборка образа
docker build -t artyom-integrator .

# Запуск контейнера
docker run -p 8000:8000 --env-file .env artyom-integrator
```

### Мониторинг:
- **Статус:** https://your-app.up.railway.app/
- **Webhook info:** /webhook/info
- **Debug (dev):** /debug/last-updates
- **Метрики:** /admin/metrics

## 📊 Мониторинг и логирование

### Встроенная система мониторинга:
- **Структурированные логи** - JSON формат для production
- **Цветные логи** - для development
- **Метрики производительности** - время выполнения, использование памяти
- **Алерты** - автоматические уведомления администраторам об ошибках

### Просмотр логов:
```bash
# Railway CLI
railway logs

# Docker
docker logs container_name

# Локальные файлы
tail -f logs/bot.log
```

## 🛡️ Безопасность

- **Webhook токен** - проверка подлинности запросов от Telegram
- **Админские права** - двухфакторная проверка (ID + username)
- **Rate limiting** - защита от спама
- **Валидация данных** - проверка всех входящих данных
- **Шифрование** - SSL/TLS для всех соединений

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! 

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) для деталей.

## 👥 Команда

- **Разработка**: [Timosan61](https://github.com/Timosan61)
- **AI Assistant**: Claude (Anthropic)
- **Для**: Textile Pro

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/Timosan61/artem.integrator/issues)
- **Telegram**: @your_support_contact

---

<div align="center">

Made with ❤️ by Artyom Integrator Team

[Documentation](docs/) | [API Reference](docs/api/) | [Contributing](CONTRIBUTING.md)

</div>