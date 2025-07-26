# API Reference - Система логирования Artyom Integrator

## Обзор API

Данный документ содержит полную техническую документацию по API системы логирования, включая классы, методы, параметры и примеры использования.

## Модуль `logging_utils.py`

### ComponentType

Перечисление типов компонентов системы.

```python
class ComponentType(str, Enum)
```

#### Значения:
- `WEBHOOK` - Webhook обработчики и маршрутизация
- `AGENT` - Система агентов и их адаптеры  
- `MCP` - MCP сервисы и интеграции
- `SERVICE` - Бизнес-сервисы и логика
- `ADAPTER` - Адаптеры интеграций
- `MEMORY` - Система памяти и кэширования
- `AUTH` - Аутентификация и авторизация
- `ERROR` - Обработка ошибок

### TraceContext

Структура данных для контекста трассировки.

```python
@dataclass
class TraceContext:
    trace_id: str                    # Уникальный идентификатор трассировки
    user_id: Optional[str]           # ID пользователя
    session_id: Optional[str]        # ID сессии
    operation: str                   # Название выполняемой операции
    metadata: Dict[str, Any]         # Дополнительные метаданные
```

### Функции логирования

#### `get_structured_logger(name: str, component: ComponentType) -> StructuredLogger`

Создает структурированный логгер для компонента.

**Параметры:**
- `name` - Имя логгера
- `component` - Тип компонента

**Возвращает:** Настроенный структурированный логгер

**Пример:**
```python
logger = get_structured_logger(\"webhook_handler\", ComponentType.WEBHOOK)
```

#### `log_operation_start(logger, operation: str, trace_id: str, metadata: Dict[str, Any] = None)`

Логирует начало операции.

**Параметры:**
- `logger` - Экземпляр логгера
- `operation` - Название операции
- `trace_id` - ID трассировки
- `metadata` - Дополнительные данные

**Пример:**
```python
log_operation_start(logger, \"message_processing\", \"abc123\", {\"user_id\": \"12345\"})
```

#### `log_operation_success(logger, operation: str, trace_id: str, duration_ms: float, metadata: Dict[str, Any] = None)`

Логирует успешное завершение операции.

**Параметры:**
- `logger` - Экземпляр логгера
- `operation` - Название операции
- `trace_id` - ID трассировки
- `duration_ms` - Длительность в миллисекундах
- `metadata` - Дополнительные данные

**Пример:**
```python
log_operation_success(logger, \"message_processing\", \"abc123\", 125.5, {\"result\": \"success\"})
```

#### `log_operation_error(logger, operation: str, trace_id: str, error: Exception, metadata: Dict[str, Any] = None)`

Логирует ошибку операции.

**Параметры:**
- `logger` - Экземпляр логгера
- `operation` - Название операции
- `trace_id` - ID трассировки
- `error` - Объект исключения
- `metadata` - Дополнительные данные

**Пример:**
```python
try:
    process_message()
except Exception as e:
    log_operation_error(logger, \"message_processing\", \"abc123\", e, {\"user_id\": \"12345\"})
```

## Модуль `request_tracer.py`

### TraceStatus

Статусы трассировки запроса.

```python
class TraceStatus(str, Enum)
```

#### Значения:
- `STARTED` - Трассировка начата
- `IN_PROGRESS` - Трассировка в процессе
- `COMPLETED` - Трассировка успешно завершена
- `FAILED` - Трассировка завершена с ошибкой
- `TIMEOUT` - Трассировка прервана по таймауту

### ComponentStep

Этапы обработки в компонентах.

```python
class ComponentStep(str, Enum)
```

#### Значения:
- `WEBHOOK_RECEIVED` - Получен webhook запрос
- `MESSAGE_PARSED` - Сообщение распознано и разобрано
- `AGENT_ROUTING` - Выбор подходящего агента
- `AGENT_PROCESSING` - Обработка сообщения агентом
- `TOOL_EXECUTION` - Выполнение инструмента/команды
- `RESPONSE_GENERATION` - Генерация ответа
- `RESPONSE_SENT` - Ответ отправлен пользователю
- `ERROR_HANDLING` - Обработка ошибки

### TraceEvent

Событие в трассировке запроса.

```python
@dataclass
class TraceEvent:
    timestamp: datetime              # Время события
    component: ComponentType         # Компонент системы
    step: ComponentStep             # Этап обработки
    details: Dict[str, Any]         # Детали события
    duration_ms: Optional[float]    # Длительность операции (мс)
    success: bool                   # Успешность операции
    error: Optional[str]            # Описание ошибки
```

### RequestTrace

Полная трассировка запроса.

```python
@dataclass
class RequestTrace:
    trace_id: str                   # Уникальный идентификатор
    user_id: str                    # ID пользователя
    session_id: Optional[str]       # ID сессии
    start_time: datetime            # Время начала
    end_time: Optional[datetime]    # Время окончания
    status: TraceStatus             # Текущий статус
    events: List[TraceEvent]        # Список событий
    metadata: Dict[str, Any]        # Метаданные запроса
```

