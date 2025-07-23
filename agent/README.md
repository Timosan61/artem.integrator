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

## Прогресс разработки

- ✅ **Этап 1**: Базовый агент с OpenAI Function Calling
- ✅ **Этап 2**: Система инструментов (Tool System) 
- ✅ **Этап 3**: Intent Classification и маршрутизация
- ✅ **Этап 4**: Confirmation Manager
- 🔄 **Этап 5**: Реальные инструменты
- ⏳ **Этап 6**: Memory и Learning
- ⏳ **Этап 7**: Интеграция с Telegram
- ⏳ **Этап 8**: Финальное тестирование

## Документация этапов

- [Этап 1 - Завершен](STAGE1_COMPLETED.md)
- [Этап 2 - Завершен](STAGE2_COMPLETED.md)
- [Этап 3 - Завершен](STAGE3_COMPLETED.md)
- [Этап 4 - Завершен](STAGE4_COMPLETED.md)
- [План разработки](DEVELOPMENT_PLAN.md)