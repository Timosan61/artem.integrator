"""
Форматирование MCP результатов для Telegram
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.interfaces import MCPFunction, MCPFunctionType


class MCPFormatter:
    """
    Форматирует MCP результаты для отображения в Telegram
    """
    
    def format_status(self, status: Dict[str, Any]) -> str:
        """Форматирует статус MCP серверов"""
        lines = ["📊 <b>MCP Status</b>\n"]
        
        # Серверы
        servers = status.get("servers", {})
        if servers:
            lines.append("<b>🔌 Серверы:</b>")
            for name, info in servers.items():
                status_emoji = {
                    "connected": "✅",
                    "disconnected": "❌",
                    "error": "⚠️",
                    "initializing": "⏳"
                }.get(info["status"], "❓")
                
                lines.append(f"{status_emoji} {info['display_name']}")
                if info.get("last_error"):
                    lines.append(f"   └─ Ошибка: {info['last_error']}")
            lines.append("")
        
        # Статистика кеша
        cache_stats = status.get("cache_stats", {})
        if cache_stats:
            lines.append("<b>💾 Кеш:</b>")
            lines.append(f"• Размер: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}")
            lines.append(f"• Hit rate: {cache_stats.get('hit_rate', 0):.1%}")
            lines.append("")
        
        # Метрики
        metrics = status.get("metrics_summary", {})
        if metrics:
            lines.append("<b>📈 Метрики:</b>")
            lines.append(f"• Всего вызовов: {metrics.get('total_calls', 0)}")
            lines.append(f"• Успешных: {metrics.get('successful_calls', 0)}")
            lines.append(f"• Success rate: {metrics.get('success_rate', 0):.1%}")
            
            # Топ функций
            top_functions = metrics.get("top_functions", [])
            if top_functions:
                lines.append("\n<b>🔥 Популярные функции:</b>")
                for func in top_functions[:3]:
                    lines.append(f"• {func['function']}: {func['calls']} вызовов")
        
        return "\n".join(lines)
    
    def format_help(self) -> str:
        """Форматирует справку по командам"""
        return """<b>📚 MCP Команды</b>

<b>🔧 Основные команды:</b>
• /mcp status - статус всех серверов
• /mcp help - эта справка
• /mcp functions [server] - список функций

<b>💾 Supabase:</b>
• /mcp projects - список проектов
• /db <SQL> - выполнить SQL запрос
• /mcp tables <project_id> - список таблиц

<b>🌊 DigitalOcean:</b>
• /mcp apps - список приложений
• /mcp deploy <app_id> - деплой приложения

<b>📖 Context7:</b>
• /docs <библиотека> [тема] - документация
• /docs react hooks - пример

