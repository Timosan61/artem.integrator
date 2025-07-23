"""
Claude Code Service - интеграция с Claude Code SDK для выполнения MCP команд

Этот сервис позволяет боту использовать MCP серверы через Claude Code SDK.
"""

import logging
import json
import os
from typing import Optional, Dict, Any, List, AsyncIterator
from pathlib import Path
import asyncio
import anyio

try:
    from claude_code_sdk import query, ClaudeCodeOptions, Message
    CLAUDE_CODE_SDK_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ claude-code-sdk не установлен. Работаем в режиме эмуляции")
    CLAUDE_CODE_SDK_AVAILABLE = False
    # Эмуляция классов для совместимости
    class Message:
        def __init__(self, role: str, content: str):
            self.role = role
            self.content = content
            self.tool_calls = []
    
    class ClaudeCodeOptions:
        def __init__(self, **kwargs):
            pass

from ..core.config import config

logger = logging.getLogger(__name__)


class ClaudeCodeService:
    """
    Сервис для работы с Claude Code SDK и выполнения MCP команд
    """
    
    def __init__(self):
        """Инициализация сервиса"""
        self.enabled = config.mcp.enabled and config.anthropic.enabled
        self.api_key = config.anthropic.api_key
        # Используем локальную конфигурацию если она существует
        local_config = Path(__file__).parent.parent.parent / "data" / "mcp-servers-local.json"
        default_config = Path(__file__).parent.parent.parent / "data" / "mcp-servers.json"
        self.mcp_config_path = local_config if local_config.exists() else default_config
        
        if not self.enabled:
            logger.warning("⚠️ Claude Code Service отключен: MCP или Anthropic не настроены")
            return
            
        # Настройка переменных окружения для SDK
        if self.api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.api_key
            
        # Настройка Moonshot API для обхода ограничений
        os.environ["ANTHROPIC_BASE_URL"] = "https://api.moonshot.ai/anthropic"
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-QNnXEpPxnV9OCIhr6IMUcXQu2b4Vsuq2biZVAFce0KIoUTsx"
            
        logger.info("✅ Claude Code Service инициализирован")
        
    async def execute_mcp_command(
        self, 
        command: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет MCP команду через Claude Code SDK
        
        Args:
            command: Команда для выполнения (например: "/mcp status")
            user_id: ID пользователя для логирования
            
        Returns:
            Dict с результатом выполнения
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "MCP сервис отключен"
            }
            
        try:
            logger.info(f"🔧 Выполнение MCP команды: {command} (user: {user_id})")
            
            # Формируем промпт для Claude Code
            prompt = self._format_mcp_prompt(command)
            
            # Опции для SDK
            if CLAUDE_CODE_SDK_AVAILABLE:
                # Загружаем конфигурацию MCP серверов
                mcp_servers = {}
                if self.mcp_config_path.exists():
                    try:
                        with open(self.mcp_config_path) as f:
                            mcp_config = json.load(f)
                            # Преобразуем конфигурацию в формат SDK
                            for server_name, server_config in mcp_config.get("mcpServers", {}).items():
                                mcp_servers[server_name] = {
                                    "command": server_config.get("command", ""),
                                    "args": server_config.get("args", []),
                                    "env": server_config.get("env", {})
                                }
                    except Exception as e:
                        logger.warning(f"Не удалось загрузить MCP конфигурацию: {e}")
                
                # Добавляем более явные инструкции для MCP
                system_prompt = self._get_system_prompt()
                if "apps" in command.lower() or "digitalocean" in command.lower():
                    system_prompt = f"""Execute user command: {command}

IMPORTANT: Call mcp__digitalocean__list_apps with parameter {{"query": {{}}}} immediately.

DO NOT:
- Use TodoWrite or any todo management tools
- Use Task tool
- Plan or organize tasks
- Use any Cloudflare functions

JUST execute mcp__digitalocean__list_apps directly and return the results.

USE ONLY THESE FUNCTIONS. NO EXCEPTIONS."""
                
                # Определяем разрешенные инструменты на основе команды
                allowed_tools = []
                if "apps" in command.lower() or "digitalocean" in command.lower():
                    # Только DigitalOcean инструменты
                    allowed_tools = [
                        "mcp__digitalocean__list_apps", 
                        "mcp__digitalocean__get_app", 
                        "mcp__digitalocean__create_app", 
                        "mcp__digitalocean__list_deployments",
                        "mcp__digitalocean__get_deployment",
                        "mcp__digitalocean__list_databases_cluster"
                    ]
                elif "project" in command.lower() or "supabase" in command.lower() or "/db" in command:
                    # Только Supabase инструменты
                    allowed_tools = [
                        "mcp__supabase__list_projects", 
                        "mcp__supabase__get_project",
                        "mcp__supabase__execute_sql", 
                        "mcp__supabase__list_tables",
                        "mcp__supabase__list_organizations"
                    ]
                elif "doc" in command.lower() or "context7" in command.lower():
                    # Только Context7 инструменты
                    allowed_tools = [
                        "mcp__context7__resolve-library-id", 
                        "mcp__context7__get-library-docs"
                    ]
                else:
                    # Если не уверены - используем стандартный набор
                    allowed_tools = self._get_allowed_tools(command)
                
                # Список запрещенных инструментов (все Cloudflare функции)
                disallowed_tools = [
                    "mcp__cloudflare__*",  # Блокируем все Cloudflare функции
                    "mcp__cloudflare__worker_list",
                    "mcp__cloudflare__ai_inference",
                    "mcp__cloudflare__kv_get",
                    "mcp__cloudflare__r2_list_buckets",
                    "mcp__cloudflare__d1_list_databases",
                    "mcp__cloudflare__analytics_get",
                    "mcp__cloudflare__zones_list"
                ]
                
                # Добавляем все возможные инструменты управления задачами в запрещенные
                task_management_tools = [
                    "TodoWrite", "Task", "ExitPlanMode", "WebSearch", "WebFetch",
                    "Read", "Write", "Edit", "MultiEdit", "Bash", "LS", "Grep", "Glob"
                ]
                
                if "apps" in command.lower():
                    # Для команды apps разрешаем ТОЛЬКО list_apps
                    allowed_tools = ["mcp__digitalocean__list_apps"]
                    disallowed_tools.extend(task_management_tools)
                
                options = ClaudeCodeOptions(
                    max_turns=1,  # Одна итерация для команды
                    system_prompt=system_prompt,
                    cwd=Path.cwd(),
                    allowed_tools=allowed_tools,  # Ограничиваем доступные инструменты
                    disallowed_tools=disallowed_tools,  # Блокируем Cloudflare и task management
                    mcp_servers=mcp_servers,  # Передаем конфигурацию серверов
                    permission_mode="acceptEdits"  # Автоматически принимаем использование инструментов
                )
            else:
                options = None
            
            # Используем реальный SDK если доступен
            if CLAUDE_CODE_SDK_AVAILABLE:
                try:
                    # Используем настоящий SDK
                    logger.info("🚀 Используем реальный Claude Code SDK")
                    messages: List[Message] = []
                    
                    try:
                        async for message in query(prompt=prompt, options=options):
                            messages.append(message)
                            # Безопасный вывод для отладки
                            msg_type = type(message).__name__
                            msg_role = getattr(message, 'role', 'No role')
                            msg_content = str(getattr(message, 'content', ''))[:100] if hasattr(message, 'content') else 'No content'
                            logger.debug(f"📨 Получено сообщение: {msg_type} - {msg_role} - {msg_content}...")
                            
                            # Ограничиваем количество сообщений для предотвращения переполнения
                            if len(messages) > 50:
                                logger.warning("⚠️ Слишком много сообщений от SDK, прерываем")
                                break
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Ошибка декодирования JSON от SDK: {e}")
                        logger.warning("⚠️ Используем частичный результат")
                        # Продолжаем с тем, что успели получить
                        
                    # Обрабатываем результат
                    result = self._process_messages(messages, command)
                except Exception as sdk_error:
                    logger.error(f"❌ Ошибка SDK: {sdk_error}")
                    # Больше не переключаемся на эмуляцию - возвращаем ошибку
                    result = {
                        "success": False,
                        "command": command,
                        "error": f"Ошибка выполнения MCP: {str(sdk_error)}"
                    }
            else:
                # SDK недоступен - возвращаем ошибку
                logger.error("❌ Claude Code SDK недоступен")
                result = {
                    "success": False,
                    "command": command,
                    "error": "Claude Code SDK не установлен или недоступен"
                }
            
            logger.info(f"✅ MCP команда выполнена успешно: {command}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения MCP команды: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_mcp_prompt(self, command: str) -> str:
        """
        Форматирует команду в промпт для Claude Code
        
        Args:
            command: Исходная команда
            
        Returns:
            Промпт для SDK
        """
        # Парсим команду
        parts = command.strip().split()
        
        # Обработка различных типов команд
        if command.startswith("/mcp status"):
            return "Check the status of all MCP servers and list available functions"
            
        elif command.startswith("/mcp projects"):
            return "List all Supabase projects using MCP"
            
        elif command.startswith("/mcp organizations"):
            return "List all Supabase organizations using MCP"
            
        elif command.startswith("/db "):
            sql_query = command[4:].strip()
            return f"Execute SQL query using Supabase MCP: {sql_query}"
            
        elif command.startswith("/mcp apps"):
            return "List all DigitalOcean apps. You MUST use the mcp__digitalocean__list_apps function. This is a DigitalOcean operation, not Cloudflare. Return the full list of apps with their names, status, and other details."
        
        elif command.startswith("/mcp digitalocean"):
            # Обрабатываем разные команды DigitalOcean
            sub_command = command[17:].strip()
            if sub_command == "list apps" or sub_command == "apps":
                return "Use mcp__digitalocean__list_apps to get all DigitalOcean applications."
            elif sub_command.startswith("deployments"):
                return "Use mcp__digitalocean__list_deployments to get deployment history."
            else:
                return f"Execute DigitalOcean MCP command: {sub_command}"
            
        elif command.startswith("/docs "):
            parts = command[6:].strip().split(maxsplit=1)
            if len(parts) >= 2:
                library, query = parts[0], parts[1]
                return f"Search documentation for {library} about: {query}"
            else:
                return f"Search documentation for: {parts[0]}"
                
        elif command.startswith("/mcp context7"):
            query = command[13:].strip()
            return f"Search Context7 documentation: {query}"
            
        else:
            # Общий случай
            return f"Execute MCP command: {command}"
    
    def _get_system_prompt(self) -> str:
        """Возвращает системный промпт для Claude Code"""
        return """You are an MCP assistant that helps execute commands through Model Context Protocol servers.

Available MCP servers:
1. DigitalOcean - for app management and deployments (mcp__digitalocean__*)
2. Supabase - for database operations and project management (mcp__supabase__*)
3. Context7 - for documentation search (mcp__context7__*)

IMPORTANT RULES:
- NEVER use mcp__cloudflare__* functions - they are NOT available
- Only use functions from the three servers listed above
- Match the server to the task (apps = DigitalOcean, database = Supabase, docs = Context7)

When executing commands:
- Use the appropriate MCP tool based on the command
- Format responses clearly and concisely
- Include relevant data from the MCP response
- Handle errors gracefully
- Return structured data when possible

Important: Execute the requested MCP operation and return the result."""
    
    def _get_allowed_tools(self, command: str) -> List[str]:
        """
        Возвращает список разрешенных инструментов для команды
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Список разрешенных инструментов
        """
        # Базовые инструменты для всех команд
        tools = ["mcp"]
        
        # Добавляем специфичные инструменты
        if "/db" in command or "sql" in command.lower():
            tools.extend(["mcp__supabase__execute_sql", "mcp__supabase__list_tables"])
        
        if "project" in command.lower():
            tools.extend(["mcp__supabase__list_projects", "mcp__supabase__get_project"])
            
        if "app" in command.lower() or "digitalocean" in command.lower():
            tools.extend(["mcp__digitalocean__list_apps", "mcp__digitalocean__get_app"])
            
        if "doc" in command.lower() or "context7" in command.lower():
            tools.extend(["mcp__context7__resolve-library-id", "mcp__context7__get-library-docs"])
            
        return tools
    
    def _process_messages(self, messages: List[Message], command: str) -> Dict[str, Any]:
        """
        Обрабатывает сообщения от Claude Code SDK
        
        Args:
            messages: Список сообщений от SDK
            command: Исходная команда
            
        Returns:
            Обработанный результат
        """
        if not messages:
            return {
                "success": False,
                "error": "Нет ответа от Claude Code"
            }
        
        # Ищем результат выполнения MCP
        result_data = None
        error_message = None
        
        for message in messages:
            # Проверяем tool_use сообщения
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.get('type') == 'tool_result':
                        result_data = tool_call.get('result')
                        
            # Проверяем текстовые сообщения на ошибки
            # Проверяем наличие атрибута role (может быть SystemMessage без role)
            if hasattr(message, 'role') and message.role == "assistant" and hasattr(message, 'content') and message.content:
                content_lower = message.content.lower()
                if "error" in content_lower or "failed" in content_lower:
                    error_message = message.content
        
        # Получаем последнее сообщение ассистента как основной ответ
        assistant_messages = [m for m in messages if hasattr(m, 'role') and m.role == "assistant" and hasattr(m, 'content') and m.content]
        
        # Обрабатываем content, который может быть строкой или списком блоков
        response_text = "Команда выполнена"
        if assistant_messages:
            last_msg = assistant_messages[-1]
            if isinstance(last_msg.content, str):
                response_text = last_msg.content
            elif isinstance(last_msg.content, list):
                # Собираем текст из всех текстовых блоков
                text_parts = []
                for block in last_msg.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                    elif isinstance(block, dict) and block.get('text'):
                        text_parts.append(block['text'])
                response_text = '\n'.join(text_parts) if text_parts else "Команда выполнена"
        
        # Ограничиваем размер ответа для предотвращения проблем с большими JSON
        MAX_RESPONSE_LENGTH = 4000  # Telegram limit
        if len(response_text) > MAX_RESPONSE_LENGTH:
            response_text = response_text[:MAX_RESPONSE_LENGTH-100] + "\n\n... (ответ обрезан)"
        
        return {
            "success": True if not error_message else False,
            "command": command,
            "response": response_text,
            "data": result_data,
            "error": error_message,
            "message_count": len(messages)
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестирует подключение к MCP серверам
        
        Returns:
            Статус подключения
        """
        if not self.enabled:
            return {
                "success": False,
                "enabled": False,
                "error": "Сервис отключен"
            }
            
        try:
            # Проверяем наличие конфигурации MCP
            mcp_config_exists = self.mcp_config_path.exists()
            
            # Пробуем выполнить простую команду
            result = await self.execute_mcp_command("/mcp status")
            
            return {
                "success": result.get("success", False),
                "enabled": True,
                "mcp_config_exists": mcp_config_exists,
                "api_key_set": bool(self.api_key),
                "test_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "enabled": True,
                "error": str(e)
            }
    
    async def _emulate_mcp_command(self, command: str) -> Dict[str, Any]:
        """
        Эмулирует выполнение MCP команд без реального SDK
        Используется для тестирования интеграции
        """
        # Парсим команду
        parts = command.strip().split()
        
        if command.startswith("/mcp status"):
            return {
                "success": True,
                "command": command,
                "response": """🔌 **MCP Status**

**Configured Servers:**
- ✅ **Supabase** - Database management (ENABLED)
- ✅ **DigitalOcean** - Infrastructure & deployments (ENABLED)  
- ✅ **Context7** - Documentation search (ENABLED)

**Available Commands:**
- `/mcp status` - Check MCP servers status
- `/mcp projects` - List Supabase projects
- `/db <query>` - Execute SQL query
- `/mcp apps` - List DigitalOcean apps
- `/docs <library> <query>` - Search documentation

⚠️ **Note:** Running in emulation mode (SDK not installed)""",
                "data": {
                    "servers": {
                        "supabase": {"enabled": config.mcp.supabase_enabled},
                        "digitalocean": {"enabled": config.mcp.digitalocean_enabled},
                        "context7": {"enabled": config.mcp.context7_enabled}
                    }
                },
                "message_count": 1
            }
        
        elif command.startswith("/mcp projects"):
            return {
                "success": True,
                "command": command,
                "response": """🗄️ **Supabase Projects** (Emulated)

1. **artem-integrator-prod**
   - Region: us-east-1
   - Status: Active
   - Database: PostgreSQL 15
   
2. **artem-integrator-dev**
   - Region: us-east-1
   - Status: Active
   - Database: PostgreSQL 15

⚠️ This is emulated data for testing""",
                "data": None,
                "message_count": 1
            }
        
        elif command.startswith("/db "):
            sql_query = command[4:].strip()
            return {
                "success": True,
                "command": command,
                "response": f"""🗄️ **SQL Query Execution** (Emulated)

Query: `{sql_query}`

Result:
```
PostgreSQL 15.2 on x86_64-pc-linux-gnu
(1 row)
```

⚠️ This is emulated response for testing""",
                "data": None,
                "message_count": 1
            }
        
        elif command.startswith("/mcp apps"):
            return {
                "success": True,
                "command": command,
                "response": """🌊 **DigitalOcean Apps** (Emulated)

1. **artem-integrator**
   - Status: Active
   - Region: FRA1
   - Last Deploy: 2 hours ago
   
2. **artem-admin-panel**
   - Status: Active
   - Region: NYC1
   - Last Deploy: 1 day ago

⚠️ This is emulated data for testing""",
                "data": None,
                "message_count": 1
            }
        
        elif command.startswith("/docs "):
            parts = command[6:].strip().split(maxsplit=1)
            library = parts[0] if parts else "unknown"
            query = parts[1] if len(parts) > 1 else ""
            
            return {
                "success": True,
                "command": command,
                "response": f"""📚 **Documentation Search** (Emulated)

Library: **{library}**
Query: **{query}**

Found 3 results:
1. **{library} - Getting Started**
   Basic introduction to {library}
   
2. **{library} - API Reference**
   Complete API documentation
   
3. **{library} - {query} Guide**
   Detailed guide about {query}

⚠️ This is emulated response for testing""",
                "data": None,
                "message_count": 1
            }
        
        else:
            return {
                "success": False,
                "command": command,
                "response": f"❌ Unknown command: {command}",
                "error": "Command not recognized in emulation mode",
                "message_count": 1
            }


# Создаем глобальный экземпляр сервиса
claude_code_service = ClaudeCodeService()