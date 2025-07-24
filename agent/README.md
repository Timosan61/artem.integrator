# Intelligent Agent для Artem Integrator

## Описание

Intelligent Agent - это интеллектуальная система обработки запросов пользователей с автоматической классификацией намерений, выбором подходящих инструментов и обучением на предпочтениях пользователей.

## Архитектура

```
agent/
├── core/                       # Основные компоненты
│   ├── intelligent_agent.py    # Главный класс агента
│   ├── intent_classifier.py    # Классификатор намерений
│   ├── tool_registry.py        # Реестр инструментов
│   ├── confirmation_manager.py # Менеджер подтверждений
│   ├── preference_manager.py   # Менеджер предпочтений
│   └── models.py              # Pydantic модели
│
├── tools/                      # Инструменты
│   ├── base.py                # Базовый класс инструментов
│   ├── mcp_tool.py            # MCP интеграция (DigitalOcean, Supabase)
│   ├── youtube_tool.py        # YouTube анализатор
│   └── echo_tool.py           # Тестовый инструмент
│
├── config/                     # Конфигурация
│   └── intent_patterns.yaml    # Паттерны классификации
│
└── tests/                      # Тесты
    └── ...                    # Тестовые файлы
```

## Основные возможности

### 1. Классификация намерений (Intent Classification)

Агент автоматически определяет тип запроса:
- **MCP_COMMAND** - команды управления инфраструктурой
- **YOUTUBE_ANALYSIS** - анализ YouTube видео
- **IMAGE_GENERATION** - генерация изображений
- **GENERAL_QUESTION** - общие вопросы
- **GENERAL_CHAT** - обычный чат

### 2. Инструменты (Tools)

#### MCPTool
- Интеграция с Claude Code SDK
- Управление DigitalOcean приложениями
- Работа с Supabase базами данных
- Поиск документации через Context7

#### YouTubeAnalyzerTool
- Извлечение метаданных видео
- Получение субтитров
- Анализ контента
- Работа через YouTube Data API v3

### 3. Подтверждения (Confirmations)

Для критических операций (удаление, изменение) агент запрашивает подтверждение:
```
Вы уверены что хотите удалить приложение test-app?
✅ Да / ❌ Нет
```

### 4. Обучение на предпочтениях (Preference Learning)

Агент запоминает выбор пользователя и после 3+ использований формирует предпочтения:
- Автоматический выбор предпочитаемого инструмента
- Учет успешности использования
- Временной фактор (TTL 30 дней)

## Использование

### Инициализация

```python
from agent.core.intelligent_agent import IntelligentAgent

# Создание агента
agent = IntelligentAgent(
    api_key="sk-...",  # OpenAI API key
    model="gpt-4o"      # Модель GPT
)
```

### Обработка сообщений

```python
# Простое сообщение
response = await agent.process_message(
    message="покажи все приложения",
    user_id="123"
)

print(response.message)  # Список приложений
print(response.intent)   # Intent.MCP_COMMAND
print(response.tool_used) # ToolType.MCP
```

### Интеграция с Telegram

```python
from bot.services.intelligent_agent_service import intelligent_agent_service

# В webhook handler
if user.role == UserRole.ADMIN:
    response = await intelligent_agent_service.process_message(message)
```

## Конфигурация

### Переменные окружения

```bash
# Обязательные
OPENAI_API_KEY=sk-...        # OpenAI API для GPT-4

# Опциональные
YOUTUBE_API_KEY=AIza...      # YouTube Data API
```

### Паттерны классификации

Файл `config/intent_patterns.yaml`:
```yaml
mcp_command:
  keywords:
    - "приложения"
    - "apps"
    - "базы данных"
    - "database"
  patterns:
    - "покажи.*приложения"
    - "list.*apps"
```

## Тестирование

```bash
# Все тесты
pytest tests/

# Конкретный этап
pytest tests/test_telegram_integration.py -v

# С покрытием
pytest --cov=agent tests/
```

### Структура тестов

