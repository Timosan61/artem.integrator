"""
MCP Formatter - Форматирование ответов MCP для Telegram

Преобразует ответы от MCP серверов в удобный для чтения формат в Telegram.
Поддерживает:
- Таблицы для SQL результатов
- Прогресс-бары для деплоев
- Структурированные сообщения для документации
- Интерактивные кнопки
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import html


class MCPFormatter:
    """Форматирует ответы MCP для Telegram"""
    
    @staticmethod
    def format_sql_results(result: Dict[str, Any]) -> str:
        """
        Форматирует результаты SQL запроса
        
        Args:
            result: Результат выполнения SQL
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        rows = result.get("rows", [])
        affected_rows = result.get("affected_rows", 0)
        execution_time = result.get("execution_time", 0)
        
        if not rows:
            return f"""📊 **SQL запрос выполнен**

⚡ Время выполнения: {execution_time:.2f}с
📝 Затронуто строк: {affected_rows}

_Результат пустой_"""
        
        # Форматируем таблицу
        message = "📊 **Результат SQL запроса**\n\n"
        
        # Если строк много, показываем первые 10
        display_rows = rows[:10]
        
        # Определяем колонки
        if display_rows:
            columns = list(display_rows[0].keys())
            
            # Форматируем как код для моноширинного шрифта
            message += "```\n"
            
            # Заголовки колонок
            header = " | ".join(str(col)[:15] for col in columns)
            message += header + "\n"
            message += "-" * len(header) + "\n"
            
            # Данные
            for row in display_rows:
                row_str = " | ".join(
                    str(row.get(col, ""))[:15] 
                    for col in columns
                )
                message += row_str + "\n"
            
            message += "```\n"
            
            if len(rows) > 10:
                message += f"\n_Показаны первые 10 из {len(rows)} строк_\n"
        
        message += f"\n⚡ Время: {execution_time:.2f}с"
        if affected_rows:
            message += f"\n📝 Затронуто строк: {affected_rows}"
        
        return message
    
    @staticmethod
    def format_project_list(result: Dict[str, Any]) -> str:
        """
        Форматирует список проектов Supabase
        
        Args:
            result: Результат получения проектов
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        projects = result.get("projects", [])
        
        if not projects:
            return "📂 **Проекты Supabase**\n\n_Проектов не найдено_"
        
        message = f"📂 **Проекты Supabase** ({len(projects)})\n\n"
        
        for project in projects:
            status_emoji = "🟢" if project.get("status") == "active" else "🟡"
            name = project.get("name", "Без названия")
            project_id = project.get("id", "")
            region = project.get("region", "неизвестно")
            
            message += f"{status_emoji} **{name}**\n"
            message += f"   🆔 `{project_id}`\n"
            message += f"   🌍 Регион: {region}\n\n"
        
        return message
    
    @staticmethod
    def format_app_list(result: Dict[str, Any]) -> str:
        """
        Форматирует список приложений DigitalOcean
        
        Args:
            result: Результат получения приложений
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        apps = result.get("apps", [])
        page = result.get("page", 1)
        
        if not apps:
            return "🌊 **Приложения DigitalOcean**\n\n_Приложений не найдено_"
        
        message = f"🌊 **Приложения DigitalOcean** (стр. {page})\n\n"
        
        for app in apps:
            status_emoji = {
                "active": "🟢",
                "deploying": "🚀",
                "error": "🔴",
                "building": "🔨"
            }.get(app.get("status", ""), "⚪")
            
            name = app.get("name", "Без названия")
            app_id = app.get("id", "")
            updated = app.get("updated_at", "")
            
            message += f"{status_emoji} **{name}**\n"
            message += f"   🆔 `{app_id}`\n"
            
            if updated:
                message += f"   🕐 Обновлено: {MCPFormatter._format_time(updated)}\n"
            
            message += "\n"
        
        return message
    
    @staticmethod
    def format_deployment_status(result: Dict[str, Any]) -> str:
        """
        Форматирует статус деплоя
        
        Args:
            result: Результат проверки статуса
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        deployment = result.get("deployment", {})
        status = result.get("status", "unknown")
        status_emoji = result.get("status_emoji", "❓")
        progress = result.get("progress", 0)
        
        message = f"{status_emoji} **Статус деплоя**\n\n"
        message += f"🆔 ID: `{deployment.get('id', 'неизвестно')}`\n"
        message += f"📊 Статус: **{status}**\n"
        
        # Прогресс-бар
        if 0 <= progress <= 100:
            filled = int(progress / 10)
            empty = 10 - filled
            progress_bar = "▓" * filled + "░" * empty
            message += f"📈 Прогресс: [{progress_bar}] {progress}%\n"
        
        # Дополнительная информация
        if deployment.get("created_at"):
            message += f"🕐 Начат: {MCPFormatter._format_time(deployment['created_at'])}\n"
        
        if deployment.get("cause"):
            message += f"📝 Причина: {deployment['cause']}\n"
        
        return message
    
    @staticmethod
    def format_logs(result: Dict[str, Any]) -> str:
        """
        Форматирует логи приложения
        
        Args:
            result: Результат получения логов
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        logs = result.get("logs", "")
        app_id = result.get("app_id", "")
        log_type = result.get("log_type", "")
        
        message = f"📋 **Логи {log_type}**\n"
        message += f"🆔 App: `{app_id}`\n\n"
        
        if not logs:
            message += "_Логи пусты_"
            return message
        
        # Ограничиваем длину логов
        max_length = 3000
        if len(logs) > max_length:
            logs = logs[-max_length:]
            message += "_...показаны последние 3000 символов_\n\n"
        
        # Экранируем HTML символы
        logs = html.escape(logs)
        
        # Форматируем как код
        message += f"```\n{logs}\n```"
        
        return message
    
    @staticmethod
    def format_doc_search_results(result: Dict[str, Any]) -> str:
        """
        Форматирует результаты поиска документации
        
        Args:
            result: Результат поиска
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        results = result.get("results", [])
        library = result.get("library", "")
        query = result.get("query", "")
        
        if not results:
            return f"📚 **Поиск в {library}**\n\nПо запросу «{query}» ничего не найдено"
        
        message = f"📚 **Поиск в {library}**\n🔍 Запрос: «{query}»\n\n"
        
        for i, doc in enumerate(results, 1):
            title = doc.get("title", "Без названия")
            url = doc.get("url", "")
            snippet = doc.get("snippet", "")
            
            message += f"**{i}. {title}**\n"
            
            if snippet:
                # Ограничиваем длину сниппета
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."
                message += f"_{snippet}_\n"
            
            if url:
                message += f"🔗 [Читать полностью]({url})\n"
            
            message += "\n"
        
        return message
    
    @staticmethod
    def format_code_examples(result: Dict[str, Any]) -> str:
        """
        Форматирует примеры кода
        
        Args:
            result: Результат получения примеров
            
        Returns:
            str: Отформатированное сообщение
        """
        if not result.get("success"):
            return MCPFormatter.format_error(result)
        
        examples = result.get("examples", [])
        library = result.get("library", "")
        topic = result.get("topic", "")
        
        if not examples:
            return f"💻 **Примеры {library}**\n\nПримеров для «{topic}» не найдено"
        
        message = f"💻 **Примеры {library}**\n📖 Тема: {topic}\n\n"
        
        for i, example in enumerate(examples, 1):
            title = example.get("title", f"Пример {i}")
            code = example.get("code", "")
            language = example.get("language", "javascript")
            description = example.get("description", "")
            
            message += f"**{title}**\n"
            
            if description:
                message += f"_{description}_\n\n"
            
            if code:
                # Ограничиваем длину кода
                if len(code) > 1000:
                    code = code[:1000] + "\n// ..."
                
                message += f"```{language}\n{code}\n```\n\n"
        
        return message
    
    @staticmethod
    def format_error(result: Dict[str, Any]) -> str:
        """
        Форматирует сообщение об ошибке
        
        Args:
            result: Результат с ошибкой
            
        Returns:
            str: Отформатированное сообщение об ошибке
        """
        error = result.get("error", "Неизвестная ошибка")
        message = result.get("message", "")
        
        if message:
            return message
        
        return f"❌ **Ошибка**\n\n{error}"
    
    @staticmethod
    def format_mcp_status(status: Dict[str, Any]) -> str:
        """
        Форматирует общий статус MCP системы
        
        Args:
            status: Статус MCP
            
        Returns:
            str: Отформатированное сообщение
        """
        message = "🔌 **Статус MCP**\n\n"
        
        enabled = status.get("mcp_enabled", False)
        message += f"📊 MCP: {'✅ Включен' if enabled else '❌ Выключен'}\n"
        
        if status.get("anthropic_available"):
            message += "🤖 Claude: ✅ Доступен\n"
        
        if status.get("openai_available"):
            message += "🤖 OpenAI: ✅ Доступен\n"
        
        total_functions = status.get("total_functions", 0)
        message += f"🔧 Функций: {total_functions}\n\n"
        
        # Статус серверов
        servers = status.get("servers", {})
        if servers:
            message += "**Серверы:**\n"
            for server_name, server_status in servers.items():
                emoji = "✅" if server_status.get("enabled") else "❌"
                display_name = server_status.get("display_name", server_name)
                functions = server_status.get("functions_count", 0)
                
                message += f"{emoji} {display_name} ({functions} функций)\n"
        
        return message
    
    @staticmethod
    def format_server_metrics(metrics: Dict[str, Any]) -> str:
        """
        Форматирует метрики использования MCP
        
        Args:
            metrics: Метрики
            
        Returns:
            str: Отформатированное сообщение
        """
        message = "📊 **Метрики MCP**\n\n"
        
        total_calls = metrics.get("total_calls", 0)
        successful = metrics.get("total_successful", 0)
        failed = metrics.get("total_failed", 0)
        avg_time = metrics.get("average_execution_time", 0)
        
        message += f"📈 Всего вызовов: {total_calls}\n"
        if total_calls > 0:
            success_rate = (successful / total_calls) * 100
            message += f"✅ Успешных: {successful} ({success_rate:.1f}%)\n"
            message += f"❌ Ошибок: {failed}\n"
            message += f"⚡ Среднее время: {avg_time:.2f}с\n\n"
        
        # Детали по серверам
        servers = metrics.get("servers", {})
        if servers:
            message += "**По серверам:**\n"
            for server_name, server_metrics in servers.items():
                calls = server_metrics.get("total_calls", 0)
                if calls > 0:
                    message += f"\n**{server_name}**: {calls} вызовов\n"
                    
                    # Топ функций
                    functions = server_metrics.get("functions", {})
                    if functions:
                        sorted_funcs = sorted(
                            functions.items(), 
                            key=lambda x: x[1]["total_calls"], 
                            reverse=True
                        )[:3]
                        
                        for func_name, func_metrics in sorted_funcs:
                            func_calls = func_metrics["total_calls"]
                            message += f"  • {func_name}: {func_calls}\n"
        
        return message
    
    @staticmethod
    def format_help_message() -> str:
        """
        Форматирует сообщение помощи по MCP командам
        
        Returns:
            str: Сообщение помощи
        """
        return """🔌 **MCP Команды**

**Supabase:**
• `/mcp projects` - список проектов
• `/db <запрос>` или `/sql <запрос>` - выполнить SQL
• `/mcp tables <project_id>` - список таблиц

**DigitalOcean:**
• `/mcp apps` - список приложений
• `/deploy <app_id>` - запустить деплой
• `/logs <app_id>` - просмотр логов

**Context7:**
• `/docs <библиотека> <запрос>` - поиск документации
• `/mcp examples <библиотека> <тема>` - примеры кода

**Система:**
• `/mcp status` - статус MCP серверов
• `/mcp metrics` - метрики использования
• `/mcp help` - эта справка"""
    
    @staticmethod
    def _format_time(timestamp: str) -> str:
        """Форматирует временную метку"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return timestamp


# Создаем глобальный экземпляр форматтера
mcp_formatter = MCPFormatter()