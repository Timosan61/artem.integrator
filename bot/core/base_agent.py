"""
Базовый интерфейс для всех агентов

Определяет контракт, который должны реализовывать все агенты
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from .interfaces import Message, Response


class IAgent(ABC):
    """Базовый интерфейс для всех агентов"""
    
    @abstractmethod
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает входящее сообщение
        
        Args:
            message: Сообщение для обработки
            
        Returns:
            Response с ответом агента
        """
        pass
        
    @abstractmethod
    async def can_handle(self, message: Message) -> bool:
        """
        Проверяет, может ли агент обработать данное сообщение
        
        Args:
            message: Сообщение для проверки
            
        Returns:
            True если агент может обработать сообщение
        """
        pass
        
    @abstractmethod
    def get_name(self) -> str:
        """Возвращает имя агента"""
        pass
        
    @abstractmethod
    def get_priority(self) -> int:
        """
        Возвращает приоритет агента (больше = выше приоритет)
        
        Returns:
            Приоритет от 0 до 100
        """
        pass
        
    async def clear_user_memory(self, user_id: int) -> bool:
        """
        Очищает память пользователя (опционально)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """
        Возвращает статус агента (опционально)
        
        Returns:
            Словарь со статусом
        """
        return {
            "name": self.get_name(),
            "priority": self.get_priority(),
            "enabled": True
        }


class ChainedAgent(IAgent):
    """
    Агент, использующий цепочку ответственности
    
    Передает сообщение по цепочке агентов, пока один из них не обработает
    """
    
    def __init__(self, agents: List[IAgent]):
        """
        Args:
            agents: Список агентов в порядке приоритета
        """
        self.agents = sorted(agents, key=lambda a: a.get_priority(), reverse=True)
        
    async def process_message(self, message: Message) -> Response:
        """Обрабатывает сообщение через цепочку агентов"""
        for agent in self.agents:
            if await agent.can_handle(message):
                return await agent.process_message(message)
                
        # Если никто не может обработать - возвращаем стандартный ответ
        return Response(
            text="Извините, я не могу обработать ваш запрос.",
            metadata={"error": "No suitable agent found"}
        )
        
    async def can_handle(self, message: Message) -> bool:
        """Проверяет, может ли хотя бы один агент обработать сообщение"""
        for agent in self.agents:
            if await agent.can_handle(message):
                return True
        return False
        
    def get_name(self) -> str:
        return "ChainedAgent"
        
    def get_priority(self) -> int:
        return 50  # Средний приоритет
        
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память во всех агентах"""
        results = []
        for agent in self.agents:
            results.append(await agent.clear_user_memory(user_id))
        return all(results)
        
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус всех агентов в цепочке"""
        return {
            "name": self.get_name(),
            "agents": [agent.get_status() for agent in self.agents],
            "total_agents": len(self.agents)
        }