1. **test_basic_agent.py** - базовая функциональность
2. **test_tools.py** - система инструментов
3. **test_intent_classifier.py** - классификация намерений
4. **test_confirmation_flow.py** - подтверждения
5. **test_real_tools.py** - реальные инструменты
6. **test_memory_learning.py** - обучение на предпочтениях
7. **test_telegram_integration.py** - интеграция с Telegram

## Примеры использования

### 1. MCP команды

```
User: покажи все приложения
Bot: Вот список приложений:
- web-app (nyc3) - active
- api-service (sfo2) - active

_🔧 Использован: mcp_executor_
```

### 2. YouTube анализ

```
User: проанализируй https://youtube.com/watch?v=dQw4w9WgXcQ
Bot: 📹 Rick Astley - Never Gonna Give You Up
Длительность: 3:33
Просмотры: 1.4B
Субтитры доступны на 5 языках

_🔧 Использован: youtube_analyzer_
```

### 3. С подтверждением

```
User: удали приложение test-app
Bot: Вы уверены что хотите удалить приложение test-app?
✅ Да / ❌ Нет

User: да
Bot: ✅ Приложение успешно удалено
```

## Расширение функциональности

### Добавление нового инструмента

1. Создайте класс инструмента:
```python
from agent.tools.base import BaseTool, ToolMetadata

class MyTool(BaseTool):
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="Мой инструмент",
            requires_confirmation=False
        )
    
    async def execute(self, params):
        # Логика выполнения
        pass
```

2. Зарегистрируйте в `IntelligentAgentService`:
```python
my_tool = MyTool()
self.tool_registry.register_tool(my_tool)
```

### Добавление нового намерения

1. Добавьте в `Intent` enum:
```python
class Intent(str, Enum):
    MY_INTENT = "my_intent"
```

2. Добавьте паттерны в `intent_patterns.yaml`:
```yaml
my_intent:
  keywords:
    - "ключевое слово"
  patterns:
    - "паттерн.*запроса"
```

## Мониторинг и отладка

### Логирование

Все компоненты используют стандартный Python logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Метрики

- Статистика предпочтений: `preference_manager.get_user_statistics(user_id)`
- Активные подтверждения: `confirmation_manager.get_active_confirmations_count()`
- Статус агента: `/agent` команда в Telegram

## Безопасность

1. **Подтверждения** - все критические операции требуют подтверждения
2. **Ролевая модель** - Intelligent Agent доступен только администраторам
3. **Валидация** - все параметры проверяются через Pydantic модели
4. **Таймауты** - подтверждения истекают через 5 минут

## Производительность

- Классификация намерений: ~50ms
- Выполнение MCP команд: 2-10 секунд
- YouTube анализ: 3-15 секунд
- Память: ~100MB на 1000 пользователей

## Прогресс разработки

- ✅ **Этап 1**: Базовый агент с OpenAI Function Calling
- ✅ **Этап 2**: Система инструментов (Tool System) 
- ✅ **Этап 3**: Intent Classification и маршрутизация
- ✅ **Этап 4**: Confirmation Manager
- ✅ **Этап 5**: Реальные инструменты
- ✅ **Этап 6**: Memory и Learning
- ✅ **Этап 7**: Интеграция с Telegram
- 🔄 **Этап 8**: Финальное тестирование

## Документация этапов

- [Этап 1 - Завершен](STAGE1_COMPLETED.md)
- [Этап 2 - Завершен](STAGE2_COMPLETED.md)
- [Этап 3 - Завершен](STAGE3_COMPLETED.md)
- [Этап 4 - Завершен](STAGE4_COMPLETED.md)
- [Этап 5 - Завершен](STAGE5_COMPLETED.md)
- [Этап 6 - Завершен](STAGE6_COMPLETED.md)
- [Этап 7 - Завершен](STAGE7_COMPLETED.md)

## Roadmap

- [ ] Поддержка мультиязычности
- [ ] Интеграция с другими LLM (Claude, Llama)
- [ ] Batch обработка команд
- [ ] Веб-интерфейс для настройки
- [ ] Экспорт аналитики использования

## Лицензия

Proprietary - Artem Integrator