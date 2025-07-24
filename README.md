# Artyom Integrator - AI Telegram Bot

**Artyom Integrator** - это мощный AI-ассистент для Telegram с поддержкой MCP (Model Context Protocol), голосовых сообщений и интеграций с внешними сервисами.

## 🚀 Быстрый старт

```bash
# Клонирование репозитория
git clone https://github.com/your-repo/artem.integrator.git
cd artem.integrator

# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp .env.example .env
# Заполните необходимые переменные в .env

# Запуск бота
python run_bot.py

# Для локальной разработки с webhook используйте Cloudflare Tunnel:
./cloudflared tunnel --url http://localhost:8000
```

## 📚 Документация

Вся документация находится в папке [`doc/`](./doc/):

### Основные руководства
- [📖 Полная документация проекта](./doc/PROJECT_README.md)
- [🛠️ Руководство по установке и деплою](./doc/CLONE_AND_DEPLOY_GUIDE.md)
- [👨‍💼 Руководство администратора](./doc/ADMIN_GUIDE.md)
- [🏢 Business API интеграция](./doc/BUSINESS_API_GUIDE.md)

### MCP (Model Context Protocol)
- [🔌 Использование MCP](./doc/MCP_USAGE.md)
- [🧪 Тестирование MCP](./doc/MCP_TESTING.md)
- [📋 MCP тесты](./doc/MCP_TESTS.md)

### Разработка и архитектура
- [🏗️ Архитектура](./doc/architecture/)
- [💻 Разработка](./doc/development/)
- [🔧 API документация](./doc/api/)
- [🚀 Деплой](./doc/deployment/)

### Дополнительно
- [🎤 Voice Service](./doc/VOICE_SERVICE.md)
- [🤝 Руководство контрибьютора](./doc/CONTRIBUTING.md)

## 🌟 Основные возможности

- **AI-ассистент** на базе OpenAI GPT-4
- **MCP интеграция** через Claude Code SDK:
  - Supabase - управление базами данных
  - DigitalOcean - деплой и инфраструктура
  - Context7 - поиск документации
- **Голосовые сообщения** с транскрипцией через Whisper
- **Business API** поддержка
- **Админ-панель** на Streamlit
- **Система памяти** для контекстных диалогов

## 🛠️ Технологический стек

- **Python 3.11+**
- **FastAPI** - веб-фреймворк
- **OpenAI API** - AI модели
- **PostgreSQL** - база данных
- **Redis** - кеширование
- **Docker** - контейнеризация

## 🚀 Деплой

Проект поддерживает несколько вариантов развертывания:

- **Railway** (рекомендуется для production)
- **DigitalOcean droplet**
- **Docker Compose** (для локальной разработки)


Подробные инструкции в [руководстве по деплою](./doc/deployment/).

## 📞 Поддержка

- Telegram: [@your_support_bot](https://t.me/your_support_bot)
- Email: support@example.com
- Issues: [GitHub Issues](https://github.com/your-repo/artem.integrator/issues)

## 📄 Лицензия

MIT License - см. файл [LICENSE](./LICENSE)

---

💡 **Совет**: Начните с [руководства по быстрому старту](./doc/CLONE_AND_DEPLOY_GUIDE.md) для развертывания бота.