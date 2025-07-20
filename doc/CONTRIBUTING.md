# Contributing to Artyom Integrator

Спасибо за интерес к развитию Artyom Integrator! Мы приветствуем вклад от сообщества.

## Кодекс поведения

Участвуя в этом проекте, вы соглашаетесь поддерживать уважительную и инклюзивную атмосферу.

## Как внести вклад

### 1. Сообщения об ошибках

Перед созданием issue:
- Проверьте, нет ли уже похожей проблемы
- Используйте поиск по закрытым issues
- Убедитесь, что проблема воспроизводима

При создании issue включите:
- Версию Python и ОС
- Шаги для воспроизведения
- Ожидаемое поведение
- Фактическое поведение
- Логи (если есть)

### 2. Предложения улучшений

- Опишите проблему, которую решает улучшение
- Предложите API/интерфейс
- Приведите примеры использования
- Обсудите альтернативы

### 3. Pull Requests

#### Процесс

1. Fork репозитория
2. Создайте branch: `git checkout -b feature/amazing-feature`
3. Внесите изменения
4. Добавьте тесты
5. Commit: `git commit -m 'feat: Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Откройте Pull Request

#### Требования к коду

- **Style**: Следуйте PEP 8, используйте Black
- **Types**: Добавляйте type hints
- **Docs**: Документируйте публичные API
- **Tests**: Покрытие новых функций > 80%
- **Commits**: Используйте [Conventional Commits](https://www.conventionalcommits.org/)

#### Commit сообщения

Формат:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Типы:
- `feat`: Новая функциональность
- `fix`: Исправление бага
- `docs`: Изменения документации
- `style`: Форматирование кода
- `refactor`: Рефакторинг
- `test`: Добавление тестов
- `chore`: Обслуживание кода

Примеры:
```
feat(mcp): Add support for new MCP server

- Implemented connection logic
- Added configuration options
- Created unit tests

Closes #123
```

#### Checklist для PR

- [ ] Код следует style guide
- [ ] Добавлены/обновлены тесты
- [ ] Все тесты проходят
- [ ] Документация обновлена
- [ ] Нет конфликтов с main
- [ ] PR имеет описательный заголовок
- [ ] Связанные issues указаны

### 4. Разработка

#### Настройка окружения

```bash
git clone https://github.com/your-username/artem.integrator.git
cd artem.integrator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=bot

# Конкретный модуль
pytest tests/test_agent.py::TestAgent
```

#### Линтинг

```bash
# Форматирование
black bot/ tests/

# Type checking
mypy bot/

# Linting
pylint bot/
```

## Архитектурные решения

При добавлении новых функций:

1. **Следуйте существующим паттернам**
2. **Используйте dependency injection**
3. **Предпочитайте композицию наследованию**
4. **Делайте компоненты тестируемыми**
5. **Документируйте публичные API**

## Review процесс

1. Автоматические проверки должны пройти
2. Минимум один approve от maintainer
3. Обсуждение и исправление замечаний
4. Squash and merge в main

## Релизы

Мы используем [Semantic Versioning](https://semver.org/):
- MAJOR: Несовместимые изменения API
- MINOR: Новая функциональность (обратно совместимая)
- PATCH: Исправления багов

## Получение помощи

- **Discord**: [Ссылка на сервер]
- **Discussions**: GitHub Discussions
- **Email**: support@example.com

## Лицензия

Внося вклад, вы соглашаетесь, что ваш код будет лицензирован под MIT License.

## Благодарности

Спасибо всем, кто вносит вклад в развитие проекта! 🙏