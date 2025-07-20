# 🧪 MCP Tests

Тесты для Model Context Protocol (MCP) компонентов Artem Integrator.

## 📋 Структура тестов

```
tests/mcp/
├── test_mcp_manager.py      # Тесты MCP Manager
├── test_mcp_agent.py        # Тесты MCP Agent
├── test_mcp_service.py      # Тесты сервисного слоя
├── test_mcp_formatter.py    # Тесты форматтера
└── __init__.py
```

## 🚀 Запуск тестов

### Все тесты
```bash
python tests/run_mcp_tests.py
```

### С подробным выводом
```bash
python tests/run_mcp_tests.py -v
```

### Конкретный модуль
```bash
pytest tests/mcp/test_mcp_manager.py -v
```

### Конкретный тест
```bash
pytest tests/mcp/test_mcp_agent.py::TestMCPAgent::test_can_handle_mcp_admin -v
```

### С покрытием кода
```bash
python tests/run_mcp_tests.py --cov
```

## 📊 Покрытие тестами

### MCP Manager (`test_mcp_manager.py`)
- ✅ Инициализация подключений
- ✅ Выполнение функций
- ✅ Кэширование результатов
- ✅ Rate limiting
- ✅ Обработка ошибок
- ✅ Метрики и статистика
- ✅ Health check серверов

### MCP Agent (`test_mcp_agent.py`)
- ✅ Инициализация агента
- ✅ Проверка прав доступа
- ✅ Генерация функций для OpenAI
- ✅ Обработка MCP запросов
- ✅ Маршрутизация команд
- ✅ Fallback на обычный AI
- ✅ Интеграционные тесты

### MCP Service (`test_mcp_service.py`)
- ✅ SupabaseService
  - Список проектов
  - SQL запросы с валидацией
  - Создание проектов
  - Список таблиц
- ✅ DigitalOceanService
  - Список приложений
  - Получение логов
  - Создание деплоев
  - Статус деплоев
- ✅ Context7Service
  - Поиск документации
  - Получение документации
  - Примеры кода
- ✅ MCPServiceFactory

### MCP Formatter (`test_mcp_formatter.py`)
- ✅ Форматирование SQL результатов
- ✅ Форматирование списков (проекты, приложения)
- ✅ Форматирование статусов деплоев
- ✅ Форматирование логов
- ✅ Форматирование документации
- ✅ Обработка ошибок
- ✅ Метрики и статистика

## 🛠️ Установка зависимостей для тестов

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

## 📝 Написание новых тестов

### Структура теста
```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestNewComponent:
    @pytest.fixture
    def mock_dependency(self):
        """Фикстура с моком зависимости"""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_async_method(self, mock_dependency):
        """Тест асинхронного метода"""
        # Arrange
        component = NewComponent(mock_dependency)
        
        # Act
        result = await component.async_method()
        
        # Assert
        assert result.success is True
```

### Моки для MCP
```python
# Мок MCP Manager
mock_manager = Mock(spec=MCPManager)
mock_manager.execute_function = AsyncMock(return_value=MCPFunctionResult(...))

# Мок MCP конфигурации
mock_config = {
    "servers": {
        "test_server": {
            "enabled": True,
            "functions": {...}
        }
    }
}
```

## 🐛 Отладка тестов

### Запуск с отладкой
```bash
pytest tests/mcp/test_mcp_agent.py -v -s --pdb
```

### Только неудачные тесты
```bash
pytest tests/mcp --lf
```

### Параллельный запуск
```bash
pytest tests/mcp -n auto
```

## ✅ CI/CD интеграция

Добавьте в `.github/workflows/test.yml`:

```yaml
- name: Run MCP tests
  run: |
    python tests/run_mcp_tests.py --cov
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./htmlcov/coverage.xml
```

## 📈 Метрики качества

- **Покрытие кода**: >80%
- **Время выполнения**: <30 секунд
- **Количество тестов**: 50+
- **Типы тестов**: Unit, Integration, Edge cases

---

🤖 Тесты помогают поддерживать высокое качество MCP системы!