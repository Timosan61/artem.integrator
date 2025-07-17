"""
Тесты для MCP Formatter

Проверяет:
- Форматирование SQL результатов
- Форматирование списков проектов/приложений
- Форматирование статусов деплоев
- Форматирование логов
- Форматирование документации
- Обработку ошибок
"""

import pytest
from datetime import datetime
import pandas as pd
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot.formatters.mcp_formatter import MCPFormatter


class TestMCPFormatter:
    """Тесты для MCPFormatter"""
    
    def test_format_sql_results_success(self):
        """Тест форматирования успешных SQL результатов"""
        result = {
            "success": True,
            "rows": [
                {"id": 1, "name": "User 1", "email": "user1@test.com"},
                {"id": 2, "name": "User 2", "email": "user2@test.com"}
            ],
            "affected_rows": 0,
            "execution_time": 0.123
        }
        
        formatted = MCPFormatter.format_sql_results(result)
        
        assert "📊 **Результат SQL запроса**" in formatted
        assert "User 1" in formatted
        assert "user1@test.com" in formatted
        assert "⚡ Время: 0.12с" in formatted
    
    def test_format_sql_results_empty(self):
        """Тест форматирования пустых SQL результатов"""
        result = {
            "success": True,
            "rows": [],
            "affected_rows": 5,
            "execution_time": 0.05
        }
        
        formatted = MCPFormatter.format_sql_results(result)
        
        assert "📊 **SQL запрос выполнен**" in formatted
        assert "📝 Затронуто строк: 5" in formatted
        assert "_Результат пустой_" in formatted
    
    def test_format_sql_results_many_rows(self):
        """Тест форматирования большого количества строк"""
        # Создаем 15 строк
        rows = [{"id": i, "value": f"value_{i}"} for i in range(15)]
        result = {
            "success": True,
            "rows": rows,
            "execution_time": 0.5
        }
        
        formatted = MCPFormatter.format_sql_results(result)
        
        assert "_Показаны первые 10 из 15 строк_" in formatted
        assert "value_9" in formatted  # 10-я строка
        assert "value_14" not in formatted  # 15-я строка
    
    def test_format_project_list(self):
        """Тест форматирования списка проектов"""
        result = {
            "success": True,
            "projects": [
                {"id": "proj1", "name": "Production", "status": "active", "region": "us-east-1"},
                {"id": "proj2", "name": "Staging", "status": "paused", "region": "eu-west-1"}
            ]
        }
        
        formatted = MCPFormatter.format_project_list(result)
        
        assert "📂 **Проекты Supabase** (2)" in formatted
        assert "🟢 **Production**" in formatted
        assert "🟡 **Staging**" in formatted
        assert "🆔 `proj1`" in formatted
        assert "🌍 Регион: us-east-1" in formatted
    
    def test_format_app_list(self):
        """Тест форматирования списка приложений"""
        result = {
            "success": True,
            "apps": [
                {
                    "id": "app1",
                    "name": "Web App",
                    "status": "active",
                    "updated_at": "2024-01-20T10:30:00Z"
                },
                {
                    "id": "app2",
                    "name": "API Server",
                    "status": "deploying"
                }
            ],
            "page": 1
        }
        
        formatted = MCPFormatter.format_app_list(result)
        
        assert "🌊 **Приложения DigitalOcean** (стр. 1)" in formatted
        assert "🟢 **Web App**" in formatted
        assert "🚀 **API Server**" in formatted
        assert "🆔 `app1`" in formatted
    
    def test_format_deployment_status(self):
        """Тест форматирования статуса деплоя"""
        result = {
            "success": True,
            "deployment": {
                "id": "deploy123",
                "created_at": "2024-01-20T10:00:00Z",
                "cause": "Manual deployment"
            },
            "status": "building",
            "status_emoji": "🔨",
            "progress": 45
        }
        
        formatted = MCPFormatter.format_deployment_status(result)
        
        assert "🔨 **Статус деплоя**" in formatted
        assert "📊 Статус: **building**" in formatted
        assert "📈 Прогресс: [▓▓▓▓░░░░░░] 45%" in formatted
        assert "📝 Причина: Manual deployment" in formatted
    
    def test_format_logs(self):
        """Тест форматирования логов"""
        log_content = """[2024-01-20 10:00:00] Starting application...
[2024-01-20 10:00:01] Connecting to database...
[2024-01-20 10:00:02] Server listening on port 8080"""
        
        result = {
            "success": True,
            "logs": log_content,
            "app_id": "app123",
            "log_type": "RUN"
        }
        
        formatted = MCPFormatter.format_logs(result)
        
        assert "📋 **Логи RUN**" in formatted
        assert "🆔 App: `app123`" in formatted
        assert "Starting application..." in formatted
        assert "```" in formatted  # Проверяем форматирование кода
    
    def test_format_logs_truncated(self):
        """Тест форматирования длинных логов"""
        # Создаем очень длинный лог
        long_log = "A" * 4000
        
        result = {
            "success": True,
            "logs": long_log,
            "app_id": "app123",
            "log_type": "BUILD"
        }
        
        formatted = MCPFormatter.format_logs(result)
        
        assert "_...показаны последние 3000 символов_" in formatted
        assert len(formatted) < 4000  # Убеждаемся, что лог обрезан
    
    def test_format_doc_search_results(self):
        """Тест форматирования результатов поиска документации"""
        result = {
            "success": True,
            "results": [
                {
                    "title": "React Hooks Guide",
                    "url": "https://docs.example.com/hooks",
                    "snippet": "Learn how to use React hooks effectively..."
                },
                {
                    "title": "useState Hook",
                    "url": "https://docs.example.com/usestate",
                    "snippet": "The useState hook allows you to add state to functional components."
                }
            ],
            "library": "react",
            "query": "hooks"
        }
        
        formatted = MCPFormatter.format_doc_search_results(result)
        
        assert "📚 **Поиск в react**" in formatted
        assert "🔍 Запрос: «hooks»" in formatted
        assert "**1. React Hooks Guide**" in formatted
        assert "_Learn how to use React hooks effectively..._" in formatted
        assert "🔗 [Читать полностью](https://docs.example.com/hooks)" in formatted
    
    def test_format_code_examples(self):
        """Тест форматирования примеров кода"""
        result = {
            "success": True,
            "examples": [
                {
                    "title": "Basic useState",
                    "code": "const [count, setCount] = useState(0);",
                    "language": "javascript",
                    "description": "Simple counter example"
                },
                {
                    "title": "useEffect Example",
                    "code": "useEffect(() => {\n  console.log('Component mounted');\n}, []);",
                    "language": "javascript"
                }
            ],
            "library": "react",
            "topic": "hooks"
        }
        
        formatted = MCPFormatter.format_code_examples(result)
        
        assert "💻 **Примеры react**" in formatted
        assert "📖 Тема: hooks" in formatted
        assert "**Basic useState**" in formatted
        assert "_Simple counter example_" in formatted
        assert "```javascript" in formatted
        assert "const [count, setCount] = useState(0);" in formatted
    
    def test_format_error(self):
        """Тест форматирования ошибок"""
        result = {
            "success": False,
            "error": "Connection timeout",
            "message": "❌ Не удалось подключиться к базе данных"
        }
        
        formatted = MCPFormatter.format_error(result)
        
        assert formatted == "❌ Не удалось подключиться к базе данных"
        
        # Тест с только error
        result_error_only = {
            "success": False,
            "error": "Internal server error"
        }
        
        formatted2 = MCPFormatter.format_error(result_error_only)
        assert "❌ **Ошибка**" in formatted2
        assert "Internal server error" in formatted2
    
    def test_format_mcp_status(self):
        """Тест форматирования статуса MCP"""
        status = {
            "mcp_enabled": True,
            "anthropic_available": True,
            "openai_available": True,
            "total_functions": 15,
            "servers": {
                "supabase": {
                    "enabled": True,
                    "display_name": "Supabase",
                    "functions_count": 8
                },
                "digitalocean": {
                    "enabled": False,
                    "display_name": "DigitalOcean",
                    "functions_count": 0
                }
            }
        }
        
        formatted = MCPFormatter.format_mcp_status(status)
        
        assert "🔌 **Статус MCP**" in formatted
        assert "📊 MCP: ✅ Включен" in formatted
        assert "🤖 Claude: ✅ Доступен" in formatted
        assert "🔧 Функций: 15" in formatted
        assert "✅ Supabase (8 функций)" in formatted
        assert "❌ DigitalOcean" in formatted
    
    def test_format_server_metrics(self):
        """Тест форматирования метрик"""
        metrics = {
            "total_calls": 100,
            "total_successful": 95,
            "total_failed": 5,
            "average_execution_time": 1.23,
            "servers": {
                "supabase": {
                    "total_calls": 60,
                    "functions": {
                        "list_projects": {"total_calls": 30},
                        "execute_sql": {"total_calls": 20},
                        "list_tables": {"total_calls": 10}
                    }
                },
                "digitalocean": {
                    "total_calls": 40,
                    "functions": {
                        "list_apps": {"total_calls": 25},
                        "create_deployment": {"total_calls": 15}
                    }
                }
            }
        }
        
        formatted = MCPFormatter.format_server_metrics(metrics)
        
        assert "📊 **Метрики MCP**" in formatted
        assert "📈 Всего вызовов: 100" in formatted
        assert "✅ Успешных: 95 (95.0%)" in formatted
        assert "❌ Ошибок: 5" in formatted
        assert "⚡ Среднее время: 1.23с" in formatted
        assert "**supabase**: 60 вызовов" in formatted
        assert "• list_projects: 30" in formatted
    
    def test_format_help_message(self):
        """Тест форматирования справки"""
        help_msg = MCPFormatter.format_help_message()
        
        assert "🔌 **MCP Команды**" in help_msg
        assert "**Supabase:**" in help_msg
        assert "/mcp projects" in help_msg
        assert "**DigitalOcean:**" in help_msg
        assert "/deploy <app_id>" in help_msg
        assert "**Context7:**" in help_msg
        assert "/docs <библиотека> <запрос>" in help_msg
    
    def test_format_time(self):
        """Тест форматирования времени"""
        # ISO формат с Z
        iso_time = "2024-01-20T15:30:45Z"
        formatted = MCPFormatter._format_time(iso_time)
        assert "20.01.2024" in formatted
        assert "15:30" in formatted
        
        # Невалидный формат
        invalid_time = "invalid-date"
        formatted_invalid = MCPFormatter._format_time(invalid_time)
        assert formatted_invalid == "invalid-date"
    
    def test_edge_cases(self):
        """Тест граничных случаев"""
        # Пустой результат
        empty_result = {"success": True}
        
        # SQL без строк
        formatted = MCPFormatter.format_sql_results(empty_result)
        assert "Результат пустой" in formatted
        
        # Проекты без данных
        empty_projects = {"success": True, "projects": []}
        formatted = MCPFormatter.format_project_list(empty_projects)
        assert "_Проектов не найдено_" in formatted
        
        # Логи без контента
        empty_logs = {"success": True, "logs": "", "app_id": "test", "log_type": "RUN"}
        formatted = MCPFormatter.format_logs(empty_logs)
        assert "_Логи пусты_" in formatted


# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v"])