# Настройка MCP для Artem Integrator

Полное руководство по настройке Model Context Protocol для автономной работы бота.

## 🎯 Автоматическая установка (Рекомендуется)

Для быстрой настройки используйте установочный скрипт:

```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/artem.integrator.git
cd artem.integrator

# Запустите автоматическую установку
./install.sh
```

Скрипт автоматически:
- ✅ Проверит и установит зависимости (Python, Node.js, Git)
- ✅ Создаст виртуальное окружение Python
- ✅ Установит все необходимые пакеты
- ✅ Настроит MCP серверы для Claude Code SDK
- ✅ Создаст .env файл с примерами переменных
- ✅ Предложит создать systemd сервис для автозапуска

## ⚙️ Ручная настройка

### 1. Подготовка окружения

#### Требования:
- Python 3.8+
- Node.js 18+
- Git

#### Установка зависимостей:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm git
```

**macOS:**
```bash
brew install python node git
```

### 2. Настройка Python окружения

```bash
# Создаем виртуальное окружение
python3 -m venv venv

# Активируем
source venv/bin/activate  # Linux/macOS
# или venv\\Scripts\\activate  # Windows

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_SECRET_TOKEN=your_secret_token_here
BOT_USERNAME=your_bot_username

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-...

# MCP Settings
MCP_ENABLED=true

# DigitalOcean MCP
DIGITALOCEAN_ENABLED=true
DIGITALOCEAN_TOKEN=dop_v1_...

# Supabase MCP
SUPABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Context7 MCP (опционально)
CONTEXT7_ENABLED=true
CONTEXT7_API_KEY=your_context7_key

# Debug & Features
DEBUG=false
VOICE_ENABLED=true
```

### 4. Настройка MCP серверов

#### Автоматическая настройка:
```bash
python3 scripts/setup_mcp.py
```

#### Ручная настройка:

1. **Установите MCP пакеты:**
```bash
npm install -g @digitalocean/mcp
npm install -g @supabase/mcp-server
npm install -g @context-labs/context7-mcp
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-git
```

2. **Настройте конфигурацию Claude Code SDK:**

Файл `~/.config/claude-code/mcp.json`:
```json
{
  "mcpServers": {
    "digitalocean": {
      "command": "npx",
      "args": ["-y", "@digitalocean/mcp"],
      "env": {
        "DIGITALOCEAN_API_TOKEN": "ваш_токен_здесь"
      }
    },
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server"],
      "env": {
        "SUPABASE_URL": "ваш_url_здесь",
        "SUPABASE_SERVICE_ROLE_KEY": "ваш_ключ_здесь"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@context-labs/context7-mcp"],
      "env": {
        "CONTEXT7_API_KEY": "ваш_ключ_здесь"
      }
    }
  }
}
```

## 🚀 Запуск бота

### Локальный запуск:
```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите бота
python run_bot.py
```

### Запуск как сервис (Linux):
```bash
# Запуск
sudo systemctl start artem-integrator

# Остановка
sudo systemctl stop artem-integrator

# Статус
sudo systemctl status artem-integrator

# Логи
journalctl -u artem-integrator -f
```

## 🔧 Архитектура MCP в проекте

### Файловая структура:
```
artem.integrator/
├── data/
│   ├── mcp-servers.json          # Шаблон конфигурации MCP
│   ├── claude_sdk_prompts.yaml   # Промпты для Claude SDK
│   └── mcp_voice_prompts.yaml    # Голосовые команды MCP
├── bot/services/
│   ├── claude_code_service.py    # Основной сервис Claude Code SDK
│   └── unified_mcp_service.py    # Унифицированный MCP сервис
├── scripts/
│   └── setup_mcp.py             # Автоматическая настройка MCP
└── install.sh                   # Полная автоматическая установка
```

### Принцип работы:

1. **Шаблон конфигурации**: `data/mcp-servers.json` содержит шаблон с переменными `{VARIABLE_NAME}`

2. **Подстановка переменных**: `claude_code_service.py` автоматически загружает шаблон и подставляет значения из `.env`

3. **Временный файл**: Создается временный файл конфигурации с реальными значениями

4. **Автономность**: Все настройки хранятся в проекте, не требуют ручной настройки системы

## 📝 Доступные MCP команды

После настройки бот поддерживает следующие команды:

### DigitalOcean Commands:
- `/mcp apps` - Список приложений DigitalOcean App Platform
- `/mcp deployments` - Информация о деплоях
- `/mcp databases` - Управление базами данных

### Supabase Commands:
- `/db SELECT * FROM users` - SQL запросы к базе данных
- `/mcp projects` - Список проектов Supabase

### Context7 Commands:
- `/docs как использовать API` - Поиск в документации

### File System Commands:
- `/files список файлов` - Операции с файловой системой
- `/git статус` - Git операции

## 🔍 Отладка и решение проблем

### Проверка статуса MCP:
```bash
# Проверка конфигурации
cat ~/.config/claude-code/mcp.json

# Проверка установленных пакетов
npm list -g --depth=0 | grep mcp

# Тест MCP команды в боте
# Отправьте боту: /mcp apps
```

### Типичные проблемы:

1. **MCP команды не работают**
   - Проверьте переменные в `.env`
   - Убедитесь что MCP пакеты установлены: `npm list -g`
   - Проверьте конфигурацию: `~/.config/claude-code/mcp.json`

2. **Ошибка "Claude Code SDK недоступен"**
   - Установите/обновите: `pip install claude-code-sdk`
   - Проверьте ANTHROPIC_API_KEY в `.env`

3. **Сервер MCP не отвечает**
   - Проверьте API ключи для конкретного сервера
   - Убедитесь что сервер включен в `.env` (`*_ENABLED=true`)

### Логи для отладки:
```bash
# Локальные логи
tail -f *.log

# Systemd логи
journalctl -u artem-integrator -f

# Python логи внутри приложения
# Проверьте вывод в консоли при запуске python run_bot.py
```

## 🔄 Обновление конфигурации

### Добавление нового MCP сервера:

1. **Обновите `data/mcp-servers.json`:**
```json
{
  "mcpServers": {
    "новый_сервер": {
      "command": "npx",
      "args": ["-y", "@package/new-mcp-server"],
      "env": {
        "API_TOKEN": "{NEW_SERVER_TOKEN}"
      }
    }
  }
}
```

2. **Добавьте переменную в `.env`:**
```bash
NEW_SERVER_TOKEN=your_token_here
```

3. **Перезапустите бота:**
```bash
sudo systemctl restart artem-integrator
```

### Обновление существующих серверов:
```bash
# Переустановка пакетов
npm install -g @digitalocean/mcp@latest

# Обновление конфигурации
python3 scripts/setup_mcp.py

# Перезапуск
sudo systemctl restart artem-integrator
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте все шаги этого руководства
2. Убедитесь что все API ключи корректны
3. Проверьте логи: `journalctl -u artem-integrator -f`
4. Запустите диагностику: `python3 scripts/setup_mcp.py`

**Успешной настройки! 🚀**