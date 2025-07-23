"""
Claude Code Service - интеграция с Claude Code SDK для выполнения MCP команд

Этот сервис позволяет боту использовать MCP серверы через Claude Code SDK.
"""

import logging
import json
import os
import yaml
from typing import Optional, Dict, Any, List, AsyncIterator
from pathlib import Path
import asyncio
import anyio
from datetime import datetime

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
        
        # Загружаем промпты из YAML файлов
        self.voice_prompts = self._load_yaml_config("mcp_voice_prompts.yaml")
        self.sdk_prompts = self._load_yaml_config("claude_sdk_prompts.yaml")
        
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
    
    def reload_prompts(self) -> None:
        """
        Перезагружает промпты из YAML файлов
        Можно вызывать для обновления промптов без перезапуска сервиса
        """
        try:
            self.voice_prompts = self._load_yaml_config("mcp_voice_prompts.yaml")
            self.sdk_prompts = self._load_yaml_config("claude_sdk_prompts.yaml")
            logger.info("✅ Промпты успешно перезагружены")
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки промптов: {e}")
    
    def _load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """
        Загружает конфигурацию из YAML файла
        
        Args:
            filename: Имя файла в папке data
            
        Returns:
            Словарь с конфигурацией или пустой словарь при ошибке
        """
        try:
            yaml_path = Path(__file__).parent.parent.parent / "data" / filename
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning(f"⚠️ YAML файл не найден: {yaml_path}")
                return {}
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки YAML {filename}: {e}")
            return {}
        
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
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения MCP команды: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_mcp_prompt(self, command: str) -> str:
        """
        Форматирует команду в промпт для Claude Code используя YAML конфигурацию
        
        Args:
            command: Исходная команда
            
        Returns:
            Промпт для SDK
        """
        # Сначала проверяем маппинги из YAML
        if self.sdk_prompts and 'command_mappings' in self.sdk_prompts:
            mappings = self.sdk_prompts['command_mappings']
            
            # Ищем точное совпадение или префикс команды
            for cmd_pattern, cmd_config in mappings.items():
                if command.startswith(cmd_pattern):
                    # Проверяем fallback для недоступных функций
                    if 'fallback_response' in cmd_config:
                        return cmd_config['fallback_response']
                    else:
                        return cmd_config.get('prompt', f"Execute MCP command: {command}")
        
        # Fallback на старую логику
        return self._get_legacy_mcp_prompt(command)
    
    def _get_legacy_mcp_prompt(self, command: str) -> str:
        """Старая логика форматирования промптов для обратной совместимости"""
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
            
        elif command.startswith("/voice"):
            # Обработка голосовых команд
            voice_text = command[6:].strip()
            return self._format_voice_mcp_prompt(voice_text)
            
        else:
            # Общий случай
            return f"Execute MCP command: {command}"
    
    def _format_voice_mcp_prompt(self, voice_text: str) -> str:
        """
        Форматирует голосовой текст в промпт для Claude Code используя YAML конфигурацию
        
        Args:
            voice_text: Транскрибированный голосовой текст
            
        Returns:
            Промпт для SDK с инструкциями для обработки
        """
        # Используем конфигурацию из YAML или fallback на старый промпт
        if self.voice_prompts and 'voice_commands' in self.voice_prompts:
            voice_config = self.voice_prompts['voice_commands']
            system_prompt = voice_config.get('system_prompt', '')
            scenarios = voice_config.get('scenarios', [])
            default_response = voice_config.get('default_response', '')
            
            # Формируем промпт из YAML конфигурации
            prompt_parts = [system_prompt]
            prompt_parts.append(f'\nПользователь сказал: "{voice_text}"\n')
            prompt_parts.append("Определи намерение пользователя и выполни соответствующее действие:\n")
            
            for i, scenario in enumerate(scenarios, 1):
                triggers = ", ".join([f'"{t}"' for t in scenario.get('triggers', [])])
                action = scenario.get('action', '')
                fallback = scenario.get('fallback_message', '')
                
                prompt_parts.append(f"{i}. **{scenario.get('name', '')}** - триггеры: {triggers}")
                if action and not fallback:
                    prompt_parts.append(f"   - Используй {action}")
                elif fallback:
                    prompt_parts.append(f"   - Верни сообщение: {fallback}")
                prompt_parts.append("")
            
            prompt_parts.append(default_response)
            
            return "\n".join(prompt_parts)
        else:
            # Fallback на старый промпт если YAML не загружен
            return self._get_legacy_voice_prompt(voice_text)
    
    def _get_legacy_voice_prompt(self, voice_text: str) -> str:
        """Старый промпт для обратной совместимости"""
        return f"""Ты голосовой ассистент для управления инфраструктурой через естественный язык.

Пользователь сказал: "{voice_text}"

Определи намерение пользователя и выполни соответствующее действие:

1. **Если спрашивает о приложениях** (например: "посмотри мои приложения", "какие у меня приложения в DigitalOcean", "список приложений"):
   - Используй mcp__digitalocean__list_apps
   - Верни список всех приложений с названиями, ID и регионами

2. **Если спрашивает о конкретном приложении** (например: "информация о приложении sample-aspnetapp"):
   - Извлеки имя приложения из текста
   - Используй mcp__digitalocean__get_app чтобы получить детали

3. **Если спрашивает о деплойментах** (например: "посмотри деплойменты", "история развертываний"):
   - Используй mcp__digitalocean__list_deployments
   - Покажи последние деплойменты

4. **Если спрашивает о базах данных** (например: "посмотри базы данных", "какие у меня базы в DigitalOcean"):
   - Используй mcp__digitalocean__list_databases_cluster

ВАЖНО: Верни ответ в дружелюбном формате для Telegram с использованием эмодзи и понятного языка.

Примеры хороших ответов:
📁 **Ваши DigitalOcean приложения:**
📦 **sample-aspnetapp**
  🆔 ID: `6eb5ebe0-c0aa-4b98-9ee1-a4e471069702`
  🌍 Регион: ams

Если не понял запрос - вежливо попроси уточнить."""

    def _get_system_prompt(self) -> str:
        """Возвращает системный промпт для Claude Code из YAML конфигурации"""
        # Используем промпт из YAML или fallback
        if self.sdk_prompts and 'system_prompt' in self.sdk_prompts:
            return self.sdk_prompts['system_prompt']
        else:
            # Fallback на старый промпт
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

