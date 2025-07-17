"""
MCP Agent - Агент для работы с Model Context Protocol серверами

Этот модуль предоставляет интеграцию с MCP серверами (Supabase, DigitalOcean, Context7)
через OpenAI Function Calling или Anthropic Claude для администраторов системы.

Основные возможности:
- Динамическая генерация функций из MCP конфигурации
- Маршрутизация запросов к соответствующим MCP серверам
- Fallback на обычный AI agent при недоступности MCP
- Интеграция с системой авторизации
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import openai
from anthropic import AsyncAnthropic

from .agent import myassistant
from .config import OPENAI_API_KEY, OPENAI_MODEL, ANTHROPIC_API_KEY, MCP_ENABLED
from .auth import get_user_mode, is_admin

logger = logging.getLogger(__name__)


@dataclass
class MCPFunction:
    """Описание функции MCP для OpenAI/Claude"""
    name: str
    description: str
    parameters: Dict[str, Any]
    server: str
    permissions: List[str]


class MCPAgent(myassistant):
    """
    Расширенный агент с поддержкой MCP серверов
    
    Наследует функциональность базового агента и добавляет:
    - Работу с MCP серверами через Function Calling
    - Динамическую генерацию доступных функций
    - Интеллектуальную маршрутизацию запросов
    """
    
    def __init__(self):
        """Инициализация MCP агента"""
        super().__init__()
        
        # Проверяем доступность MCP
        self.mcp_enabled = MCP_ENABLED and bool(OPENAI_API_KEY or ANTHROPIC_API_KEY)
        
        # Инициализация клиентов
        self.anthropic_client = None
        if ANTHROPIC_API_KEY and self.mcp_enabled:
            try:
                self.anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
                logger.info("✅ Anthropic клиент инициализирован для MCP")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Anthropic: {e}")
        
        # Загрузка MCP конфигурации
        self.mcp_config = self._load_mcp_config()
        self.mcp_functions = self._generate_mcp_functions()
        
        # MCP Manager будет инициализирован отдельно
        self.mcp_manager = None
        
        logger.info(f"🤖 MCP Agent инициализирован. MCP включен: {self.mcp_enabled}")
        logger.info(f"📊 Загружено MCP функций: {len(self.mcp_functions)}")
    
    def _load_mcp_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию MCP серверов"""
        try:
            with open('data/mcp_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("✅ MCP конфигурация загружена")
                return config
        except FileNotFoundError:
            logger.warning("⚠️ MCP конфигурация не найдена, используем стандартную")
            return self._get_default_mcp_config()
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки MCP конфигурации: {e}")
            return self._get_default_mcp_config()
    
    def _get_default_mcp_config(self) -> Dict[str, Any]:
        """Возвращает стандартную конфигурацию MCP"""
        return {
            "mcp_enabled": True,
            "servers": {
                "supabase": {
                    "enabled": False,
                    "display_name": "Supabase База данных",
                    "description": "Управление базами данных и проектами Supabase",
                    "functions": []
                },
                "digitalocean": {
                    "enabled": False,
                    "display_name": "DigitalOcean Инфраструктура",
                    "description": "Управление приложениями и инфраструктурой DigitalOcean",
                    "functions": []
                },
                "context7": {
                    "enabled": False,
                    "display_name": "Context7 Документация",
                    "description": "Поиск документации и примеров кода",
                    "functions": []
                }
            },
            "agent_instruction": "Ты помощник с доступом к MCP серверам. Используй доступные функции для выполнения задач администратора.",
            "last_updated": datetime.now().isoformat()
        }
    
    def _generate_mcp_functions(self) -> List[MCPFunction]:
        """
        Генерирует список доступных MCP функций из конфигурации
        
        Returns:
            List[MCPFunction]: Список функций для Function Calling
        """
        functions = []
        
        if not self.mcp_config.get("mcp_enabled", False):
            return functions
        
        servers = self.mcp_config.get("servers", {})
        
        # Генерация функций для каждого активного сервера
        for server_name, server_config in servers.items():
            if not server_config.get("enabled", False):
                continue
            
            # Базовые функции для каждого MCP сервера
            if server_name == "supabase":
                functions.extend(self._generate_supabase_functions())
            elif server_name == "digitalocean":
                functions.extend(self._generate_digitalocean_functions())
            elif server_name == "context7":
                functions.extend(self._generate_context7_functions())
        
        return functions
    
    def _generate_supabase_functions(self) -> List[MCPFunction]:
        """Генерирует функции для Supabase"""
        return [
            MCPFunction(
                name="supabase_list_projects",
                description="Получить список всех проектов Supabase",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                server="supabase",
                permissions=["read"]
            ),
            MCPFunction(
                name="supabase_execute_sql",
                description="Выполнить SQL запрос в базе данных Supabase",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID проекта Supabase"
                        },
                        "query": {
                            "type": "string",
                            "description": "SQL запрос для выполнения"
                        }
                    },
                    "required": ["project_id", "query"]
                },
                server="supabase",
                permissions=["read", "write"]
            ),
            MCPFunction(
                name="supabase_create_project",
                description="Создать новый проект Supabase",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Название проекта"
                        },
                        "organization_id": {
                            "type": "string",
                            "description": "ID организации"
                        },
                        "region": {
                            "type": "string",
                            "description": "Регион для размещения",
                            "enum": ["us-east-1", "us-west-1", "eu-west-1", "ap-southeast-1"]
                        }
                    },
                    "required": ["name", "organization_id"]
                },
                server="supabase",
                permissions=["admin"]
            )
        ]
    
    def _generate_digitalocean_functions(self) -> List[MCPFunction]:
        """Генерирует функции для DigitalOcean"""
        return [
            MCPFunction(
                name="digitalocean_list_apps",
                description="Получить список всех приложений в DigitalOcean",
                parameters={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "number",
                            "description": "Номер страницы"
                        },
                        "per_page": {
                            "type": "number",
                            "description": "Количество на странице"
                        }
                    },
                    "required": []
                },
                server="digitalocean",
                permissions=["read"]
            ),
            MCPFunction(
                name="digitalocean_get_app_logs",
                description="Получить логи приложения DigitalOcean",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_id": {
                            "type": "string",
                            "description": "ID приложения"
                        },
                        "deployment_id": {
                            "type": "string",
                            "description": "ID деплоя (опционально)"
                        },
                        "type": {
                            "type": "string",
                            "description": "Тип логов",
                            "enum": ["BUILD", "DEPLOY", "RUN"]
                        }
                    },
                    "required": ["app_id", "type"]
                },
                server="digitalocean",
                permissions=["read"]
            ),
            MCPFunction(
                name="digitalocean_deploy_app",
                description="Запустить новый деплой приложения",
                parameters={
                    "type": "object",
                    "properties": {
                        "app_id": {
                            "type": "string",
                            "description": "ID приложения"
                        },
                        "force_build": {
                            "type": "boolean",
                            "description": "Принудительная пересборка"
                        }
                    },
                    "required": ["app_id"]
                },
                server="digitalocean",
                permissions=["deploy"]
            )
        ]
    
    def _generate_context7_functions(self) -> List[MCPFunction]:
        """Генерирует функции для Context7"""
        return [
            MCPFunction(
                name="context7_search_docs",
                description="Поиск в документации библиотек и фреймворков",
                parameters={
                    "type": "object",
                    "properties": {
                        "library_name": {
                            "type": "string",
                            "description": "Название библиотеки (например, 'react', 'vue', 'django')"
                        },
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Максимальное количество результатов",
                            "default": 5
                        }
                    },
                    "required": ["library_name", "query"]
                },
                server="context7",
                permissions=["read"]
            ),
            MCPFunction(
                name="context7_get_code_examples",
                description="Получить примеры кода для библиотеки",
                parameters={
                    "type": "object",
                    "properties": {
                        "library_name": {
                            "type": "string",
                            "description": "Название библиотеки"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Тема или функция (например, 'hooks', 'routing')"
                        }
                    },
                    "required": ["library_name", "topic"]
                },
                server="context7",
                permissions=["read"]
            )
        ]
    
    async def can_handle_mcp(self, message: str, user_id: int, username: str = None) -> bool:
        """
        Проверяет, может ли MCP обработать данный запрос
        
        Args:
            message: Сообщение пользователя
            user_id: ID пользователя
            username: Username пользователя
            
        Returns:
            bool: True если MCP может обработать запрос
        """
        # Проверяем, что MCP включен
        if not self.mcp_enabled:
            return False
        
        # Проверяем права пользователя
        user_mode = get_user_mode(user_id, username)
        if user_mode != "admin":
            return False
        
        # Проверяем явные MCP команды
        mcp_keywords = [
            '/mcp', '/db', '/database', '/supabase',
            '/deploy', '/digitalocean', '/do',
            '/docs', '/context7', '/documentation'
        ]
        
        message_lower = message.lower()
        for keyword in mcp_keywords:
            if message_lower.startswith(keyword):
                return True
        
        # Проверяем контекстные признаки MCP запросов
        context_patterns = [
            'база данных', 'sql', 'запрос к бд', 'таблица',
            'деплой', 'развернуть', 'логи приложения',
            'документация', 'примеры кода', 'как использовать'
        ]
        
        for pattern in context_patterns:
            if pattern in message_lower:
                return True
        
        return False
    
    async def process_mcp_request(
        self, 
        message: str, 
        session_id: str, 
        user_name: str = None,
        user_id: int = None
    ) -> str:
        """
        Обрабатывает запрос через MCP
        
        Args:
            message: Сообщение пользователя
            session_id: ID сессии
            user_name: Имя пользователя
            user_id: ID пользователя
            
        Returns:
            str: Ответ от MCP или fallback на обычный agent
        """
        try:
            # Логируем MCP запрос
            logger.info(f"🔌 MCP запрос от {user_name} ({user_id}): {message[:100]}...")
            
            # Если есть Anthropic клиент, используем его
            if self.anthropic_client:
                return await self._process_with_anthropic(message, session_id, user_name)
            
            # Иначе используем OpenAI с Function Calling
            elif self.openai_client:
                return await self._process_with_openai(message, session_id, user_name)
            
            # Fallback на обычный agent
            else:
                logger.warning("⚠️ Нет доступных клиентов для MCP, используем обычный agent")
                return await self.generate_response(message, session_id, user_name)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки MCP запроса: {e}")
            # Fallback на обычный agent
            return await self.generate_response(message, session_id, user_name)
    
    async def _process_with_openai(self, message: str, session_id: str, user_name: str) -> str:
        """Обработка через OpenAI с Function Calling"""
        try:
            # Подготавливаем системный промпт с MCP инструкциями
            system_prompt = self.mcp_config.get("agent_instruction", self.instruction.get("system_instruction", ""))
            
            # Добавляем контекст из памяти
            context = await self.get_zep_memory_context(session_id)
            if context:
                system_prompt += f"\n\nКонтекст предыдущих разговоров:\n{context}"
            
            # Подготавливаем функции для OpenAI
            functions = []
            for mcp_func in self.mcp_functions:
                functions.append({
                    "name": mcp_func.name,
                    "description": mcp_func.description,
                    "parameters": mcp_func.parameters
                })
            
            # Создаем сообщения
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            # Вызываем OpenAI с функциями
            response = await self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                functions=functions if functions else None,
                function_call="auto" if functions else None,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Обрабатываем ответ
            response_message = response.choices[0].message
            
            # Если есть вызов функции
            if response_message.function_call:
                function_name = response_message.function_call.name
                function_args = json.loads(response_message.function_call.arguments)
                
                logger.info(f"🔧 Вызов MCP функции: {function_name}")
                
                # Выполняем функцию через MCP Manager
                if self.mcp_manager:
                    result = await self.mcp_manager.execute_function(
                        function_name, 
                        function_args,
                        user_id=user_name
                    )
                else:
                    result = {"error": "MCP Manager не инициализирован"}
                
                # Добавляем результат в контекст и получаем финальный ответ
                messages.append(response_message)
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(result, ensure_ascii=False)
                })
                
                # Получаем финальный ответ
                final_response = await self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                bot_response = final_response.choices[0].message.content
            else:
                # Обычный ответ без функций
                bot_response = response_message.content
            
            # Сохраняем в память
            await self.add_to_zep_memory(session_id, message, bot_response, user_name)
            
            return bot_response
            
        except Exception as e:
            logger.error(f"❌ Ошибка OpenAI MCP: {e}")
            raise
    
    async def _process_with_anthropic(self, message: str, session_id: str, user_name: str) -> str:
        """Обработка через Anthropic Claude"""
        try:
            # Подготавливаем системный промпт
            system_prompt = self.mcp_config.get("agent_instruction", "")
            
            # Добавляем описание доступных MCP функций
            if self.mcp_functions:
                system_prompt += "\n\nДоступные MCP функции:\n"
                for func in self.mcp_functions:
                    system_prompt += f"- {func.name}: {func.description}\n"
            
            # Добавляем контекст
            context = await self.get_zep_memory_context(session_id)
            if context:
                system_prompt += f"\n\nКонтекст:\n{context}"
            
            # Вызываем Claude
            response = await self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            bot_response = response.content[0].text
            
            # Сохраняем в память
            await self.add_to_zep_memory(session_id, message, bot_response, user_name)
            
            return bot_response
            
        except Exception as e:
            logger.error(f"❌ Ошибка Anthropic MCP: {e}")
            raise
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """
        Получает статус MCP системы
        
        Returns:
            Dict: Статус MCP серверов и функций
        """
        status = {
            "mcp_enabled": self.mcp_enabled,
            "anthropic_available": self.anthropic_client is not None,
            "openai_available": self.openai_client is not None,
            "total_functions": len(self.mcp_functions),
            "servers": {},
            "last_config_update": self.mcp_config.get("last_updated", "unknown")
        }
        
        # Статус каждого сервера
        servers = self.mcp_config.get("servers", {})
        for server_name, server_config in servers.items():
            status["servers"][server_name] = {
                "enabled": server_config.get("enabled", False),
                "display_name": server_config.get("display_name", server_name),
                "functions_count": len([f for f in self.mcp_functions if f.server == server_name])
            }
        
        return status
    
    def reload_mcp_config(self):
        """Перезагружает конфигурацию MCP"""
        logger.info("🔄 Перезагрузка MCP конфигурации...")
        old_functions_count = len(self.mcp_functions)
        
        self.mcp_config = self._load_mcp_config()
        self.mcp_functions = self._generate_mcp_functions()
        
        new_functions_count = len(self.mcp_functions)
        logger.info(f"✅ MCP конфигурация перезагружена. Функций: {old_functions_count} -> {new_functions_count}")


# Создаем глобальный экземпляр MCP агента
mcp_agent = None

def initialize_mcp_agent():
    """Инициализирует глобальный MCP агент"""
    global mcp_agent
    try:
        mcp_agent = MCPAgent()
        logger.info("✅ MCP Agent инициализирован глобально")
        return mcp_agent
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации MCP Agent: {e}")
        return None