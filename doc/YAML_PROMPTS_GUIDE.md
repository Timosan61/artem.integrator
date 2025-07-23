# Руководство по настройке промптов через YAML

## Обзор

Система промптов для MCP команд теперь настраивается через YAML файлы, что позволяет:
- Легко добавлять новые команды без изменения кода
- Настраивать триггеры для голосовых команд
- Изменять шаблоны ответов
- Управлять доступными инструментами MCP

## Структура файлов

### 1. `data/mcp_voice_prompts.yaml`

Этот файл управляет обработкой голосовых команд.

```yaml
voice_commands:
  system_prompt: |
    Системный промпт для голосового ассистента
    
  scenarios:
    - name: "название_сценария"
      triggers:
        - "фраза триггер 1"
        - "фраза триггер 2"
      action: "mcp__digitalocean__function_name"
      parameters: 
        query: {}
      response_template: |
        📱 **Шаблон ответа:**
        {переменная}
```

#### Ключевые поля:

- **name**: Уникальное имя сценария
- **triggers**: Список фраз, которые активируют сценарий
- **action**: MCP функция для вызова
- **parameters**: Параметры для MCP функции
- **fallback_message**: Сообщение, если функция недоступна
- **response_template**: Шаблон форматирования ответа

### 2. `data/claude_sdk_prompts.yaml`

Этот файл управляет системными промптами и текстовыми командами.

```yaml
system_prompt: |
  Основной системный промпт для Claude Code SDK

allowed_tools:
  digitalocean:
    apps:
      - mcp__digitalocean__list_apps
      - mcp__digitalocean__get_app

command_mappings:
  "/mcp apps": 
    prompt: "Промпт для выполнения команды"
    tools: ["mcp__digitalocean__list_apps"]
```

## Примеры использования

### Добавление новой голосовой команды

1. Откройте `mcp_voice_prompts.yaml`
2. Добавьте новый сценарий:

```yaml
- name: "check_status"
  triggers:
    - "проверь статус"
    - "какой статус"
    - "статус системы"
  action: "mcp__digitalocean__get_app_status"
  response_template: |
    📊 **Статус приложения:**
    {status_info}
```

### Добавление поддержки дроплетов (когда будет доступно)

1. В `claude_sdk_prompts.yaml` раскомментируйте:

```yaml
droplets_future:
  - mcp__digitalocean__list_droplets
  - mcp__digitalocean__create_droplet
```

2. В `mcp_voice_prompts.yaml` измените сценарий droplets:

```yaml
- name: "droplets"
  triggers:
    - "дроплеты"
    - "серверы"
  action: "mcp__digitalocean__list_droplets"
  # Удалите fallback_message
```

### Изменение формата ответов

Отредактируйте `response_template` в нужном сценарии:

```yaml
response_template: |
  🎯 **Ваши приложения:**
  {% for app in apps %}
  ▫️ {{app.name}} ({{app.region}})
  {% endfor %}
```

## Горячая перезагрузка

Промпты можно перезагрузить без перезапуска сервиса:

```python
# В коде
claude_code_service.reload_prompts()
```

Или добавить admin команду:
```python
# /reload_prompts
if command == "/reload_prompts":
    claude_code_service.reload_prompts()
    return "✅ Промпты перезагружены"
```

## Отладка

### Проверка загрузки

```bash
python3 test_yaml_prompts.py
```

### Логирование

В логах будут сообщения:
- `✅ Промпты успешно перезагружены` - при успешной загрузке
- `⚠️ YAML файл не найден` - если файл отсутствует
- `❌ Ошибка загрузки YAML` - при ошибке парсинга

### Валидация YAML

Проверьте синтаксис:
```bash
python3 -c "import yaml; yaml.safe_load(open('data/mcp_voice_prompts.yaml'))"
```

## Лучшие практики

1. **Триггеры**: Добавляйте различные варианты фраз
   ```yaml
   triggers:
     - "покажи приложения"
     - "список приложений"
     - "мои приложения"
     - "apps"
   ```

2. **Fallback**: Всегда добавляйте `default_response` для неизвестных команд

3. **Параметры**: Используйте `requires_context: true` для команд, требующих дополнительную информацию

4. **Тестирование**: После изменений всегда тестируйте с помощью `test_yaml_prompts.py`

## Расширение функционала

### Добавление нового MCP сервера

1. Добавьте в `claude_sdk_prompts.yaml`:
   ```yaml
   allowed_tools:
     new_service:
       category:
         - mcp__new_service__function
   ```

2. Добавьте маппинги команд:
   ```yaml
   command_mappings:
     "/mcp new":
       prompt: "Execute new service command"
       tools: ["mcp__new_service__function"]
   ```

### Мультиязычность

Можно добавить поддержку других языков:
```yaml
scenarios:
  - name: "applications"
    triggers_ru:
      - "приложения"
    triggers_en:
      - "applications"
      - "apps"
```

## Миграция старых команд

Все старые команды сохранены в legacy методах:
- `_get_legacy_voice_prompt()`
- `_get_legacy_mcp_prompt()`
- `_get_legacy_allowed_tools()`

Они используются как fallback, если YAML не загружен.