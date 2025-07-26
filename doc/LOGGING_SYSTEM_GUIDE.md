# Система логирования Artyom Integrator

## Обзор

Система логирования Artyom Integrator представляет собой многоуровневую архитектуру для комплексного отслеживания работы бота. Система включает в себя структурированное логирование, трассировку запросов и детальную диагностику всех компонентов.

## Архитектура системы логирования

```
┌─────────────────────────────────────────────────────────────┐
│                    СИСТЕМА ЛОГИРОВАНИЯ                      │
├─────────────────────────────────────────────────────────────┤
│  1. Структурированное логирование (logging_utils.py)       │
│  2. Система трассировки запросов (request_tracer.py)       │
│  3. Интеграция с компонентами бота                         │
│  4. Централизованный сбор метрик                           │
└─────────────────────────────────────────────────────────────┘
```

## 1. Структурированное логирование

### Местоположение
- **Файл**: `bot/core/logging_utils.py`
- **Статус**: ✅ Реализовано

### Основные компоненты

#### ComponentType (Типы компонентов)
```python
class ComponentType(str, Enum):
    WEBHOOK = \"webhook\"           # Webhook обработчики
    AGENT = \"agent\"               # Система агентов
    MCP = \"mcp\"                   # MCP сервисы
    SERVICE = \"service\"           # Бизнес-сервисы
    ADAPTER = \"adapter\"           # Адаптеры агентов
    MEMORY = \"memory\"             # Система памяти
    AUTH = \"auth\"                 # Аутентификация
    ERROR = \"error\"               # Обработка ошибок
```

#### TraceContext (Контекст трассировки)
```python
@dataclass
class TraceContext:
    trace_id: str                  # Уникальный ID запроса
    user_id: Optional[str]         # ID пользователя
    session_id: Optional[str]      # ID сессии
    operation: str                 # Название операции
    metadata: Dict[str, Any]       # Метаданные операции
```

#### Функции логирования
- `get_structured_logger()` - Создание структурированного логгера
- `log_operation_start()` - Логирование начала операции
- `log_operation_success()` - Логирование успешного завершения
- `log_operation_error()` - Логирование ошибки

### Пример использования
```python
from bot.core.logging_utils import (
    get_structured_logger, ComponentType, 
    log_operation_start, log_operation_success
)

logger = get_structured_logger(\"webhook_handler\", ComponentType.WEBHOOK)

# Логирование с контекстом
logger.info(
    \"📥 Получено сообщение от пользователя\",
    trace_id=\"abc123\",
    operation=\"message_received\",
    metadata={
        \"user_id\": \"12345\",
        \"message_type\": \"text\",
        \"chat_id\": 67890
    }
)
```

## 2. Система трассировки запросов

### Местоположение
- **Файл**: `bot/core/request_tracer.py`
- **Статус**: ✅ Реализовано

### Основные компоненты

#### RequestTracer (Основной класс)
```python
class RequestTracer:
    def create_trace(user_id, session_id, metadata) -> str
    def add_event(trace_id, component, step, details, duration_ms, success, error)
    def complete_trace(trace_id, status, final_metadata)
    def get_trace(trace_id) -> RequestTrace
    def get_performance_metrics() -> Dict[str, Any]
```

#### ComponentStep (Этапы обработки)
```python
class ComponentStep(str, Enum):
    WEBHOOK_RECEIVED = \"webhook_received\"        # Получен webhook
    MESSAGE_PARSED = \"message_parsed\"            # Сообщение разобрано
    AGENT_ROUTING = \"agent_routing\"              # Маршрутизация к агенту
    AGENT_PROCESSING = \"agent_processing\"        # Обработка агентом
    TOOL_EXECUTION = \"tool_execution\"            # Выполнение инструмента
    RESPONSE_GENERATION = \"response_generation\"  # Генерация ответа
    RESPONSE_SENT = \"response_sent\"              # Ответ отправлен
    ERROR_HANDLING = \"error_handling\"            # Обработка ошибки
```

#### RequestTrace (Структура трассировки)
```python
@dataclass
class RequestTrace:
    trace_id: str                      # Уникальный идентификатор
    user_id: str                       # ID пользователя
    session_id: Optional[str]          # ID сессии
    start_time: datetime               # Время начала
    end_time: Optional[datetime]       # Время окончания
    status: TraceStatus                # Статус (started/completed/failed)
    events: List[TraceEvent]           # Список событий
    metadata: Dict[str, Any]           # Метаданные запроса
```

