# 🛠️ Development Guide

## Обзор

Это руководство поможет вам начать разработку Artyom Integrator. Здесь описаны инструменты, процессы и best practices для эффективной работы с кодовой базой.

## Настройка окружения

### 1. Требования

- Python 3.11+
- Git
- PostgreSQL 14+ (для Zep)
- Redis (опционально)
- Docker (опционально)

### 2. Клонирование репозитория

```bash
git clone https://github.com/Timosan61/artem.integrator.git
cd artem.integrator
```

### 3. Виртуальное окружение

```bash
# Создание venv
python3.11 -m venv venv

# Активация
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Обновление pip
pip install --upgrade pip
```

### 4. Установка зависимостей

```bash
# Основные зависимости
pip install -r requirements.txt

# Dev зависимости
pip install -r requirements-dev.txt
```

### 5. Настройка IDE

#### VS Code

Рекомендуемые расширения:
- Python
- Pylance
- Black Formatter
- GitLens
- Docker

`.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "100"],
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. Выберите созданный venv
3. Enable Django support (если нужно)
4. Configure code style → Black

## Структура проекта

```
artem.integrator/
├── bot/                    # Основной код
│   ├── core/              # Ядро системы
│   ├── services/          # Бизнес-логика
│   ├── webhook/           # HTTP слой
│   └── mcp/               # MCP интеграция
├── tests/                 # Тесты
│   ├── unit/             # Unit тесты
│   ├── integration/      # Integration тесты
│   └── fixtures/         # Тестовые данные
├── docs/                  # Документация
├── scripts/              # Утилиты
└── admin/                # Веб-интерфейсы
```

## Workflow разработки

### 1. Создание feature branch

```bash
git checkout -b feature/my-awesome-feature
```

### 2. Разработка

#### Добавление нового сервиса

1. Создайте файл в `bot/services/`:
```python
# bot/services/my_service.py
from typing import Optional
from ..core.interfaces import BaseService

class MyService(BaseService):
    """Описание сервиса"""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
    
    async def process(self, data: Any) -> Any:
        """Основная логика"""
        # Реализация
        pass
```

2. Добавьте конфигурацию в `bot/core/config.py`:
```python
@dataclass
class MyServiceConfig:
    enabled: bool = False
    api_key: Optional[str] = None
    # другие параметры
```

3. Зарегистрируйте в `bot/services/__init__.py`

#### Добавление нового endpoint

1. Создайте router в `bot/webhook/routers/`:
```python
# bot/webhook/routers/my_router.py
from fastapi import APIRouter, Depends
from typing import Dict, Any

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint() -> Dict[str, Any]:
    """Описание endpoint"""
    return {"status": "ok"}
```

2. Добавьте в `bot/webhook/app.py`:
```python
from .routers import my_router

app.include_router(
    my_router.router,
    prefix="/api",
    tags=["my-feature"]
)
```

### 3. Написание тестов

#### Unit тест

```python
# tests/unit/test_my_service.py
import pytest
from bot.services.my_service import MyService

class TestMyService:
    @pytest.fixture
    def service(self):
        return MyService()
    
    async def test_process(self, service):
        result = await service.process("test data")
        assert result is not None
```

#### Integration тест

```python
# tests/integration/test_my_endpoint.py
import pytest
from fastapi.testclient import TestClient
from bot.webhook.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_my_endpoint(client):
    response = client.get("/api/my-endpoint")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### 4. Локальное тестирование

```bash
# Запуск всех тестов
pytest

# Конкретный файл
pytest tests/unit/test_my_service.py

# С покрытием
pytest --cov=bot --cov-report=html

# Только быстрые тесты
pytest -m "not slow"
```

### 5. Линтинг и форматирование

```bash
# Black форматирование
black bot/ tests/

# Проверка типов
mypy bot/

# Линтинг
pylint bot/

# Все проверки
make lint  # если есть Makefile
```

## Debugging

### 1. Локальный запуск

```bash
# Development режим
DEBUG=true python webhook.py

# С specific портом
PORT=8001 python webhook.py
```

