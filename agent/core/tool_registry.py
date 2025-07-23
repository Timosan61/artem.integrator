"""
Реестр инструментов для динамического управления
"""
import logging
from typing import Dict, List, Any, Optional, Type, TYPE_CHECKING
from pathlib import Path
import importlib
import inspect
import yaml

from ..core.models import ToolResponse

if TYPE_CHECKING:
    from ..tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Реестр для управления инструментами"""
    
    def __init__(self):
        self._tools: Dict[str, 'BaseTool'] = {}
        self._enabled_tools: Dict[str, bool] = {}
        logger.info("📚 ToolRegistry инициализирован")
    
    def register_tool(self, tool: 'BaseTool', enabled: bool = True) -> None:
        """
        Регистрирует инструмент
        
        Args:
            tool: Экземпляр инструмента
            enabled: Включен ли инструмент
        """
        tool_name = tool.metadata.name
        
        if tool_name in self._tools:
            logger.warning(f"⚠️ Инструмент {tool_name} уже зарегистрирован, перезаписываем")
        
        self._tools[tool_name] = tool
        self._enabled_tools[tool_name] = enabled
        
        status = "включен" if enabled else "отключен"
        logger.info(f"✅ Инструмент '{tool_name}' зарегистрирован и {status}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Удаляет инструмент из реестра
        
        Args:
            tool_name: Имя инструмента
            
        Returns:
            True если удален, False если не найден
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            del self._enabled_tools[tool_name]
            logger.info(f"🗑 Инструмент '{tool_name}' удален из реестра")
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional['BaseTool']:
        """
        Получает инструмент по имени
        
        Args:
            tool_name: Имя инструмента
            
        Returns:
            Инструмент или None
        """
        return self._tools.get(tool_name)
    
    def is_enabled(self, tool_name: str) -> bool:
        """Проверяет, включен ли инструмент"""
        return self._enabled_tools.get(tool_name, False)
    
    def enable_tool(self, tool_name: str) -> bool:
        """Включает инструмент"""
        if tool_name in self._tools:
            self._enabled_tools[tool_name] = True
            logger.info(f"✅ Инструмент '{tool_name}' включен")
            return True
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Отключает инструмент"""
        if tool_name in self._tools:
            self._enabled_tools[tool_name] = False
            logger.info(f"🚫 Инструмент '{tool_name}' отключен")
            return True
        return False
    
    def get_all_tools(self, only_enabled: bool = False) -> Dict[str, 'BaseTool']:
        """
        Возвращает все инструменты
        
        Args:
            only_enabled: Только включенные инструменты
            
        Returns:
            Словарь инструментов
        """
        if only_enabled:
            return {
                name: tool 
                for name, tool in self._tools.items() 
                if self._enabled_tools.get(name, False)
            }
        return self._tools.copy()
    
    def get_openai_schemas(self, only_enabled: bool = True) -> List[Dict[str, Any]]:
        """
        Возвращает схемы всех инструментов для OpenAI
        
        Args:
            only_enabled: Только включенные инструменты
            
        Returns:
            Список схем функций
        """
        schemas = []
        tools = self.get_all_tools(only_enabled=only_enabled)
        
        for tool_name, tool in tools.items():
            try:
                schema = tool.get_openai_schema()
                schemas.append(schema)
            except Exception as e:
                logger.error(f"❌ Ошибка получения схемы для {tool_name}: {e}")
        
        return schemas
    
    async def execute_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> ToolResponse:
        """
        Выполняет инструмент
        
        Args:
            tool_name: Имя инструмента
            params: Параметры для выполнения
            
        Returns:
            ToolResponse с результатом
        """
        # Проверяем наличие инструмента
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResponse(
                success=False,
                error=f"Инструмент '{tool_name}' не найден"
            )
        
        # Проверяем, включен ли инструмент
        if not self.is_enabled(tool_name):
            return ToolResponse(
                success=False,
                error=f"Инструмент '{tool_name}' отключен"
            )
        
        # Выполняем инструмент
        return await tool.execute_with_validation(params)
    
    def load_tools_from_config(self, config_path: str) -> int:
        """
        Загружает инструменты из конфигурации
        
        Args:
            config_path: Путь к YAML конфигурации
            
        Returns:
            Количество загруженных инструментов
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            tools_config = config.get('tools', [])
            loaded_count = 0
            
            for tool_config in tools_config:
                if not tool_config.get('enabled', True):
                    continue
                
                tool_name = tool_config['name']
                try:
                    # Пытаемся импортировать и создать инструмент
                    tool_class = self._import_tool_class(tool_name)
                    if tool_class:
                        tool_instance = tool_class()
                        self.register_tool(tool_instance, enabled=True)
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки инструмента {tool_name}: {e}")
            
            logger.info(f"📦 Загружено {loaded_count} инструментов из конфигурации")
            return loaded_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации инструментов: {e}")
            return 0
    
    def _import_tool_class(self, tool_name: str) -> Optional[Type['BaseTool']]:
        """
        Импортирует класс инструмента по имени
        
        Args:
            tool_name: Имя инструмента
            
        Returns:
            Класс инструмента или None
        """
        # Мапинг имен инструментов на модули
        tool_modules = {
            "echo_tool": "agent.tools.echo_tool.EchoTool",
            "mcp_executor": "agent.tools.mcp_tool.MCPTool",
            "youtube_analyzer": "agent.tools.youtube_tool.YouTubeAnalyzerTool"
        }
        
        if tool_name not in tool_modules:
            logger.warning(f"⚠️ Неизвестный инструмент: {tool_name}")
            return None
        
        module_path = tool_modules[tool_name]
        module_name, class_name = module_path.rsplit('.', 1)
        
        try:
            module = importlib.import_module(module_name)
            tool_class = getattr(module, class_name)
            
            # Проверяем, что это подкласс BaseTool
            # Импортируем BaseTool локально чтобы избежать циклического импорта
            from ..tools.base import BaseTool as BaseToolClass
            if not issubclass(tool_class, BaseToolClass):
                logger.error(f"❌ {class_name} не является подклассом BaseTool")
                return None
            
            return tool_class
            
        except Exception as e:
            logger.error(f"❌ Ошибка импорта {module_path}: {e}")
            return None
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Возвращает информацию о реестре"""
        return {
            "total_tools": len(self._tools),
            "enabled_tools": sum(1 for enabled in self._enabled_tools.values() if enabled),
            "tools": [
                {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "version": tool.metadata.version,
                    "enabled": self._enabled_tools.get(tool.metadata.name, False),
                    "requires_confirmation": tool.metadata.requires_confirmation
                }
                for tool in self._tools.values()
            ]
        }


# Глобальный экземпляр реестра
tool_registry = ToolRegistry()