#### Свойства:

##### `duration_ms: Optional[float]`
Общая длительность запроса в миллисекундах.

**Возвращает:** `float` если трассировка завершена, иначе `None`

##### `component_durations: Dict[str, float]`
Суммарная длительность операций по компонентам.

**Возвращает:** Словарь с длительностями по компонентам

**Пример:**
```python
{
    \"webhook\": 5.2,
    \"agent\": 120.8,
    \"mcp\": 45.3
}
```

### RequestTracer

Основной класс системы трассировки.

```python
class RequestTracer
```

#### Конструктор

```python
def __init__(self, max_traces: int = 1000, trace_ttl_hours: int = 24)
```

**Параметры:**
- `max_traces` - Максимальное количество хранимых трассировок
- `trace_ttl_hours` - Время жизни трассировки в часах

#### Методы

##### `create_trace(user_id: str, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str`

Создает новую трассировку запроса.

**Параметры:**
- `user_id` - Идентификатор пользователя
- `session_id` - Идентификатор сессии (опционально)
- `metadata` - Дополнительные метаданные (опционально)

**Возвращает:** Уникальный ID трассировки

**Пример:**
```python
trace_id = request_tracer.create_trace(
    user_id=\"12345\",
    session_id=\"session_67890\",
    metadata={\"source\": \"telegram\", \"chat_type\": \"private\"}
)
```

##### `add_event(trace_id: str, component: ComponentType, step: ComponentStep, details: Optional[Dict[str, Any]] = None, duration_ms: Optional[float] = None, success: bool = True, error: Optional[str] = None)`

Добавляет событие в трассировку.

**Параметры:**
- `trace_id` - ID трассировки
- `component` - Компонент системы
- `step` - Этап обработки
- `details` - Детали события (опционально)
- `duration_ms` - Длительность операции в мс (опционально)
- `success` - Успешность операции (по умолчанию True)
- `error` - Описание ошибки (опционально)

**Пример:**
```python
request_tracer.add_event(
    trace_id=\"abc123\",
    component=ComponentType.AGENT,
    step=ComponentStep.AGENT_PROCESSING,
    details={\"agent_name\": \"IntelligentAgent\", \"user_role\": \"admin\"},
    duration_ms=145.7,
    success=True
)
```

##### `complete_trace(trace_id: str, status: TraceStatus = TraceStatus.COMPLETED, final_metadata: Optional[Dict[str, Any]] = None)`

Завершает трассировку запроса.

**Параметры:**
- `trace_id` - ID трассировки
- `status` - Финальный статус (по умолчанию COMPLETED)
- `final_metadata` - Финальные метаданные (опционально)

**Пример:**
```python
request_tracer.complete_trace(
    trace_id=\"abc123\",
    status=TraceStatus.COMPLETED,
    final_metadata={\"response_length\": 150, \"tokens_used\": 45}
)
```

##### `get_trace(trace_id: str) -> Optional[RequestTrace]`

Получает трассировку по ID.

**Параметры:**
- `trace_id` - ID трассировки

**Возвращает:** Объект RequestTrace или None если не найдена

**Пример:**
```python
trace = request_tracer.get_trace(\"abc123\")
if trace:
    print(f\"Статус: {trace.status}, Длительность: {trace.duration_ms}ms\")
```

##### `get_active_traces() -> List[RequestTrace]`

Получает все активные трассировки.

**Возвращает:** Список активных трассировок

**Пример:**
```python
active = request_tracer.get_active_traces()
print(f\"Активных запросов: {len(active)}\")
```

##### `get_user_traces(user_id: str, limit: int = 10) -> List[RequestTrace]`

Получает трассировки конкретного пользователя.

**Параметры:**
- `user_id` - ID пользователя
- `limit` - Максимальное количество трассировок

**Возвращает:** Список трассировок пользователя (отсортированы по времени, новые первыми)

**Пример:**
```python
user_traces = request_tracer.get_user_traces(\"12345\", limit=5)
for trace in user_traces:
    print(f\"Трассировка {trace.trace_id}: {trace.status}\")
```

##### `get_performance_metrics() -> Dict[str, Any]`

Получает метрики производительности системы.

**Возвращает:** Словарь с метриками

**Структура ответа:**
```python
{
    \"total_requests\": int,          # Общее количество запросов
    \"successful_requests\": int,     # Количество успешных запросов
    \"failed_requests\": int,         # Количество неуспешных запросов
    \"success_rate\": float,          # Коэффициент успеха (0.0-1.0)
    \"active_traces\": int,           # Количество активных трассировок
    \"completed_traces\": int,        # Количество завершенных трассировок
    \"avg_duration_ms\": float,       # Средняя длительность запроса (мс)
    \"component_performance\": {      # Производительность по компонентам
        \"component_name\": {
            \"avg_ms\": float,         # Среднее время выполнения
            \"total_ms\": float,       # Общее время выполнения
            \"count\": int             # Количество операций
        }
    }
}
```

