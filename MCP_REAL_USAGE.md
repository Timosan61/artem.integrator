# 🔌 Реальное использование MCP с Claude Code SDK

## 📋 Текущее состояние

### ✅ Что готово:
1. **Claude Code SDK v0.0.14** - последняя версия установлена
2. **Переключение на реальный SDK** - эмуляция отключена
3. **MCP конфигурация** - созданы файлы конфигурации
4. **Docker контейнеры** - подготовлены MCP серверы

### 🚀 Как включить реальный MCP

#### Вариант 1: Использование Docker MCP серверов
```bash
# 1. Запустите Docker контейнеры
./docker_start.sh

# 2. Убедитесь что в .env установлены токены:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_key
DIGITALOCEAN_API_TOKEN=your_token
CLOUDFLARE_API_TOKEN=your_token
CONTEXT7_API_KEY=your_key

# 3. Используйте локальную конфигурацию
export MCP_CONFIG_PATH=data/mcp-servers.json
```

#### Вариант 2: Использование официальных MCP серверов
```bash
# 1. Установите Node.js если нет
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Используйте официальную конфигурацию
export MCP_CONFIG_PATH=data/mcp-servers-official.json
export MCP_USE_OFFICIAL=true

# 3. Запустите бота
./auto_start.sh
```

## 🔍 Как работает интеграция

### Поток данных:
```
Telegram → Bot → claude_code_service → Claude Code SDK → MCP серверы
```

### Пример работы:
1. Пользователь: `/db SELECT * FROM users`
2. Bot: Принимает команду
3. `claude_code_service`:
   - Формирует промпт для Claude Code
   - Вызывает `query()` из SDK
   - SDK подключается к MCP серверу Supabase
   - Выполняет SQL запрос
   - Возвращает результат
4. Bot: Отправляет результат пользователю

## 🛠️ Отладка

### Проверка работы SDK:
```python
# В bot/services/claude_code_service.py
# Логи покажут:
# 🚀 Используем реальный Claude Code SDK - SDK работает
# ⚠️ SDK недоступен, работаем в режиме эмуляции - SDK не работает
```

### Проверка MCP серверов:
```bash
# Docker контейнеры
docker-compose logs mcp-supabase
docker-compose logs mcp-digitalocean

# Официальные серверы (проверка установки)
npx -y @modelcontextprotocol/server-supabase --version
```

### Типичные проблемы:

1. **"SDK недоступен"**:
   - Проверьте установку: `pip show claude-code-sdk`
   - Переустановите: `pip install claude-code-sdk==0.0.14 --force-reinstall`

2. **"Ошибка SDK"**:
   - Проверьте ANTHROPIC_API_KEY в .env
   - Проверьте доступность MCP серверов
   - Смотрите логи: `tail -f bot.log`

3. **"MCP сервер не отвечает"**:
   - Для Docker: `docker-compose ps`
   - Для официальных: проверьте Node.js и npx

## 📊 Мониторинг

### Логирование:
```bash
# Включите debug режим в .env
DEBUG=true

# Смотрите подробные логи
tail -f bot.log | grep -E "(MCP|SDK|claude_code)"
```

### Метрики:
- Количество успешных MCP вызовов
- Время выполнения команд
- Ошибки и fallback на эмуляцию

## 🔧 Настройка для продакшена

1. **Оптимизация**:
   ```env
   # Кеширование MCP ответов
   MCP_CACHE_ENABLED=true
   MCP_CACHE_TTL=300
   ```

2. **Безопасность**:
   - Используйте отдельные API ключи для каждого сервера
   - Ограничьте доступ к MCP командам только админам
   - Логируйте все MCP операции

3. **Масштабирование**:
   - Запускайте MCP серверы на отдельных машинах
   - Используйте load balancer для распределения нагрузки

## 🎯 Следующие шаги

1. **Добавить больше MCP серверов**:
   - GitHub
   - AWS
   - Google Cloud

2. **Улучшить обработку ошибок**:
   - Retry механизм
   - Более подробные сообщения об ошибках
   - Автоматическое восстановление

3. **Расширить функциональность**:
   - Batch операции
   - Streaming ответы
   - Webhook интеграция

---

**Теперь Claude Code SDK действительно используется для выполнения MCP команд! 🚀**