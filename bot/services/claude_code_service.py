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
        
        # Создаем временный файл конфигурации с подставленными переменными
        self.temp_mcp_config = self._create_mcp_config_with_env_vars()
        
        # Упрощенная инициализация - больше не используем YAML промпты
        
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
        Заглушка для совместимости - промпты больше не используются
        """
        logger.info("ℹ️ Перезагрузка промптов не требуется в упрощенной версии")
    
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
    
    def _create_mcp_config_with_env_vars(self) -> Optional[Path]:
        """
        Создает временный файл конфигурации MCP с подставленными переменными окружения
        
        Returns:
            Путь к временному файлу конфигурации или None при ошибке
        """
        try:
            if not self.mcp_config_path.exists():
                logger.warning(f"⚠️ Файл конфигурации MCP не найден: {self.mcp_config_path}")
                return None
                
            # Загружаем шаблон конфигурации
            with open(self.mcp_config_path, 'r', encoding='utf-8') as f:
                config_template = f.read()
            
            # Подставляем переменные окружения
            config_content = self._substitute_env_variables(config_template)
            
            # Создаем временный файл
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                prefix='mcp-config-', 
                delete=False,
                encoding='utf-8'
            )
            temp_file.write(config_content)
            temp_file.flush()
            temp_file.close()
            
            temp_path = Path(temp_file.name)
            logger.info(f"✅ Создан временный файл конфигурации MCP: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания временного файла конфигурации MCP: {e}")
            return None
    
    def _substitute_env_variables(self, template: str) -> str:
        """
        Подставляет переменные окружения в шаблон конфигурации
        
        Args:
            template: Шаблон с переменными вида {VARIABLE_NAME}
            
        Returns:
            Строка с подставленными значениями
        """
        import re
        
        # Маппинг переменных из .env
        env_mapping = {
            'DIGITALOCEAN_TOKEN': os.getenv('DIGITALOCEAN_TOKEN', ''),
            'SUPABASE_URL': os.getenv('SUPABASE_URL', ''),
            'SUPABASE_KEY': os.getenv('SUPABASE_KEY', ''),
            'CONTEXT7_API_KEY': os.getenv('CONTEXT7_API_KEY', ''),
        }
        
        # Подставляем переменные
        result = template
        for var_name, var_value in env_mapping.items():
            pattern = f"{{{var_name}}}"
            result = result.replace(pattern, var_value)
            
        # Удаляем серверы с пустыми токенами
        try:
            import json
            config_dict = json.loads(result)
            filtered_servers = {}
            
            for server_name, server_config in config_dict.get("mcpServers", {}).items():
                env_vars = server_config.get("env", {})
                # Проверяем, есть ли хотя бы одна заполненная переменная окружения
                has_valid_env = any(value.strip() for value in env_vars.values()) if env_vars else True
                
                if has_valid_env:
                    filtered_servers[server_name] = server_config
                else:
                    logger.info(f"⚠️ Пропускаем сервер {server_name} - отсутствуют переменные окружения")
            
            config_dict["mcpServers"] = filtered_servers
            result = json.dumps(config_dict, indent=2)
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отфильтровать серверы: {e}")
            
        return result
        
    async def execute_mcp_command(
        self, 
        command: str, 
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет MCP команду через Claude Code SDK
        
        Args:
            command: Команда для выполнения (например: "/mcp status")
            user_id: ID пользователя для логирования
            trace_id: ID трассировки для логирования
            
        Returns:
            Dict с результатом выполнения
        """
        if not trace_id:
            import uuid
            trace_id = str(uuid.uuid4())[:8]
            
        if not self.enabled:
            logger.warning(f"❌ [TRACE:{trace_id}] MCP Service отключен")
            return {
                "success": False,
                "error": "MCP сервис отключен"
            }
            
        try:
            logger.info(f"🔧 [TRACE:{trace_id}] Claude Code Service: начинаем выполнение MCP команды")
            logger.info(f"📝 [TRACE:{trace_id}] Команда: '{command}'")
            logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {user_id}")
            logger.info(f"⚙️ [TRACE:{trace_id}] SDK доступен: {CLAUDE_CODE_SDK_AVAILABLE}")
            
            # Анализируем тип команды
            command_type = self._analyze_command_type(command, trace_id)
            logger.info(f"🎯 [TRACE:{trace_id}] Тип команды: {command_type}")
            
            # Формируем промпт для Claude Code
            logger.info(f"📋 [TRACE:{trace_id}] Этап 1: Подготовка промпта...")
            prompt = self._format_mcp_prompt(command, trace_id)
            
            # Опции для SDK
            if CLAUDE_CODE_SDK_AVAILABLE:
                logger.info(f"📂 [TRACE:{trace_id}] Этап 2: Загрузка конфигурации MCP серверов...")
                
                # Загружаем конфигурацию MCP серверов из временного файла
                mcp_servers = {}
                config_file = self.temp_mcp_config if self.temp_mcp_config and self.temp_mcp_config.exists() else self.mcp_config_path
                
                logger.info(f"📄 [TRACE:{trace_id}] Файл конфигурации: {config_file}")
                
                if config_file and config_file.exists():
                    try:
                        with open(config_file) as f:
                            mcp_config = json.load(f)
                            # Преобразуем конфигурацию в формат SDK
                            for server_name, server_config in mcp_config.get("mcpServers", {}).items():
                                mcp_servers[server_name] = {
                                    "command": server_config.get("command", ""),
                                    "args": server_config.get("args", []),
                                    "env": server_config.get("env", {})
                                }
                                logger.debug(f"🔧 [TRACE:{trace_id}] Сервер {server_name}: {server_config.get('command', 'N/A')}")
                                
                        logger.info(f"✅ [TRACE:{trace_id}] Загружено {len(mcp_servers)} MCP серверов")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ [TRACE:{trace_id}] Не удалось загрузить MCP конфигурацию: {e}")
                else:
                    logger.warning(f"⚠️ [TRACE:{trace_id}] Файл конфигурации MCP не найден")
                
                # Добавляем более явные инструкции для MCP
                logger.info(f"🎯 [TRACE:{trace_id}] Этап 3: Определение системного промпта...")
                system_prompt = self._get_system_prompt()
                command_lower = command.lower()
                
                # Распознаем запросы о приложениях (русский и английский)
                if any(word in command_lower for word in ["apps", "приложен", "digitalocean"]):
                    logger.info(f"📱 [TRACE:{trace_id}] Обнаружен запрос о DigitalOcean приложениях")
                    system_prompt = f"""Execute user command: {command}

IMPORTANT: Call mcp__digitalocean__list_apps with parameter {{"query": {{}}}} immediately.

DO NOT:
- Use TodoWrite or any todo management tools
- Use Task tool
- Plan or organize tasks
- Use any Cloudflare functions

JUST execute mcp__digitalocean__list_apps directly and return the results.

USE ONLY THESE FUNCTIONS. NO EXCEPTIONS."""
                
                # Распознаем запросы о MCP серверах
                elif any(word in command_lower for word in ["mcp сервер", "list servers", "серверов", "какие серверы", "список серверов"]):
                    logger.info(f"🔌 [TRACE:{trace_id}] Обнаружен запрос о MCP серверах")
                    system_prompt = f"""Execute user command: {command}

User wants to know about available MCP servers. Show them what MCP servers are configured and available.

IMPORTANT: You can use mcp__digitalocean__list_apps to show DigitalOcean capabilities as an example of MCP servers working.

Explain that MCP servers provide access to:
- DigitalOcean (apps, databases, deployments)
- Context7 (documentation)
- Other configured servers

DO NOT use TodoWrite or Task tools. Just provide information about MCP servers."""
                
                # Определяем разрешенные инструменты на основе команды
                logger.info(f"🛠️ [TRACE:{trace_id}] Этап 4: Определение разрешенных инструментов...")
                allowed_tools = []
                
                # Запросы о приложениях
                if any(word in command_lower for word in ["apps", "приложен", "digitalocean"]):
                    logger.info(f"📱 [TRACE:{trace_id}] Используем DigitalOcean инструменты для приложений")
                    # Только DigitalOcean инструменты
                    allowed_tools = [
                        "mcp__digitalocean__list_apps", 
                        "mcp__digitalocean__get_app", 
                        "mcp__digitalocean__create_app", 
                        "mcp__digitalocean__list_deployments",
                        "mcp__digitalocean__get_deployment",
                        "mcp__digitalocean__list_databases_cluster"
                    ]
                
                # Запросы о MCP серверах
                elif any(word in command_lower for word in ["mcp сервер", "list servers", "серверов", "какие серверы", "список серверов"]):
                    logger.info(f"🔌 [TRACE:{trace_id}] Используем DigitalOcean для демонстрации MCP серверов")
                    # Разрешаем DigitalOcean для демонстрации работы MCP
                    allowed_tools = [
                        "mcp__digitalocean__list_apps"
                    ]
                elif "project" in command.lower() or "supabase" in command.lower() or "/db" in command:
                    logger.info(f"🗄️ [TRACE:{trace_id}] Используем Supabase инструменты для проектов/БД")
                    # Только Supabase инструменты
                    allowed_tools = [
                        "mcp__supabase__list_projects", 
                        "mcp__supabase__get_project",
                        "mcp__supabase__execute_sql", 
                        "mcp__supabase__list_tables",
                        "mcp__supabase__list_organizations"
                    ]
                elif "doc" in command.lower() or "context7" in command.lower():
                    logger.info(f"📚 [TRACE:{trace_id}] Используем Context7 инструменты для документации")
                    # Только Context7 инструменты
                    allowed_tools = [
                        "mcp__context7__resolve-library-id", 
                        "mcp__context7__get-library-docs"
                    ]
                else:
                    logger.info(f"❓ [TRACE:{trace_id}] Неопределенная команда, используем стандартный набор")
                    # Если не уверены - используем стандартный набор
                    allowed_tools = self._get_allowed_tools(command)
                
                # Список запрещенных инструментов (все Cloudflare функции)
                logger.info(f"🚫 [TRACE:{trace_id}] Этап 5: Настройка запрещенных инструментов...")
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
                    logger.info(f"📱 [TRACE:{trace_id}] Специальные ограничения для команды apps")
                    # Для команды apps разрешаем ТОЛЬКО list_apps
                    allowed_tools = ["mcp__digitalocean__list_apps"]
                    disallowed_tools.extend(task_management_tools)
                
                logger.info(f"✅ [TRACE:{trace_id}] Разрешенные инструменты ({len(allowed_tools)}): {allowed_tools}")
                logger.info(f"❌ [TRACE:{trace_id}] Запрещенные инструменты ({len(disallowed_tools)}): {disallowed_tools[:3]}...")
                
                logger.info(f"🔧 [TRACE:{trace_id}] Этап 6: Создание опций для Claude Code SDK...")
                options = ClaudeCodeOptions(
                    max_turns=1,  # Одна итерация для команды
                    system_prompt=system_prompt,
                    cwd=Path.cwd(),
                    allowed_tools=allowed_tools,  # Ограничиваем доступные инструменты
                    disallowed_tools=disallowed_tools,  # Блокируем Cloudflare и task management
                    mcp_servers=mcp_servers,  # Передаем конфигурацию серверов
                    permission_mode="acceptEdits"  # Автоматически принимаем использование инструментов
                )
                logger.info(f"✅ [TRACE:{trace_id}] Опции SDK созданы успешно")
            else:
                options = None
            
            # Используем реальный SDK если доступен
            if CLAUDE_CODE_SDK_AVAILABLE:
                try:
                    logger.info(f"🚀 [TRACE:{trace_id}] Этап 7: Выполнение через реальный Claude Code SDK...")
                    logger.info(f"📝 [TRACE:{trace_id}] Промпт: '{prompt[:100]}{'...' if len(prompt) > 100 else ''}'")
                    
                    # Используем настоящий SDK
                    messages: List[Message] = []
                    
                    import time
                    start_time = time.time()
                    
                    try:
                        logger.info(f"🔄 [TRACE:{trace_id}] Начинаем потоковое получение сообщений от SDK...")
                        
                        async for message in query(prompt=prompt, options=options):
                            messages.append(message)
                            # Безопасный вывод для отладки
                            msg_type = type(message).__name__
                            msg_role = getattr(message, 'role', 'No role')
                            msg_content = str(getattr(message, 'content', ''))[:100] if hasattr(message, 'content') else 'No content'
                            logger.debug(f"📨 [TRACE:{trace_id}] Получено сообщение #{len(messages)}: {msg_type} - {msg_role} - {msg_content}...")
                            
                            # Ограничиваем количество сообщений для предотвращения переполнения
                            if len(messages) > 50:
                                logger.warning(f"⚠️ [TRACE:{trace_id}] Слишком много сообщений от SDK ({len(messages)}), прерываем")
                                break
                                
                        execution_time = time.time() - start_time
                        logger.info(f"✅ [TRACE:{trace_id}] SDK выполнение завершено за {execution_time:.2f}с")
                        logger.info(f"📊 [TRACE:{trace_id}] Получено {len(messages)} сообщений от SDK")
                                
                    except json.JSONDecodeError as e:
                        execution_time = time.time() - start_time
                        logger.error(f"❌ [TRACE:{trace_id}] Ошибка декодирования JSON от SDK за {execution_time:.2f}с: {e}")
                        logger.warning(f"⚠️ [TRACE:{trace_id}] Используем частичный результат ({len(messages)} сообщений)")
                        # Продолжаем с тем, что успели получить
                    
                    # Обрабатываем результат
                    logger.info(f"🔄 [TRACE:{trace_id}] Этап 8: Обработка полученных сообщений...")
                    result = self._process_messages(messages, command, trace_id)
                    
                except Exception as sdk_error:
                    logger.error(f"💥 [TRACE:{trace_id}] Критическая ошибка SDK: {sdk_error}", exc_info=True)
                    # Больше не переключаемся на эмуляцию - возвращаем ошибку
                    result = {
                        "success": False,
                        "command": command,
                        "error": f"Ошибка выполнения MCP: {str(sdk_error)}"
                    }
            else:
                # SDK недоступен - возвращаем ошибку
                logger.error(f"❌ [TRACE:{trace_id}] Claude Code SDK недоступен")
                result = {
                    "success": False,
                    "command": command,
                    "error": "Claude Code SDK не установлен или недоступен"
                }
            
            logger.info(f"📊 [TRACE:{trace_id}] Этап 9: Финальный результат обработки")
            logger.info(f"✅ [TRACE:{trace_id}] Success: {result.get('success', False)}")
            
            if result.get('success'):
                response_len = len(result.get('response', ''))
                logger.info(f"📝 [TRACE:{trace_id}] Длина ответа: {response_len} символов")
            else:
                logger.warning(f"❌ [TRACE:{trace_id}] Ошибка: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 [TRACE:{trace_id}] Критическая ошибка выполнения MCP команды: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_command_type(self, command: str, trace_id: str = None) -> str:
        """Анализирует тип команды для логирования"""
        if not trace_id:
            trace_id = "no-trace"
            
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["apps", "приложен", "digitalocean"]):
            return "DIGITALOCEAN_APPS (список приложений)"
        elif any(word in command_lower for word in ["mcp сервер", "list servers", "серверов"]):
            return "MCP_SERVERS (информация о серверах)"
        elif any(word in command_lower for word in ["project", "supabase", "/db"]):
            return "SUPABASE_DB (работа с базой данных)"
        elif any(word in command_lower for word in ["doc", "context7"]):
            return "CONTEXT7_DOCS (поиск документации)"
        elif command.startswith("/voice"):
            return "VOICE_COMMAND (голосовая команда)"
        else:
            return "GENERAL_MCP (общая MCP команда)"

    def _format_mcp_prompt(self, command: str, trace_id: str = None) -> str:
        """
        Упрощенное форматирование команды в промпт для Claude Code
        
        Args:
            command: Исходная команда
            trace_id: ID трассировки
            
        Returns:
            Простой промпт для SDK
        """
        if not trace_id:
            trace_id = "no-trace"
            
        logger.info(f"📝 [TRACE:{trace_id}] Форматирование промпта для команды: '{command}'")
        
        # Упрощенная обработка - просто передаем команду напрямую
        prompt = self._get_simple_mcp_prompt(command)
        
        logger.debug(f"📋 [TRACE:{trace_id}] Сгенерированный промпт: '{prompt[:200]}{'...' if len(prompt) > 200 else ''}'")
        
        return prompt
    
    def _get_simple_mcp_prompt(self, command: str) -> str:
        """Упрощенный промпт без сложной логики"""
        # Проверяем основные типы команд
        if command.startswith("/voice"):
            # Убираем префикс /voice и обрабатываем как обычный запрос
            voice_text = command[6:].strip()
            return f"Пользователь сказал: '{voice_text}'. Определи что он хочет и выполни соответствующее MCP действие."
        
        elif command.startswith("/mcp apps") or "приложен" in command.lower():
            return "List all DigitalOcean apps using mcp__digitalocean__list_apps function."
        
        elif command.startswith("/mcp status") or "mcp сервер" in command.lower() or "сервер" in command.lower():
            return "Show status of available MCP servers and list their capabilities."
        
        elif command.startswith("/mcp projects") or "проект" in command.lower():
            return "List all Supabase projects using MCP."
        
        elif command.startswith("/db "):
            sql_query = command[4:].strip()
            return f"Execute SQL query using Supabase MCP: {sql_query}"
        
        else:
            # Общий случай - пусть SDK сам разбирается
            return f"Execute MCP command: {command}"
    
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
            # Обработка голосовых команд - теперь упрощенно
            voice_text = command[6:].strip()
            return f"Пользователь сказал: '{voice_text}'. Определи что он хочет и выполни соответствующее MCP действие."
            
        else:
            # Общий случай
            return f"Execute MCP command: {command}"
    
    
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
        """Упрощенный системный промпт для Claude Code"""
        return """You are a simple MCP assistant. Execute MCP commands directly.

Available MCP servers:
- DigitalOcean: mcp__digitalocean__list_apps, mcp__digitalocean__get_app
- Supabase: mcp__supabase__list_projects, mcp__supabase__execute_sql  
- Context7: mcp__context7__get-library-docs

Rules:
1. For apps/applications → use DigitalOcean functions
2. For databases/projects → use Supabase functions  
3. For docs/documentation → use Context7 functions
4. Return results clearly and concisely

Execute the requested operation and return the result."""
    
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
    
    def _process_messages(self, messages: List[Message], command: str, trace_id: str = None) -> Dict[str, Any]:
        """
        Обрабатывает сообщения от Claude Code SDK
        
        Args:
            messages: Список сообщений от SDK
            command: Исходная команда
            trace_id: ID трассировки
            
        Returns:
            Обработанный результат
        """
        if not trace_id:
            trace_id = "no-trace"
            
        logger.info(f"🔄 [TRACE:{trace_id}] Обработка {len(messages)} сообщений от SDK")
        
        if not messages:
            logger.warning(f"❌ [TRACE:{trace_id}] Нет сообщений от Claude Code SDK")
            return {
                "success": False,
                "error": "Нет ответа от Claude Code"
            }
        
        # Ищем результат выполнения MCP
        logger.info(f"🔍 [TRACE:{trace_id}] Анализ сообщений для извлечения MCP результатов...")
        
        result_data = None
        error_message = None
        mcp_result_text = None
        
        for i, message in enumerate(messages):
            logger.debug(f"📨 [TRACE:{trace_id}] Обрабатываем сообщение #{i+1}: {type(message).__name__}")
            # Проверяем tool_result в UserMessage
            if hasattr(message, 'content') and isinstance(message.content, list):
                for item in message.content:
                    if isinstance(item, dict) and item.get('type') == 'tool_result':
                        content = item.get('content', '')
                        logger.debug(f"🔧 [TRACE:{trace_id}] Tool result найден: content_type={type(content)}, is_error={item.get('is_error')}")
                        logger.debug(f"📄 [TRACE:{trace_id}] Tool result content: '{str(content)[:200]}{'...' if len(str(content)) > 200 else ''}'")
                        
                        if item.get('is_error'):
                            # Особый случай для "No apps found" - это не ошибка
                            if "No apps found" in content:
                                mcp_result_text = "📁 **DigitalOcean Apps**\n\nℹ️ Нет приложений в вашем аккаунте DigitalOcean."
                                logger.info(f"📱 [TRACE:{trace_id}] Обработан случай 'No apps found': {mcp_result_text}")
                            else:
                                error_message = content
                                logger.warning(f"❌ [TRACE:{trace_id}] Обнаружена ошибка в tool_result: {error_message}")
                        else:
                            result_data = content
                            logger.info(f"✅ [TRACE:{trace_id}] Получены данные от MCP: тип={type(content)}, размер={len(str(content))}")
                            logger.debug(f"🔧 [TRACE:{trace_id}] Processing result_data: {type(content)} - {str(content)[:100]}...")
                            
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
        
        logger.info(f"📊 [TRACE:{trace_id}] Финальная обработка результата:")
        logger.info(f"✅ [TRACE:{trace_id}] Success: {success}")
        logger.info(f"📝 [TRACE:{trace_id}] Response text: {len(response_text)} символов")
        logger.info(f"📦 [TRACE:{trace_id}] Result data: {bool(result_data)}")
        logger.info(f"❌ [TRACE:{trace_id}] Error message: {bool(error_message)}")
        
        # Используем response_text как финальный ответ
        logger.debug(f"📊 [TRACE:{trace_id}] Final response: {response_text[:200]}...")
        
        final_result = {
            "success": success,
            "command": command,
            "response": response_text,
            "data": result_data,
            "error": error_message if not response_text or response_text == "Команда выполнена" else None,
            "message_count": len(messages)
        }
        
        logger.info(f"🎯 [TRACE:{trace_id}] Результат обработки SDK сообщений завершен")
        
        return final_result
    
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
    
    def __del__(self):
        """Очищаем временные файлы при удалении экземпляра"""
        self._cleanup_temp_files()
    
    def _cleanup_temp_files(self):
        """Удаляет временные файлы конфигурации"""
        try:
            if hasattr(self, 'temp_mcp_config') and self.temp_mcp_config and self.temp_mcp_config.exists():
                self.temp_mcp_config.unlink()
                logger.info(f"🧹 Удален временный файл: {self.temp_mcp_config}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить временный файл: {e}")


# Создаем глобальный экземпляр сервиса
claude_code_service = ClaudeCodeService()