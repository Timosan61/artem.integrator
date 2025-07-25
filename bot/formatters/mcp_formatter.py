"""
MCP Formatter для форматирования ответов MCP серверов
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MCPFormatter:
    """Форматировщик для ответов MCP серверов"""
    
    def __init__(self):
        """Инициализация форматировщика"""
        pass
    
    def format_mcp_response(self, response: Dict[str, Any], provider: str = "unknown") -> str:
        """
        Форматирует ответ MCP сервера для отображения пользователю
        
        Args:
            response: Ответ от MCP сервера
            provider: Название провайдера MCP
            
        Returns:
            str: Отформатированный ответ
        """
        try:
            if not response:
                return "Получен пустой ответ от MCP сервера"
            
            # Если есть прямой текстовый ответ
            if isinstance(response, str):
                return response
            
            # Если есть message в ответе
            if isinstance(response, dict) and "message" in response:
                return response["message"]
            
            # Если есть content в ответе
            if isinstance(response, dict) and "content" in response:
                content = response["content"]
                if isinstance(content, str):
                    return content
                elif isinstance(content, list) and content:
                    return "\n".join(str(item) for item in content)
            
            # Если есть данные приложений (для DigitalOcean)
            if isinstance(response, dict) and "apps" in response:
                return self._format_apps_list(response["apps"])
            
            # Если есть список серверов
            if isinstance(response, dict) and "servers" in response:
                return self._format_servers_list(response["servers"])
            
            # Если есть error
            if isinstance(response, dict) and "error" in response:
                return f"❌ Ошибка MCP: {response['error']}"
            
            # Общий случай - показываем как JSON
            return f"📊 Ответ от {provider}:\n```json\n{response}\n```"
            
        except Exception as e:
            logger.error(f"Ошибка форматирования MCP ответа: {e}")
            return f"❌ Ошибка форматирования ответа: {str(e)}"
    
    def _format_apps_list(self, apps: List[Dict[str, Any]]) -> str:
        """Форматирует список приложений"""
        if not apps:
            return "📱 Приложения не найдены"
        
        result = "📱 **Ваши приложения:**\n\n"
        for app in apps:
            name = app.get("name", "Неизвестно")
            status = app.get("status", "unknown")
            url = app.get("url", "")
            
            status_emoji = {
                "running": "🟢",
                "stopped": "🔴", 
                "pending": "🟡",
                "unknown": "⚪"
            }.get(status, "⚪")
            
            result += f"{status_emoji} **{name}**\n"
            if status:
                result += f"   Статус: {status}\n"
            if url:
                result += f"   URL: {url}\n"
            result += "\n"
        
        return result
    
    def _format_servers_list(self, servers: List[Dict[str, Any]]) -> str:
        """Форматирует список серверов"""
        if not servers:
            return "🖥️ MCP серверы не найдены"
        
        result = "🖥️ **Доступные MCP серверы:**\n\n"
        for server in servers:
            name = server.get("name", "Неизвестно")
            status = server.get("status", "unknown")
            
            status_emoji = {
                "connected": "🟢",
                "disconnected": "🔴",
                "connecting": "🟡",
                "unknown": "⚪"
            }.get(status, "⚪")
            
            result += f"{status_emoji} **{name}**\n"
            if status:
                result += f"   Статус: {status}\n"
            result += "\n"
        
        return result
    
    def format_error(self, error: str, provider: str = "MCP") -> str:
        """
        Форматирует ошибку MCP
        
        Args:
            error: Текст ошибки
            provider: Название провайдера
            
        Returns:
            str: Отформатированная ошибка
        """
        return f"❌ Ошибка {provider}: {error}"
    
    def format_success(self, message: str, provider: str = "MCP") -> str:
        """
        Форматирует успешный ответ
        
        Args:
            message: Сообщение об успехе
            provider: Название провайдера
            
        Returns:
            str: Отформатированное сообщение
        """
        return f"✅ {provider}: {message}"