**Пример:**
```python
metrics = request_tracer.get_performance_metrics()
print(f\"Процент успеха: {metrics['success_rate']:.1%}\")
print(f\"Средняя задержка: {metrics['avg_duration_ms']:.1f}ms\")
```

##### `trace_operation(trace_id: str, component: ComponentType, step: ComponentStep, details: Optional[Dict[str, Any]] = None)`

Контекстный менеджер для автоматической трассировки операций.

**Параметры:**
- `trace_id` - ID трассировки
- `component` - Компонент системы
- `step` - Этап обработки
- `details` - Детали операции (опционально)

**Возвращает:** Асинхронный контекстный менеджер

**Пример:**
```python
async with request_tracer.trace_operation(
    trace_id=\"abc123\",
    component=ComponentType.MCP,
    step=ComponentStep.TOOL_EXECUTION,
    details={\"tool\": \"mcp_apps\", \"provider\": \"digitalocean\"}
):
    result = await execute_mcp_command()
    # Время автоматически измеряется
    # Успех/ошибка автоматически логируется
```

## Глобальные экземпляры

### `request_tracer`

Глобальный экземпляр класса RequestTracer.

```python
from bot.core.request_tracer import request_tracer
```

Используется по всей системе для единообразной трассировки запросов.

## Интеграция с компонентами

### Webhook обработчики

```python
# В bot/webhook/handlers.py
from bot.core.request_tracer import request_tracer, ComponentType, ComponentStep

class TelegramWebhookHandler:
    async def handle_message(self, update: Update):
        # Создание трассировки
        trace_id = request_tracer.create_trace(
            user_id=str(update.message.from_user.id),
            session_id=str(update.message.chat.id),
            metadata={\"message_type\": \"telegram\"}
        )
        
        # Добавление trace_id к сообщению
        message.trace_id = trace_id
        
        # Логирование события
        request_tracer.add_event(
            trace_id, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED,
            details={\"update_id\": update.update_id}
        )
```

### Система агентов

```python
# В bot/core/base_agent.py
class ChainedAgent:
    async def process_message(self, message: Message) -> Response:
        trace_id = getattr(message, 'trace_id', None)
        
        if trace_id:
            request_tracer.add_event(
                trace_id, ComponentType.AGENT, ComponentStep.AGENT_ROUTING,
                details={\"available_agents\": len(self.agents)}
            )
        
        # Трассировка обработки агентом
        async with request_tracer.trace_operation(
            trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
            details={\"agent\": agent.get_name()}
        ):
            response = await agent.process_message(message)
```

### MCP сервисы

```python
# В bot/services/unified_mcp_service.py
class UnifiedMCPService:
    async def execute_command(self, command: MCPCommand, trace_id: str = None):
        if trace_id:
            async with request_tracer.trace_operation(
                trace_id, ComponentType.MCP, ComponentStep.TOOL_EXECUTION,
                details={
                    \"provider\": command.provider.value,
                    \"action\": command.action
                }
            ):
                return await self._execute_via_sdk(command)
```

## Обработка ошибок

### Автоматическая обработка в контекстном менеджере

```python
async with request_tracer.trace_operation(trace_id, component, step):
    # Любое исключение автоматически:
    # 1. Логируется как событие с success=False
    # 2. Включает описание ошибки
    # 3. Измеряет время до ошибки
    # 4. Прокидывает исключение дальше
    raise ValueError(\"Тестовая ошибка\")
```

### Ручная обработка ошибок

```python
try:
    result = await some_operation()
    request_tracer.add_event(
        trace_id, component, step,
        details={\"result\": \"success\"},
        duration_ms=duration,
        success=True
    )
except Exception as e:
    request_tracer.add_event(
        trace_id, component, ComponentStep.ERROR_HANDLING,
        details={\"operation\": \"some_operation\"},
        success=False,
        error=str(e)
    )
    raise
```

## Best Practices

### 1. Создание трассировок
- Создавайте трассировку как можно раньше в цепочке обработки
- Включайте максимум контекстной информации в metadata
- Используйте осмысленные идентификаторы пользователей и сессий

### 2. Добавление событий
- Выбирайте подходящие ComponentType и ComponentStep
- Включайте релевантные детали в поле details
- Измеряйте время критических операций
- Корректно отмечайте успех/неуспех

### 3. Использование контекстного менеджера
- Предпочитайте контекстный менеджер для автоматического измерения времени
- Используйте для операций, которые могут завершиться исключением
- Добавляйте детальную информацию об операции

### 4. Завершение трассировок
- Всегда завершайте трассировки вызовом complete_trace()
- Используйте правильные статусы завершения
- Добавляйте итоговые метаданные с результатами

### 5. Мониторинг производительности
- Регулярно проверяйте метрики через get_performance_metrics()
- Мониторьте коэффициент успеха и среднее время ответа
- Анализируйте производительность по компонентам

---

**Версия API**: 1.0  
**Дата обновления**: 26 июля 2025  
**Совместимость**: Python 3.8+