### Пример использования трассировки
```python
from bot.core.request_tracer import request_tracer, ComponentType, ComponentStep

# Создание трассировки
trace_id = request_tracer.create_trace(
    user_id=\"12345\",
    session_id=\"session_67890\",
    metadata={\"source\": \"telegram\", \"message_type\": \"text\"}
)

# Добавление событий
request_tracer.add_event(
    trace_id, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED,
    details={\"message\": \"Привет, бот!\"},
    duration_ms=2.5,
    success=True
)

# Использование контекстного менеджера
async with request_tracer.trace_operation(
    trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
    details={\"agent\": \"IntelligentAgent\"}
):
    response = await process_with_agent(message)

# Завершение трассировки
request_tracer.complete_trace(
    trace_id, TraceStatus.COMPLETED,
    final_metadata={\"response_length\": 150}
)
```

## 3. Интеграция с компонентами

### Webhook обработчики (`bot/webhook/handlers.py`)
- ✅ **Полная интеграция трассировки**
- Создание trace_id для каждого входящего сообщения
- Отслеживание всех этапов обработки
- Интеграция с Business API трассировкой

```python
# Создание трассировки для webhook
trace_id = request_tracer.create_trace(
    user_id=str(user_id),
    session_id=str(chat_id),
    metadata={
        \"message_type\": \"telegram\",
        \"chat_type\": update.message.chat.type,
        \"is_business_message\": is_business_message
    }
)

# Добавление событий обработки
request_tracer.add_event(
    trace_id, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED,
    details={\"update_id\": update.update_id}
)
```

### Система агентов (`bot/core/base_agent.py`)
- ✅ **ChainedAgent с полной трассировкой**
- Отслеживание процесса выбора агента
- Логирование can_handle проверок
- Трассировка обработки сообщений

```python
# Трассировка маршрутизации агентов
request_tracer.add_event(
    trace_id, ComponentType.AGENT, ComponentStep.AGENT_ROUTING,
    details={\"available_agents\": len(self.agents)}
)

# Трассировка обработки конкретным агентом
async with request_tracer.trace_operation(
    trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
    details={\"agent\": agent_name, \"user_id\": message.user.id}
):
    response = await agent.process_message(message)
```

### Адаптеры агентов (`bot/core/agent_adapters.py`)
- ✅ **IntelligentAgentAdapter и DefaultAgentAdapter**
- Структурированное логирование can_handle логики
- Трассировка process_message операций
- Детальное логирование принятия решений

### MCP сервисы (`bot/services/unified_mcp_service.py`)
- ✅ **Унифицированный MCP сервис с трассировкой**
- Отслеживание выполнения MCP команд
- Трассировка SDK и эмуляции команд
- Логирование ошибок и успешных операций

```python
# Трассировка MCP команд
async with request_tracer.trace_operation(
    trace_id, ComponentType.MCP, ComponentStep.TOOL_EXECUTION,
    details={
        \"provider\": command.provider.value,
        \"action\": command.action,
        \"sdk_available\": self._claude_sdk_available
    }
):
    result = await self._execute_via_sdk(command, trace_id)
```

## 4. Метрики производительности

### Автоматический сбор метрик
```python
metrics = request_tracer.get_performance_metrics()

# Доступные метрики:
{
    \"total_requests\": 150,              # Общее количество запросов
    \"successful_requests\": 140,         # Успешные запросы
    \"failed_requests\": 10,              # Неуспешные запросы
    \"success_rate\": 0.933,              # Процент успеха
    \"active_traces\": 5,                 # Активные трассировки
    \"completed_traces\": 145,            # Завершенные трассировки
    \"avg_duration_ms\": 125.5,           # Средняя длительность
    \"component_performance\": {          # Производительность по компонентам
        \"webhook\": {
            \"avg_ms\": 3.2,
            \"total_ms\": 480.0,
            \"count\": 150
        },
        \"agent\": {
            \"avg_ms\": 85.4,
            \"total_ms\": 12810.0,
            \"count\": 150
        }
    }
}
```

## 5. Практическое использование

### Отладка проблем
1. **Найти трассировку пользователя**:
```python
user_traces = request_tracer.get_user_traces(\"12345\", limit=10)
for trace in user_traces:
    print(f\"Трассировка {trace.trace_id}: {trace.status} за {trace.duration_ms}ms\")
```