### 2. Использование debugger

#### VS Code
1. Создайте `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Webhook",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/webhook.py",
            "console": "integratedTerminal",
            "env": {
                "DEBUG": "true",
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

2. Установите breakpoints
3. F5 для запуска

#### PyCharm
1. Run → Edit Configurations
2. Add Python configuration
3. Script path: webhook.py
4. Environment variables: добавьте нужные

### 3. Логирование

```python
from bot.core.logging import get_logger

logger = get_logger(__name__)

# Разные уровни
logger.debug("Debug информация")
logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка", exc_info=True)

# С дополнительным контекстом
logger.info("User action", extra={
    "user_id": 123,
    "action": "send_message"
})
```

### 4. Профилирование

```python
from bot.core.monitoring import monitor_performance, Timer

# Декоратор
@monitor_performance
async def slow_function():
    # код
    pass

# Контекстный менеджер
async with Timer("operation_name") as timer:
    # код
    pass
print(f"Took {timer.elapsed:.2f} seconds")
```

## Работа с базой данных

### 1. Zep Memory

```python
from bot.services.memory_manager import MemoryManager

memory = MemoryManager()

# Сохранение
await memory.save_message(user_id, message)

# Получение контекста
context = await memory.get_context(user_id)
```

### 2. Миграции (если используете SQLAlchemy)

```bash
# Создание миграции
alembic revision --autogenerate -m "Add new table"

# Применение
alembic upgrade head

# Откат
alembic downgrade -1
```

## Интеграция с внешними сервисами

### 1. Добавление нового MCP сервера

```python
# bot/mcp/servers/my_server.py
from ..core.interfaces import MCPServer, MCPResult

class MyMCPServer(MCPServer):
    async def connect(self) -> bool:
        # Логика подключения
        return True
    
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPResult:
        # Выполнение функции
        return MCPResult(success=True, data={})
```

### 2. Работа с API

```python
import httpx
from bot.core.errors import APIError

async def call_external_api():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://api.example.com")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise APIError("external_service", e.response.status_code)
```

## Best Practices

### 1. Код

- **Type hints везде**: Используйте типы для всех функций
- **Docstrings**: Документируйте все публичные методы
- **DRY**: Don't Repeat Yourself
- **SOLID**: Следуйте принципам SOLID
- **Async first**: Предпочитайте асинхронный код

### 2. Безопасность

- Никогда не логируйте секреты
- Валидируйте все входные данные
- Используйте prepared statements для SQL
- Санитизируйте пользовательский ввод

### 3. Производительность

- Используйте кеширование где возможно
- Избегайте N+1 запросов
- Профилируйте медленные операции
- Используйте connection pooling

### 4. Тестирование

- Пишите тесты до кода (TDD)
- Покрытие > 80%
- Мокайте внешние сервисы
- Тестируйте edge cases

## Полезные команды

### Make команды (если есть Makefile)

```bash
make install    # Установка зависимостей
make test       # Запуск тестов
make lint       # Проверка кода
make format     # Форматирование
make run        # Запуск приложения
make docker     # Сборка Docker образа
```

### Скрипты

```bash
# Проверка окружения
python scripts/check_env.py

# Генерация конфигурации
python scripts/generate_config.py

# Тестовые данные
python scripts/seed_data.py
```

## Troubleshooting

### Import errors

```bash
# Проверьте PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Или используйте -m
python -m bot.webhook
```

### Async errors

```python
# Правильно
async def main():
    result = await async_function()

# Неправильно
def main():
    result = async_function()  # Забыли await
```

### Type errors

```bash
# Проверка типов
mypy bot/ --ignore-missing-imports

# Генерация stubs
stubgen -p bot
```

## Ресурсы

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [OpenAI API](https://platform.openai.com/docs/)
- [MCP Protocol](https://github.com/mcp/protocol)

## Contributing

1. Fork репозитория
2. Создайте feature branch
3. Напишите код и тесты
4. Убедитесь что тесты проходят
5. Создайте Pull Request

См. [CONTRIBUTING.md](../../CONTRIBUTING.md) для деталей.