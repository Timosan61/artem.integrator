# 🚀 Artem Integrator + MCP - Быстрый старт за 1 минуту

## ✅ Что сделано:

1. **Claude Code SDK установлен** - MCP функции доступны
2. **Автоматическая авторизация** - первый пользователь становится админом
3. **Веб-интерфейс настройки** - http://localhost:8000/setup
4. **Команды MCP** - `/mcp`, `/db`, `/docs`
5. **Скрипты запуска** - `./auto_start.sh`, `./install.sh`

## 📱 Как протестировать MCP через Telegram:

### 1. Запустите бота (он уже запущен)
```bash
./auto_start.sh
```

### 2. Откройте Telegram
- Найдите вашего бота: @artem_integrator_bot
- Отправьте `/start` - вы автоматически станете администратором
- Отправьте `/help` - увидите все доступные команды

### 3. Тестируйте MCP команды
```
/mcp list tools              # Список всех MCP инструментов
/db SHOW TABLES              # Работа с базами данных
/docs FastAPI authentication # Поиск документации
```

## 🌐 Веб-интерфейсы:

- **Настройка**: http://localhost:8000/setup
- **Статус**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs (в debug режиме)

## 🔧 Настройка HTTPS (для webhook):

### Вариант 1: Ngrok (у вас есть ключ)
```bash
# Добавьте в .env:
NGROK_API_KEY=2zWyBoccEWDF7IEs0kp1z7MRldl_5qwwZ9pCYEA9LRwuhKSEh

# Перезапустите с auto_start.sh
./auto_start.sh
```

### Вариант 2: Cloudflare Tunnel
```bash
# Установка cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Запуск туннеля
cloudflared tunnel --url http://localhost:8000
```

## 📋 Все доступные команды:

### Для всех:
- `/start` - Начать (первый пользователь = админ)
- `/help` - Помощь
- `/mcp_enable` - Активировать MCP доступ

### Для админов:
- `/mcp` - Общий доступ к MCP
- `/db <query>` - SQL запросы
- `/docs <query>` - Поиск документации
- `/clear` - Очистить память
- `/youtube <url>` - Анализ видео

## 🎯 Что можно делать с MCP:

1. **Работа с базами данных**
   ```
   /db CREATE TABLE users (id INT, name VARCHAR(255))
   /db SELECT * FROM users
   /db SHOW DATABASES
   ```

2. **Поиск документации**
   ```
   /docs how to use React hooks
   /docs Python asyncio
   /docs FastAPI middleware
   ```

3. **MCP инструменты**
   ```
   /mcp list servers
   /mcp help
   ```

## ❓ Если что-то не работает:

1. **Проверьте логи**: `tail -f bot.log`
2. **Проверьте статус**: http://localhost:8000/
3. **Перезапустите**: `pkill -f uvicorn && ./auto_start.sh`

---

**Готово к использованию! Откройте Telegram и начните с команды /start 🚀**