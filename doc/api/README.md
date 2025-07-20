# 📚 API Reference

## Обзор

Artyom Integrator предоставляет REST API для взаимодействия с ботом и управления его функциями. API построен на FastAPI и поддерживает автоматическую документацию через OpenAPI.

## Базовый URL

```
https://your-app.up.railway.app
```

## Аутентификация

### Webhook Token

Для Telegram webhook используется проверка секретного токена:

```http
X-Telegram-Bot-Api-Secret-Token: your-secret-token
```

### Admin Token

Для административных endpoints:

```http
X-Admin-Token: your-admin-token
```

## Endpoints

### 🏥 Health Check

#### `GET /`

Проверка статуса сервера.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "2.0.0",
  "services": {
    "telegram": "✅",
    "openai": "✅",
    "mcp": "✅"
  }
}
```

### 📨 Webhook

#### `POST /webhook`

Основной endpoint для приема updates от Telegram.

**Headers:**
```
X-Telegram-Bot-Api-Secret-Token: your-secret-token
Content-Type: application/json
```

**Request Body:**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456789,
      "username": "user123",
      "first_name": "John"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "text": "Hello bot!",
    "date": 1234567890
  }
}
```

**Response:**
```json
{
  "ok": true,
  "response_sent": true
}
```

#### `GET /webhook/info`

Получить информацию о текущем webhook.

**Response:**
```json
{
  "url": "https://your-app.up.railway.app/webhook",
  "has_custom_certificate": false,
  "pending_update_count": 0,
  "allowed_updates": ["message", "callback_query", "business_message"],
  "last_error_date": null,
  "last_error_message": null
}
```

#### `GET /webhook/set`

Установить webhook (для браузера).

**Response:**
```json
{
  "ok": true,
  "description": "Webhook was set",
  "url": "https://your-app.up.railway.app/webhook"
}
```

### 🐛 Debug Endpoints

*Доступны только в debug режиме*

#### `GET /debug/last-updates`

Получить последние 10 updates.

**Response:**
```json
{
  "count": 3,
  "updates": [
    {
      "id": 1,
      "timestamp": "2024-01-01T12:00:00Z",
      "update": { ... }
    }
  ]
}
```

#### `GET /debug/config`

Получить текущую конфигурацию (без секретов).

**Response:**
```json
{
  "environment": "production",
  "debug": false,
  "services": {
    "telegram": true,
    "openai": true,
    "mcp": true
  }
}
```

#### `GET /debug/metrics`

Получить метрики производительности.

**Response:**
```json
{
  "system": {
    "cpu": {
      "current": 15.2,
      "avg_1min": 12.5
    },
    "memory": {
      "current_mb": 256.5,
      "current_percent": 25.5
    }
  },
  "top_functions": [
    {
      "name": "process_message",
      "count": 1000,
      "avg_time": 0.123
    }
  ]
}
```

### 👨‍💼 Admin Endpoints

*Требуют админский токен*

#### `POST /admin/reload-prompt`

Перезагрузить инструкции AI из файла.

**Headers:**
```
X-Admin-Token: your-admin-token
```

**Response:**
```json
{
  "success": true,
  "message": "Instructions reloaded successfully"
}
```

#### `POST /admin/clear-memory/{user_id}`

Очистить память конкретного пользователя.

**Response:**
```json
{
  "success": true,
  "message": "Memory cleared for user 123456789"
}
```

#### `GET /admin/stats`

Получить статистику бота.

**Response:**
```json
{
  "users": {
    "total": 150,
    "active_today": 45,
    "active_week": 89
  },
  "messages": {
    "total": 5000,
    "today": 234,
    "avg_response_time": 1.23
  },
  "errors": {
    "today": 5,
    "week": 23
  }
}
```

#### `POST /admin/broadcast`

Отправить сообщение пользователям.

**Request Body:**
```json
{
  "message": "Важное обновление!",
  "user_ids": [123456789, 987654321],
  "parse_mode": "HTML"
}
```

**Response:**
```json
{
  "sent": 2,
  "failed": 0,
  "details": []
}
```

### 🧪 Test Endpoints

*Доступны только в development*

#### `POST /test/message`

Отправить тестовое сообщение боту.

**Request Body:**
```json
{
  "text": "Test message",
  "user_id": 123456789,
  "username": "testuser"
}
```

#### `GET /test/voice-status`

Проверить статус Voice Service.

**Response:**
```json
{
  "enabled": true,
  "whisper_api": "available",
  "last_transcription": "2024-01-01T12:00:00Z"
}
```

## Модели данных

### Message

```python
class Message:
    id: int
    user: User
    chat_id: int
    text: Optional[str]
    type: MessageType
    timestamp: datetime
    metadata: Dict[str, Any]
```

### User

```python
class User:
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    role: UserRole
```

### Response

```python
class Response:
    text: str
    parse_mode: str = "HTML"
    reply_markup: Optional[Any] = None
    metadata: Dict[str, Any] = {}
```

## Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 400 | Неверный формат запроса |
| 401 | Не авторизован |
| 403 | Доступ запрещен |
| 404 | Endpoint не найден |
| 429 | Превышен лимит запросов |
| 500 | Внутренняя ошибка сервера |

## Rate Limiting

- **Webhook**: без ограничений (только от Telegram)
- **Admin API**: 60 запросов в минуту
- **Debug API**: 30 запросов в минуту

## Примеры

### cURL

```bash
# Health check
curl https://your-app.up.railway.app/

# Webhook info
curl https://your-app.up.railway.app/webhook/info

# Admin stats
curl -H "X-Admin-Token: your-token" \
     https://your-app.up.railway.app/admin/stats
```

### Python

```python
import requests

# Health check
response = requests.get("https://your-app.up.railway.app/")
print(response.json())

# Admin broadcast
headers = {"X-Admin-Token": "your-token"}
data = {
    "message": "Hello everyone!",
    "user_ids": [123456789]
}
response = requests.post(
    "https://your-app.up.railway.app/admin/broadcast",
    json=data,
    headers=headers
)
print(response.json())
```

### JavaScript

```javascript
// Health check
fetch('https://your-app.up.railway.app/')
  .then(res => res.json())
  .then(data => console.log(data));

// Admin stats
fetch('https://your-app.up.railway.app/admin/stats', {
  headers: {
    'X-Admin-Token': 'your-token'
  }
})
  .then(res => res.json())
  .then(data => console.log(data));
```

## WebSocket (планируется)

В будущих версиях планируется поддержка WebSocket для:
- Real-time обновления статистики
- Стриминг логов
- Push уведомления

## OpenAPI Schema

Полная OpenAPI документация доступна по адресу:
```
https://your-app.up.railway.app/docs
```

Swagger UI:
```
https://your-app.up.railway.app/docs
```

ReDoc:
```
https://your-app.up.railway.app/redoc
```