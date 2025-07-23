# Intelligent Agent для Artem Integrator

## Обзор

Интеллектуальный AI агент с поддержкой инструментов для обработки запросов пользователей.

## Архитектура

```
Пользователь → Telegram Bot → Intelligent Agent
                                    ↓
                        ┌───────────┴───────────┐
                        │                       │
                  Простые ответы          Вызов инструментов
                        │                       │
                   OpenAI GPT-4          ┌──────┴──────┐
                        │                │             │
                        │           Claude SDK    Vision AI
                        │                │             │
                        └───────────┬────┴─────────────┘
                                    ↓
                              Ответ пользователю
```

## Основные компоненты

1. **Intent Classifier** - определяет намерение пользователя
2. **Tool Registry** - управляет доступными инструментами
3. **Confirmation Manager** - запрашивает подтверждение действий
4. **Memory Manager** - сохраняет контекст разговоров

## Поддерживаемые инструменты

- **MCP Executor** - выполнение MCP команд через Claude SDK
- **Image Generator** - генерация изображений
- **Vision Analyzer** - анализ видео и изображений
- **Database Query** - работа с базами данных

## Установка

```bash
pip install -r requirements.txt
```

## Конфигурация

См. `agent/config/agent_config.yaml`