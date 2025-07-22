# 🚀 Artem Integrator с MCP - Быстрый запуск

## 🎯 Что это?

Artem Integrator теперь поддерживает MCP (Model Context Protocol) через Claude Code SDK, что позволяет:
- 🔌 Выполнять MCP команды прямо в Telegram
- 🗄️ Работать с базами данных через `/db`
- 📚 Искать документацию через `/docs`
- 🤖 Автоматическая авторизация без ручной настройки

## ⚡ Быстрый старт (1 минута)

### 1. Клонирование и установка
```bash
git clone https://github.com/your-repo/artem-integrator.git
cd artem-integrator
./install.sh
```

### 2. Запуск
```bash
./auto_start.sh
```

### 3. В Telegram
1. Найдите вашего бота
2. Отправьте `/start`
3. Вы автоматически стали администратором!
4. Используйте `/help` для списка команд

## 🔧 Конфигурация

### Минимальная конфигурация (.env)
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Полная конфигурация (.env)
```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_SECRET_TOKEN=auto_generated

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key_here

# Ngrok (опционально)
NGROK_API_KEY=your_ngrok_key_here

# Debug
DEBUG=true

# Voice
VOICE_ENABLED=true
```

## 📱 Команды Telegram

### Для всех пользователей
- `/start` - Начать работу (первый пользователь становится админом)
- `/help` - Показать список команд
- `/mcp_enable` - Активировать MCP функции

### Для администраторов
- `/mcp` - Общий доступ к MCP
- `/db <query>` - Работа с базами данных
- `/docs <query>` - Поиск документации
- `/clear` - Очистить память бота
- `/youtube <url>` - Анализ YouTube видео

## 🎯 Примеры использования MCP

### Работа с базами данных
```
/db SELECT * FROM users LIMIT 5
/db CREATE TABLE products (id INT, name VARCHAR(255))
/db SHOW TABLES
```

### Поиск документации
```
/docs how to use React hooks
/docs Python asyncio examples
/docs FastAPI authentication
```

### Общие MCP команды
```
/mcp list tools
/mcp help
```

## 🔌 Автоматическая система администрирования

1. **Первый пользователь** - автоматически становится администратором при `/start`
2. **Другие пользователи** - могут активировать MCP через `/mcp_enable`
3. **Админы сохраняются** - в `data/auto_admins.json`

## 🌐 Веб-интерфейсы

- `http://localhost:8000/` - Статус бота
- `http://localhost:8000/setup` - Настройка бота
- `http://localhost:8000/docs` - API документация (в debug режиме)
- `http://localhost:8000/debug` - Отладочная информация

## 🚀 Варианты запуска

### 1. Простой запуск
```bash
./start.sh
```

### 2. Автоматический с ngrok
```bash
./auto_start.sh
```

### 3. Через systemd (автозапуск при старте системы)
```bash
sudo systemctl start artem-integrator
sudo systemctl enable artem-integrator
```

### 4. Docker (скоро)
```bash
docker-compose up -d
```

## 🔍 Отладка

### Просмотр логов
```bash
# Логи бота
tail -f bot.log

# Логи ngrok
tail -f ngrok.log

# Systemd логи
sudo journalctl -u artem-integrator -f
```

### Проверка статуса
```bash
# Статус сервиса
sudo systemctl status artem-integrator

# Проверка webhook
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo

# Проверка сервера
curl http://localhost:8000/
```

## ❓ Частые вопросы

### Как получить токены?
1. **Telegram Bot Token**: создайте бота у [@BotFather](https://t.me/BotFather)
2. **Anthropic API Key**: получите на [console.anthropic.com](https://console.anthropic.com)
3. **Ngrok API Key**: зарегистрируйтесь на [ngrok.com](https://ngrok.com)

### Что если MCP не работает?
1. Проверьте установку: `pip show claude-code-sdk`
2. Переустановите: `pip install claude-code-sdk==0.0.13 --no-deps`
3. Проверьте логи: `tail -f bot.log`

### Как добавить администратора вручную?
1. Через веб-интерфейс: `http://localhost:8000/setup`
2. Через команду в Telegram: пусть пользователь отправит `/mcp_enable`
3. Вручную в файле: отредактируйте `data/auto_admins.json`

## 📞 Поддержка

- 📧 Email: support@artem-integrator.com
- 💬 Telegram: @artem_support
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**С любовью сделано для удобной работы с MCP через Telegram! 🚀**