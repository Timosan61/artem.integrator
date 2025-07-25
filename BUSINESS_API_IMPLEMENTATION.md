# 📱 Business API Implementation - Artyom Integrator

## ✅ Статус: РЕАЛИЗОВАНО

Business API полностью интегрирован в Artyom Integrator Bot. Пользователи могут писать в личный аккаунт владельца, и бот будет отвечать от его имени согласно инструкциям из Streamlit админки.

## 🎯 Как это работает

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Клиент     │────▶│  Premium         │────▶│  Artyom Bot     │
│             │     │  Аккаунт         │     │                 │
└─────────────┘     └──────────────────┘     └─────────────────┘
       │                     │                         │
       │                     │                         │
       ▼                     ▼                         ▼
 Пишет сообщение    Business API связь       webhook получает
 в личку владельцу   с подключенным ботом    business_message
                                                      │
                                                      ▼
                                             ┌──────────────┐
                                             │  ArtemAgent  │
                                             │ (инструкции  │
                                             │ из админки)  │
                                             └──────────────┘
                                                      │
                                                      ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Клиент     │◀────│  Premium         │◀────│  Business API   │
│             │     │  Аккаунт         │     │   Response      │
└─────────────┘     └──────────────────┘     └─────────────────┘
       ▲                                               │
       │                                               │
       └───────────────────────────────────────────────┘
              Клиент видит ответ от имени владельца
