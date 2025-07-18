"""
Базовые интерфейсы и абстрактные классы

Определяет контракты для основных компонентов системы
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """Типы сообщений"""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    COMMAND = "command"


class UserRole(str, Enum):
    """Роли пользователей"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


@dataclass
class User:
    """Модель пользователя"""
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str] = "ru"
    role: UserRole = UserRole.USER
    is_premium: bool = False
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or f"User_{self.id}"
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя"""
        if self.username:
            return f"@{self.username}"
        return self.full_name


@dataclass
class Message:
    """Модель сообщения"""
    id: int
    user: User
    chat_id: int
    text: Optional[str]
    type: MessageType
    timestamp: datetime
    reply_to_message_id: Optional[int] = None
    entities: List[Dict[str, Any]] = None
    attachments: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.attachments is None:
            self.attachments = {}
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_command(self) -> bool:
        """Проверяет, является ли сообщение командой"""
        return self.type == MessageType.COMMAND or (
            self.text and self.text.startswith('/')
        )
    
    def get_command(self) -> Optional[Tuple[str, str]]:
        """Извлекает команду и аргументы"""
        if not self.is_command or not self.text:
            return None
            
        parts = self.text.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Убираем @ из команды если есть
        if '@' in command:
            command = command.split('@')[0]
            
        return command, args


@dataclass
class Response:
    """Модель ответа"""
    text: str
    parse_mode: Optional[str] = "Markdown"
    reply_markup: Optional[Any] = None
    disable_web_page_preview: bool = False
    attachments: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class IMemoryManager(ABC):
    """Интерфейс для управления памятью"""
    
    @abstractmethod
    async def add_message(self, user_id: int, message: Message, response: Optional[Response] = None) -> None:
        """Добавляет сообщение в память"""
        pass
    
    @abstractmethod
    async def get_context(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает контекст разговора"""
        pass
    
    @abstractmethod
    async def clear_memory(self, user_id: int) -> None:
        """Очищает память пользователя"""
        pass
    
    @abstractmethod
    async def search_memory(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """Ищет в памяти по запросу"""
        pass


class IResponseGenerator(ABC):
    """Интерфейс для генерации ответов"""
    
    @abstractmethod
    async def generate(self, message: Message, context: List[Dict[str, Any]]) -> Response:
        """Генерирует ответ на сообщение"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Проверяет доступность генератора"""
        pass


class IIntentDetector(ABC):
    """Интерфейс для определения намерений"""
    
    @abstractmethod
    async def detect(self, message: Message) -> Dict[str, Any]:
        """Определяет намерение сообщения"""
        pass


class ICommandHandler(ABC):
    """Интерфейс для обработчика команд"""
    
    @abstractmethod
    def can_handle(self, command: str, user: User) -> bool:
        """Проверяет, может ли обработать команду"""
        pass
    
    @abstractmethod
    async def handle(self, message: Message) -> Response:
        """Обрабатывает команду"""
        pass
    
    @property
    @abstractmethod
    def commands(self) -> List[str]:
        """Список поддерживаемых команд"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Описание обработчика"""
        pass


class IService(ABC):
    """Базовый интерфейс для сервисов"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Инициализация сервиса"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Остановка сервиса"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья сервиса"""
        pass


class IMessageProcessor(ABC):
    """Интерфейс для процессора сообщений"""
    
    @abstractmethod
    async def process(self, message: Message) -> Response:
        """Обрабатывает сообщение и возвращает ответ"""
        pass


class IStateManager(ABC):
    """Интерфейс для управления состоянием"""
    
    @abstractmethod
    async def get_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает состояние пользователя"""
        pass
    
    @abstractmethod
    async def set_state(self, user_id: int, state: Dict[str, Any]) -> None:
        """Устанавливает состояние пользователя"""
        pass
    
    @abstractmethod
    async def clear_state(self, user_id: int) -> None:
        """Очищает состояние пользователя"""
        pass


class BaseError(Exception):
    """Базовый класс ошибок"""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ConfigurationError(BaseError):
    """Ошибка конфигурации"""
    pass


class ServiceError(BaseError):
    """Ошибка сервиса"""
    pass


class ValidationError(BaseError):
    """Ошибка валидации"""
    pass


class AuthorizationError(BaseError):
    """Ошибка авторизации"""
    pass