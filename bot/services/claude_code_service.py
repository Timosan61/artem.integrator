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
    
    async def execute_natural_request(
        self, 
        text: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет запрос на естественном языке через Claude Code SDK
        (по аналогии с Claude Desktop)
        
        Args:
            text: Текст запроса от пользователя
            user_id: ID пользователя для логирования
            
        Returns:
            Dict с результатом выполнения
        """
        import uuid
        trace_id = str(uuid.uuid4())[:8]
        
        if not self.enabled:
            logger.warning(f"❌ [TRACE:{trace_id}] Claude Code Service отключен")
            return {
                "success": False,
                "error": "Claude Code SDK отключен"
            }
            
        if not CLAUDE_CODE_SDK_AVAILABLE:
            logger.warning(f"❌ [TRACE:{trace_id}] Claude Code SDK недоступен")
            return {
                "success": False,
                "error": "Claude Code SDK не установлен"
            }
            
        try:
            logger.info(f"🚀 [TRACE:{trace_id}] Естественный запрос: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {user_id}")
            
            # Загружаем MCP серверы
            mcp_servers = {}
            config_file = self.temp_mcp_config if self.temp_mcp_config and self.temp_mcp_config.exists() else self.mcp_config_path
            
            if config_file and config_file.exists():
                try:
                    with open(config_file) as f:
                        mcp_config = json.load(f)
                        for server_name, server_config in mcp_config.get("mcpServers", {}).items():
                            mcp_servers[server_name] = {
                                "command": server_config.get("command", ""),
                                "args": server_config.get("args", []),
                                "env": server_config.get("env", {})
                            }
                    logger.info(f"✅ [TRACE:{trace_id}] Загружено {len(mcp_servers)} MCP серверов")
                except Exception as e:
                    logger.warning(f"⚠️ [TRACE:{trace_id}] Не удалось загрузить MCP конфигурацию: {e}")
            
            # Минимальные опции для SDK - пусть сам анализирует
            options = ClaudeCodeOptions(
                max_turns=1,
                mcp_servers=mcp_servers,
                permission_mode="acceptEdits"
            )
            
            # Выполняем через SDK
            messages: List[Message] = []
            
            import time
            start_time = time.time()
            
            async for message in query(prompt=text, options=options):
                messages.append(message)
                if len(messages) > 50:  # Ограничение для безопасности
                    logger.warning(f"⚠️ [TRACE:{trace_id}] Слишком много сообщений, прерываем")
                    break
                    
            execution_time = time.time() - start_time
            logger.info(f"✅ [TRACE:{trace_id}] SDK выполнен за {execution_time:.2f}с, получено {len(messages)} сообщений")
            
            # Обрабатываем результат (используем существующую логику)
            result = self._process_messages(messages, text, trace_id)
            
            return result
            
        except Exception as e:
            logger.error(f"💥 [TRACE:{trace_id}] Ошибка выполнения естественного запроса: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    
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
        УСТАРЕВШИЙ метод - используйте execute_natural_request
        Оставлен для обратной совместимости
        """
        logger.warning(f"⚠️ execute_mcp_command устарел, используйте execute_natural_request")
        return await self.execute_natural_request(command, user_id)
    
    
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