For voice commands (/voice prefix), understand natural language and execute the appropriate MCP operation.

Important: Execute the requested MCP operation and return the result."""
    
    def _get_allowed_tools(self, command: str) -> List[str]:
        """
        Возвращает список разрешенных инструментов для команды используя YAML конфигурацию
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Список разрешенных инструментов
        """
        tools = []
        
        # Сначала проверяем маппинги команд из YAML
        if self.sdk_prompts and 'command_mappings' in self.sdk_prompts:
            mappings = self.sdk_prompts['command_mappings']
            
            # Ищем подходящую команду
            for cmd_pattern, cmd_config in mappings.items():
                if command.startswith(cmd_pattern):
                    cmd_tools = cmd_config.get('tools', [])
                    tools.extend(cmd_tools)
                    break
        
        # Если не нашли в маппингах, используем allowed_tools из YAML
        if not tools and self.sdk_prompts and 'allowed_tools' in self.sdk_prompts:
            allowed = self.sdk_prompts['allowed_tools']
            
            # Определяем какой сервер использовать по ключевым словам
            if any(word in command.lower() for word in ['app', 'deploy', 'droplet', 'database', 'digitalocean', 'do']):
                # Добавляем все инструменты DigitalOcean
                for category in allowed.get('digitalocean', {}).values():
                    if isinstance(category, list):
                        tools.extend(category)
            
            if any(word in command.lower() for word in ['project', 'supabase', 'sql', 'db']):
                # Добавляем инструменты Supabase
                for category in allowed.get('supabase', {}).values():
                    if isinstance(category, list):
                        tools.extend(category)
            
            if any(word in command.lower() for word in ['doc', 'context7', 'library']):
                # Добавляем инструменты Context7
                for category in allowed.get('context7', {}).values():
                    if isinstance(category, list):
                        tools.extend(category)
        
        # Fallback на старую логику если YAML не помог
        if not tools:
            return self._get_legacy_allowed_tools(command)
            
        return list(set(tools))  # Убираем дубликаты
    
    def _get_legacy_allowed_tools(self, command: str) -> List[str]:
        """Старая логика определения инструментов для обратной совместимости"""
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
        mcp_result_text = None
        
        for message in messages:
            # Проверяем tool_result в UserMessage
            if hasattr(message, 'content') and isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict) and item.get('type') == 'tool_result':
                        content = item.get('content', '')
                        logger.debug(f"🔧 Tool result: content='{content[:100]}...', is_error={item.get('is_error')}")
                        
                        if item.get('is_error'):
                            # Особый случай для "No apps found" - это не ошибка
                            if "No apps found" in content:
                                mcp_result_text = "📁 **DigitalOcean Apps**\n\nℹ️ Нет приложений в вашем аккаунте DigitalOcean."
                                logger.debug(f"🎯 Установлен mcp_result_text: {mcp_result_text}")
                            else:
                                error_message = content
                        else:
                            result_data = content
                            logger.debug(f"🔧 Processing result_data: {type(content)} - {content}")
                            
                            if isinstance(content, list) and content:
                                # Обработка списка результатов от MCP
                                for item in content:
                                    if isinstance(item, dict) and item.get('type') == 'text' and item.get('text'):
                                        text_content = item['text']
                                        logger.debug(f"🔧 Processing text content: {text_content}")
                                        
                                        # Парсим текстовый формат
                                        lines = text_content.strip().split('\n')
                                        apps_list = []
                                        
                                        for line in lines:
                                            line = line.strip()
                                            if line and 'App ID:' in line and 'Name:' in line:
                                                # Формат: "App ID: 6eb5ebe0-c0aa-4b98-9ee1-a4e471069702 Name: sample-aspnetapp Region: ams"
                                                try:
                                                    # Ищем ключевые слова
                                                    app_id = None
                                                    name = None
                                                    region = None
                                                    
                                                    if 'App ID:' in line:
                                                        app_id_part = line.split('App ID:')[1].split('Name:')[0].strip()
                                                        app_id = app_id_part.strip()
                                                    if 'Name:' in line:
                                                        name_part = line.split('Name:')[1].split('Region:')[0].strip()
                                                        name = name_part.strip()
                                                    if 'Region:' in line:
                                                        region_part = line.split('Region:')[1].strip()
                                                        region = region_part.strip()
                                                    
                                                    if app_id and name:
                                                        apps_list.append({
                                                            'id': app_id,
                                                            'name': name,
                                                            'region': region or 'N/A'
                                                        })
                                                except Exception as e:
                                                    logger.debug(f"⚠️ Ошибка парсинга строки '{line}': {e}")
                                        
                                        if apps_list:
                                            mcp_result_text = "📁 **DigitalOcean Apps**\n\n"
                                            for app in apps_list:
                                                mcp_result_text += f"📦 **{app['name']}**\n"
                                                mcp_result_text += f"  🆔 ID: `{app['id']}`\n"
                                                mcp_result_text += f"  🌍 Регион: {app['region']}\n\n"
                                            logger.debug(f"✅ Сформирован результат: {mcp_result_text[:100]}...")
                                        elif "No apps found" in text_content:
                                            mcp_result_text = "📁 **DigitalOcean Apps**\n\nℹ️ Нет приложений в вашем аккаунте DigitalOcean."
                                        else:
                                            mcp_result_text = text_content
                                        
                                        break  # Используем первый элемент
                            elif isinstance(content, str) and content:
                                # Обрабатываем текстовый ответ напрямую
                                lines = content.strip().split('\n')
                                apps_list = []
                                
                                # Парсим текстовый формат
                                current_app = {}
                                for line in lines:
                                    line = line.strip()
                                    if line.startswith('App ID:') and 'Name:' in line:
                                        # Формат: "App ID: 6eb5ebe0-c0aa-4b98-9ee1-a4e471069702 Name: sample-aspnetapp Region: ams"
                                        parts = line.split()
                                        if len(parts) >= 6:
                                            app_id = parts[2] if len(parts) > 2 else 'N/A'
                                            name = parts[4] if len(parts) > 4 else 'Unknown'
                                            region = parts[6] if len(parts) > 6 else 'N/A'
                                            apps_list.append({
                                                'id': app_id,
                                                'name': name,
                                                'region': region
                                            })
                                
                                if apps_list:
                                    mcp_result_text = "📁 **DigitalOcean Apps**\n\n"
                                    for app in apps_list:
                                        mcp_result_text += f"📦 **{app['name']}**\n"
                                        mcp_result_text += f"  🆔 ID: `{app['id']}`\n"
                                        mcp_result_text += f"  🌍 Регион: {app['region']}\n\n"
                                else:
                                    # Если нет приложений
                                    if "No apps found" in content or "нет приложений" in content.lower():
                                        mcp_result_text = "📁 **DigitalOcean Apps**\n\nℹ️ Нет приложений в вашем аккаунте DigitalOcean."
                                    else:
                                        # Используем оригинальный текст
                                        mcp_result_text = content
                        
            # Проверяем текстовые сообщения на ошибки
            # Проверяем наличие атрибута role (может быть SystemMessage без role)
            if hasattr(message, 'role') and message.role == "assistant" and hasattr(message, 'content') and message.content:
                content_lower = message.content.lower()
                if "error" in content_lower or "failed" in content_lower:
                    error_message = message.content
        
        # Получаем последнее сообщение ассистента как основной ответ
        assistant_messages = [m for m in messages if hasattr(m, 'role') and m.role == "assistant" and hasattr(m, 'content') and m.content]
        
        # Обрабатываем content, который может быть строкой или списком блоков
        response_text = None
        
        # Если есть результат MCP, используем его
        if mcp_result_text:
            logger.debug(f"🎯 Используем MCP результат: {mcp_result_text[:100]}...")
            response_text = mcp_result_text
        elif assistant_messages:
            last_msg = assistant_messages[-1]
            if isinstance(last_msg.content, str) and last_msg.content.strip():
                response_text = last_msg.content.strip()
            elif isinstance(last_msg.content, list):
                # Собираем текст из всех текстовых блоков
                text_parts = []
                for block in last_msg.content:
                    if hasattr(block, 'text') and block.text:
                        text_parts.append(block.text)
                    elif isinstance(block, dict) and block.get('text'):
                        text_parts.append(block['text'])
                response_text = '\n'.join(text_parts) if text_parts else None
        
        # Если ничего не найдено, используем стандартное сообщение
        if not response_text:
            response_text = "Команда выполнена"
        
        # Ограничиваем размер ответа для предотвращения проблем с большими JSON
        MAX_RESPONSE_LENGTH = 4000  # Telegram limit
        if len(response_text) > MAX_RESPONSE_LENGTH:
            response_text = response_text[:MAX_RESPONSE_LENGTH-100] + "\n\n... (ответ обрезан)"
        
        # Определяем успешность - если есть mcp_result_text, это успех
        success = bool(mcp_result_text) or (not error_message)
        
        # Используем response_text как финальный ответ
        logger.debug(f"📊 Final response: {response_text[:200]}...")
        
        return {
            "success": success,
            "command": command,
            "response": response_text,
            "data": result_data,
            "error": error_message if not response_text or response_text == "Команда выполнена" else None,
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