```

## 🔧 Техническая реализация

### 1. Обработка Business Messages

**Файл:** `bot/webhook/handlers.py`

```python
async def _handle_business_message(self, business_message: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает Business API сообщение"""
    
    # Извлекаем business_connection_id
    business_connection_id = business_message.get('business_connection_id')
    
    # Обрабатываем как обычное сообщение, но с флагом Business
    result = await self._handle_message(
        business_message, 
        is_business=True, 
        business_connection_id=business_connection_id
    )
    
    return result
```

### 2. Отправка через Business API

**Функция:** `send_business_message()`

```python
def send_business_message(chat_id: int, text: str, business_connection_id: str) -> Dict[str, Any]:
    """
    Отправка сообщения через Business API используя прямой HTTP запрос
    (pyTelegramBotAPI не поддерживает business_connection_id)
    """
    
    # Валидация входных данных
    if not chat_id or not text.strip() or not business_connection_id:
        return {"success": False, "error": "Invalid parameters"}
    
    # Ограничение длины (4096 символов)
    if len(text) > 4096:
        text = text[:4093] + "..."
    
    # Прямой HTTP запрос к Telegram API
    url = f"https://api.telegram.org/bot{config.telegram.token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "business_connection_id": business_connection_id,
        "parse_mode": "HTML"
    }
    
    # Отправка и обработка ответа
    response = requests.post(url, json=data, timeout=15)
    result = response.json()
    
    if response.status_code == 200 and result.get("ok"):
        return {"success": True, "message_id": result.get('result', {}).get('message_id')}
    else:
        return {"success": False, "error": result.get("description", "Unknown error")}
```

### 3. Агент-роутинг

**Файл:** `bot/core/agent_adapters.py`

Intelligent Agent обрабатывает только MCP команды от владельца бота:

```python
async def can_handle(self, message: Message) -> bool:
    # Только MCP команды от владельца бота
    if message.user.role != UserRole.ADMIN:
        return False
        
    owner_id = config.admin.user_ids[0] if config.admin.user_ids else None
    if owner_id is not None and message.user.id != owner_id:
        return False
        
    return unified_mcp_service.is_mcp_command(message.text)
```

ArtemAgent обрабатывает все остальные сообщения, включая Business:

```python
# Все сообщения, которые не попали к IntelligentAgent, 
# автоматически идут к ArtemAgent (DefaultAgent в цепочке)
```

### 4. Message Structure

**Файл:** `bot/core/interfaces.py`

```python
@dataclass
class Message:
    # ... другие поля ...
    is_business_message: bool = False  # Флаг Business сообщения
    metadata: Dict[str, Any] = None    # Содержит business_connection_id
```

## 🚨 Ключевые особенности

### 1. pyTelegramBotAPI не поддерживает Business API
❌ **Не работает:**
```python
bot.send_message(chat_id, text, business_connection_id=conn_id)
```

✅ **Работает:**
```python
# Прямой HTTP запрос к Telegram API
requests.post("https://api.telegram.org/bot{token}/sendMessage", json={
    "chat_id": chat_id,
    "text": text,
    "business_connection_id": business_connection_id
})
```

### 2. Webhook должен получать business события

**Файл:** `bot/webhook/app.py`

```python
allowed_updates = [
    "message",
    "business_connection", 
    "business_message",
    "edited_business_message",
    "deleted_business_messages"
]
```

### 3. business_connection_id обязателен

- Приходит в каждом `business_message`
- Должен использоваться при отправке ответа
- Сохраняется в `message.metadata["business_connection_id"]`

## 📊 Диагностика и мониторинг

### Команды администратора

**`/business_status`** - Проверка статуса Business API подключений:

```python
elif command == '/business_status':
    connections_info = get_business_connections_info()
    
    if connections_info.get("success"):
        # Показать активные подключения
        status_text = f"📱 Business API Status\nПодключений: {count}"
    else:
        # Показать ошибку
        status_text = f"❌ Business API Error\nОшибка: {error_details}"
```

### Логи для отслеживания

- `📱 Обработка Business сообщения` - входящее сообщение
- `📤 Отправляю Business сообщение` - отправка ответа
- `✅ Business сообщение отправлено успешно` - успех
- `❌ Ошибка отправки Business сообщения` - ошибки

### Функция диагностики

```python
def get_business_connections_info() -> Dict[str, Any]:
    """Получает информацию о Business подключениях бота"""
    
    url = f"https://api.telegram.org/bot{config.telegram.token}/getBusinessConnection"
    response = requests.get(url, timeout=10)
    result = response.json()
    
    if response.status_code == 200 and result.get("ok"):
        connections = result.get("result", [])
        return {
            "success": True,
            "connections_count": len(connections),
            "connections": connections
        }
    else:
        return {
            "success": False,
            "error": "API Error",
            "details": result.get("description", "Unknown error")
        }
```

## 🧪 Тестирование

**Файл:** `test_business_api.py`

Включает тесты:
- ✅ Валидация входных данных
- ✅ Ограничение длины сообщений (4096 символов)
- ✅ Структура Business сообщений
- ✅ Обработка ошибок API

**Запуск тестов:**
```bash
python test_business_api.py
```

## 🎯 Схема обработки сообщений

```
business_message
       │
       ▼
_handle_business_message()
       │
       ▼
_handle_message(is_business=True, business_connection_id=xxx)
       │
       ▼
unified_agent.process_message()
       │
       ▼
ArtemAgent (по инструкции из админки)
       │
       ▼
send_business_message() → Telegram Business API
       │
       ▼
Пользователь видит ответ от имени владельца
```

## 💡 Настройка для пользователя

### 1. Требования:
- Telegram Premium аккаунт
- Подключение бота в Settings → Business → Chatbots
- Включение "Reply to messages"

### 2. В админке Streamlit:
- Настроить инструкции для ArtemAgent
- Они будут использованы для всех Business сообщений

### 3. Для тестирования:
- Команда `/business_status` покажет статус подключений
- Логи покажут весь процесс обработки

## 🔒 Безопасность

- Валидация всех входных данных
- Ограничение длины сообщений
- Обработка всех типов ошибок API
- Таймаут запросов (15 секунд)
- Fallback к обычной отправке при сбоях Business API

## 🎉 Результат

Теперь когда клиенты пишут в личку владельцу бота:

1. **Бот автоматически получает** их сообщения через Business API
2. **ArtemAgent генерирует ответ** согласно инструкциям из Streamlit админки  
3. **Ответ отправляется от имени владельца** через Business API
4. **Клиент думает, что общается с владельцем**, а не с ботом

**Business API полностью функционален!** 🚀