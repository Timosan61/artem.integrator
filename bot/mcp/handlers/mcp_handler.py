"""
Обработчик MCP запросов
"""

import logging
from typing import Dict, Any, Optional, List
import json

from ...core.interfaces import Message, Response, User
from ..core.manager import MCPManager
from ..core.interfaces import MCPResult, MCPFunction
from .formatter import MCPFormatter

logger = logging.getLogger(__name__)


class MCPHandler:
    """
    Обработчик MCP запросов
    
    Отвечает за:
    - Парсинг MCP команд
    - Вызов соответствующих функций
    - Форматирование результатов
    - Обработку ошибок
    """
    
    def __init__(self, mcp_manager: MCPManager):
        """
        Инициализация обработчика
        
        Args:
            mcp_manager: Менеджер MCP серверов
        """
        self.mcp_manager = mcp_manager
        self.formatter = MCPFormatter()
        
    async def handle_message(
        self, 
        message: Message, 
        mcp_intent: Dict[str, Any]
    ) -> Response:
        """
        Обрабатывает MCP сообщение
        
        Args:
            message: Сообщение пользователя
            mcp_intent: Распознанный MCP интент
            
        Returns:
            Response: Ответ с результатом
        """
        intent_type = mcp_intent.get("type")
        
        try:
            if intent_type == "command":
                return await self._handle_command(message, mcp_intent)
            elif intent_type == "sql":
                return await self._handle_sql(message, mcp_intent)
            elif intent_type == "docs":
                return await self._handle_docs(message, mcp_intent)
            elif intent_type == "natural":
                return await self._handle_natural(message, mcp_intent)
            else:
                return Response(
                    text="❓ Неизвестный тип MCP запроса",
                    metadata={"error": "Unknown intent type"}
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки MCP: {e}", exc_info=True)
            return Response(
                text=self.formatter.format_error(str(e)),
                metadata={"error": str(e)}
            )
    
    async def _handle_command(
        self, 
        message: Message, 
        intent: Dict[str, Any]
    ) -> Response:
        """Обрабатывает MCP команду"""
        command = intent.get("command", "").lower()
        args = intent.get("args", "")
        
        if command == "status":
            return await self._get_status()
        elif command == "help":
            return self._get_help()
        elif command == "projects":
            return await self._list_projects()
        elif command == "apps":
            return await self._list_apps()
        elif command == "functions":
            return await self._list_functions(args)
        else:
            return Response(
                text=f"❓ Неизвестная MCP команда: {command}",
                metadata={"error": "Unknown command"}
            )
    
    async def _handle_sql(
        self, 
        message: Message, 
        intent: Dict[str, Any]
    ) -> Response:
        """Обрабатывает SQL запрос"""
        query = intent.get("query", "").strip()
        
        if not query:
            return Response(
                text="❌ SQL запрос не указан\n\nИспользование: `/db SELECT * FROM table`",
                metadata={"error": "Empty query"}
            )
        
        # Получаем ID проекта (можно сделать настраиваемым)
        # Пока используем первый доступный проект
        projects_result = await self.mcp_manager.execute_function(
            "supabase", "list_projects", {}
        )
        
        if not projects_result.success or not projects_result.data:
            return Response(
                text="❌ Не удалось получить список проектов",
                metadata={"error": "No projects"}
            )
        
        project_id = projects_result.data[0]["id"]
        
        # Выполняем SQL
        result = await self.mcp_manager.execute_function(
            "supabase",
            "execute_sql",
            {"project_id": project_id, "query": query}
        )
        
        if result.success:
            formatted = self.formatter.format_sql_result(result.data)
            return Response(
                text=formatted,
                metadata={
                    "mcp_server": "supabase",
                    "mcp_function": "execute_sql",
                    "cached": result.cached
                }
            )
        else:
            return Response(
                text=self.formatter.format_error(result.error),
                metadata={"error": result.error}
            )
    
    async def _handle_docs(
        self, 
        message: Message, 
        intent: Dict[str, Any]
    ) -> Response:
        """Обрабатывает запрос документации"""
        library = intent.get("library", "")
        topic = intent.get("topic")
        
        if not library:
            return Response(
                text="❌ Библиотека не указана\n\nИспользование: `/docs react hooks`",
                metadata={"error": "No library"}
            )
        
        # Сначала ищем библиотеку
        result = await self.mcp_manager.execute_function(
            "context7",
            "resolve-library-id",
            {"libraryName": library}
        )
        
        if not result.success:
            return Response(
                text=f"❌ Библиотека '{library}' не найдена",
                metadata={"error": "Library not found"}
            )
        
        # Получаем документацию
        library_id = result.data.get("id")  # Предполагаемая структура
        
        docs_result = await self.mcp_manager.execute_function(
            "context7",
            "get-library-docs",
            {
                "context7CompatibleLibraryID": library_id,
                "topic": topic
            }
        )
        
        if docs_result.success:
            formatted = self.formatter.format_docs_result(
                library, docs_result.data
            )
            return Response(
                text=formatted,
                metadata={
                    "mcp_server": "context7",
                    "mcp_function": "get-library-docs",
                    "library": library,
                    "topic": topic
                }
            )
        else:
            return Response(
                text=self.formatter.format_error(docs_result.error),
                metadata={"error": docs_result.error}
            )
    
    async def _handle_natural(
        self, 
        message: Message, 
        intent: Dict[str, Any]
    ) -> Response:
        """Обрабатывает естественный язык с MCP интентом"""
        server = intent.get("server")
        query = intent.get("query")
        
        # Здесь можно использовать AI для определения конкретной функции
        # Пока просто возвращаем подсказку
        return Response(
            text=f"🤖 Обнаружен запрос к {server}\n\n"
                 f"Попробуйте использовать конкретные команды:\n"
                 f"• `/mcp help` - список всех команд\n"
                 f"• `/db <запрос>` - выполнить SQL\n"
                 f"• `/docs <библиотека>` - найти документацию",
            metadata={"mcp_intent": intent}
        )
    
    async def _get_status(self) -> Response:
        """Получает статус MCP серверов"""
        status = self.mcp_manager.get_status()
        formatted = self.formatter.format_status(status)
        
        return Response(
            text=formatted,
            metadata={"mcp_status": status}
        )
    
    def _get_help(self) -> Response:
        """Возвращает справку по MCP командам"""
        help_text = self.formatter.format_help()
        
        return Response(
            text=help_text,
            metadata={"mcp_help": True}
        )
    
    async def _list_projects(self) -> Response:
        """Список Supabase проектов"""
        result = await self.mcp_manager.execute_function(
            "supabase", "list_projects", {}
        )
        
        if result.success:
            formatted = self.formatter.format_projects_list(result.data)
            return Response(
                text=formatted,
                metadata={
                    "mcp_server": "supabase",
                    "mcp_function": "list_projects"
                }
            )
        else:
            return Response(
                text=self.formatter.format_error(result.error),
                metadata={"error": result.error}
            )
    
    async def _list_apps(self) -> Response:
        """Список DigitalOcean приложений"""
        result = await self.mcp_manager.execute_function(
            "digitalocean",
            "list_apps",
            {"query": {"page": 1, "per_page": 10}}
        )
        
        if result.success:
            formatted = self.formatter.format_apps_list(result.data)
            return Response(
                text=formatted,
                metadata={
                    "mcp_server": "digitalocean",
                    "mcp_function": "list_apps"
                }
            )
        else:
            return Response(
                text=self.formatter.format_error(result.error),
                metadata={"error": result.error}
            )
    
    async def _list_functions(self, server_name: str = None) -> Response:
        """Список доступных MCP функций"""
        functions = await self.mcp_manager.get_available_functions(server_name)
        formatted = self.formatter.format_functions_list(functions, server_name)
        
        return Response(
            text=formatted,
            metadata={
                "mcp_functions": len(functions),
                "server": server_name
            }
        )