<b>💡 Примеры:</b>
• <code>/db SELECT * FROM users LIMIT 10</code>
• <code>/docs supabase authentication</code>
• <code>/mcp status</code>"""
    
    def format_sql_result(self, data: Dict[str, Any]) -> str:
        """Форматирует результат SQL запроса"""
        rows = data.get("rows", [])
        row_count = data.get("rowCount", 0)
        fields = data.get("fields", [])
        
        if not rows:
            return "📊 <b>Результат SQL:</b>\n\nНет данных (0 строк)"
        
        lines = [f"📊 <b>Результат SQL:</b> {row_count} строк\n"]
        
        # Ограничиваем вывод
        display_rows = rows[:10]
        
        # Форматируем как таблицу
        if fields:
            # Заголовки
            headers = [f["name"] for f in fields]
            lines.append("<code>" + " | ".join(headers) + "</code>")
            lines.append("<code>" + "-" * (len(" | ".join(headers))) + "</code>")
        
        # Данные
        for row in display_rows:
            if isinstance(row, dict):
                values = [str(row.get(h, "")) for h in headers]
            else:
                values = [str(v) for v in row]
            lines.append("<code>" + " | ".join(values) + "</code>")
        
        if len(rows) > 10:
            lines.append(f"\n<i>... и еще {len(rows) - 10} строк</i>")
        
        return "\n".join(lines)
    
    def format_projects_list(self, projects: List[Dict[str, Any]]) -> str:
        """Форматирует список проектов"""
        if not projects:
            return "📁 <b>Supabase проекты:</b>\n\nНет проектов"
        
        lines = ["📁 <b>Supabase проекты:</b>\n"]
        
        for project in projects:
            lines.append(f"<b>{project.get('name', 'Без имени')}</b>")
            lines.append(f"• ID: <code>{project.get('id')}</code>")
            lines.append(f"• Регион: {project.get('region', 'н/д')}")
            
            created_at = project.get('created_at')
            if created_at:
                lines.append(f"• Создан: {self._format_date(created_at)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_apps_list(self, data: Any) -> str:
        """Форматирует список приложений"""
        # Структура зависит от API DigitalOcean
        if isinstance(data, dict):
            apps = data.get("apps", [])
        else:
            apps = data if isinstance(data, list) else []
        
        if not apps:
            return "📱 <b>DigitalOcean приложения:</b>\n\nНет приложений"
        
        lines = ["📱 <b>DigitalOcean приложения:</b>\n"]
        
        for app in apps:
            lines.append(f"<b>{app.get('spec', {}).get('name', 'Без имени')}</b>")
            lines.append(f"• ID: <code>{app.get('id')}</code>")
            lines.append(f"• Статус: {app.get('status', 'н/д')}")
            lines.append(f"• URL: {app.get('live_url', 'н/д')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_docs_result(self, library: str, data: Any) -> str:
        """Форматирует результат поиска документации"""
        lines = [f"📖 <b>Документация {library}</b>\n"]
        
        # Здесь нужно адаптировать под реальную структуру Context7
        if isinstance(data, str):
            # Если вернулся просто текст
            lines.append(data[:1000])  # Ограничиваем длину
            if len(data) > 1000:
                lines.append("\n<i>... документация обрезана</i>")
        elif isinstance(data, dict):
            # Если структурированные данные
            title = data.get("title", library)
            content = data.get("content", "")
            url = data.get("url", "")
            
            lines.append(f"<b>{title}</b>")
            if url:
                lines.append(f"🔗 {url}")
            lines.append("")
            lines.append(content[:1000])
            if len(content) > 1000:
                lines.append("\n<i>... документация обрезана</i>")
        
        return "\n".join(lines)
    
    def format_functions_list(
        self, 
        functions: List[MCPFunction], 
        server_name: Optional[str] = None
    ) -> str:
        """Форматирует список функций"""
        if not functions:
            return "📋 <b>MCP Функции:</b>\n\nНет доступных функций"
        
        title = f"📋 <b>MCP Функции{f' ({server_name})' if server_name else ''}:</b>\n"
        lines = [title]
        
        # Группируем по серверам
        by_server = {}
        for func in functions:
            server = func.server
            if server not in by_server:
                by_server[server] = []
            by_server[server].append(func)
        
        # Форматируем по серверам
        for server, server_functions in by_server.items():
            lines.append(f"<b>{server.upper()}</b>")
            
            for func in server_functions:
                type_emoji = {
                    MCPFunctionType.READ: "👁",
                    MCPFunctionType.WRITE: "✏️",
                    MCPFunctionType.ADMIN: "🔐",
                    MCPFunctionType.SEARCH: "🔍"
                }.get(func.function_type, "📌")
                
                lines.append(f"{type_emoji} <code>{func.name}</code>")
                lines.append(f"   └─ {func.description}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def format_error(self, error: str) -> str:
        """Форматирует сообщение об ошибке"""
        return f"❌ <b>Ошибка MCP:</b>\n\n{error}"
    
    def _format_date(self, date_str: str) -> str:
        """Форматирует дату"""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return date_str