2. **Анализ ошибок**:
```python
trace = request_tracer.get_trace(\"abc123\")
for event in trace.events:
    if not event.success:
        print(f\"Ошибка в {event.component.value}: {event.error}\")
```

3. **Анализ производительности**:
```python
metrics = request_tracer.get_performance_metrics()
slowest_component = max(
    metrics[\"component_performance\"].items(),
    key=lambda x: x[1][\"avg_ms\"]
)
print(f\"Самый медленный компонент: {slowest_component[0]}\")
```

### Мониторинг в реальном времени
```python
# Активные трассировки
active = request_tracer.get_active_traces()
print(f\"Активных запросов: {len(active)}\")

# Трассировки с ошибками
for trace in active:
    error_events = [e for e in trace.events if not e.success]
    if error_events:
        print(f\"Трассировка {trace.trace_id} имеет {len(error_events)} ошибок\")
```

## 6. Конфигурация и настройка

### Параметры RequestTracer
```python
request_tracer = RequestTracer(
    max_traces=1000,        # Максимум хранимых трассировок
    trace_ttl_hours=24      # Время жизни трассировки в часах
)
```

### Включение/выключение структурированного логирования
Автоматическое определение доступности через try/except:
```python
try:
    from .logging_utils import get_structured_logger
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False
```

### Fallback логирование
При недоступности структурированного логирования система автоматически переключается на стандартное:
```python
if self.structured_logger:
    self.structured_logger.info(\"Структурированное сообщение\", trace_id=trace_id)
else:
    self.fallback_logger.info(f\"[TRACE:{trace_id}] Обычное сообщение\")
```

## 7. Тестирование системы

### Тестовый скрипт
- **Файл**: `test_tracing_isolated.py`
- **Статус**: ✅ Все тесты пройдены

Запуск тестов:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ12345678 python test_tracing_isolated.py
```

### Тестовые сценарии
1. ✅ Инициализация RequestTracer
2. ✅ Создание и управление трассировками
3. ✅ Добавление и управление событиями
4. ✅ Завершение трассировки
5. ✅ Контекстный менеджер для операций
6. ✅ Получение трассировок пользователя
7. ✅ Детальные метрики производительности
8. ✅ Функциональность очистки трассировок

## 8. Лучшие практики

### Создание трассировок
- Всегда создавайте трассировку в начале обработки запроса
- Включайте user_id и session_id для связывания запросов
- Добавляйте релевантные метаданные для контекста

### Добавление событий
- Используйте подходящие ComponentType и ComponentStep
- Включайте детали операции в поле details
- Измеряйте время выполнения операций
- Корректно отмечайте успех/неуспех операций

### Использование контекстного менеджера
- Предпочитайте контекстный менеджер для автоматического измерения времени
- Позволяйте исключениям проходить через менеджер для корректной обработки
- Используйте детальные описания операций

### Завершение трассировок
- Всегда завершайте трассировки вызовом complete_trace()
- Используйте правильные статусы (COMPLETED/FAILED/TIMEOUT)
- Добавляйте финальные метаданные с результатами операции

## 9. Мониторинг и диагностика

### Ключевые индикаторы
- **Коэффициент успеха**: > 95% для стабильной работы
- **Средняя задержка**: < 200ms для веб-интерфейса
- **Активные трассировки**: мониторинг на предмет утечек памяти
- **Ошибки по компонентам**: выявление проблемных мест

### Автоматическая очистка
- Система автоматически очищает старые трассировки
- Настраиваемые лимиты по количеству и времени жизни
- Сохранение самых новых трассировок при превышении лимитов

### Уведомления о проблемах
- Мониторинг коэффициента ошибок
- Алерты при превышении времени выполнения
- Уведомления о недоступности компонентов

## 10. Заключение

Комплексная система логирования Artyom Integrator обеспечивает:

- ✅ **Полную трассируемость** запросов от webhook до ответа
- ✅ **Структурированное логирование** с контекстом и метаданными
- ✅ **Автоматические метрики** производительности и надежности
- ✅ **Гибкую конфигурацию** и fallback механизмы
- ✅ **Простоту отладки** и диагностики проблем
- ✅ **Масштабируемость** и производительность

Система готова к использованию в production окружении и обеспечивает все необходимые возможности для мониторинга и отладки работы бота.

---

**Дата создания**: 26 июля 2025  
**Статус**: Реализовано и протестировано  
**Автор**: Claude Code Assistant