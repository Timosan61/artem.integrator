"""
Система авторизации для двухрежимного бота

Определяет права доступа пользователей:
- Обычные пользователи: базовая консультация
- Администратор: полный доступ к SocialMedia функциям
"""

import logging
from functools import wraps
from typing import Optional, Dict, Any, List

from .config import ADMIN_USER_ID, ADMIN_USERNAMES
from .core.config import config

logger = logging.getLogger(__name__)


def is_admin(user_id: int, username: str = None) -> bool:
    """
    Проверяет является ли пользователь администратором
    
    Args:
        user_id: Telegram User ID
        username: Telegram username (без @)
        
    Returns:
        bool: True если пользователь админ
    """
    # Проверка по User ID из списка
    if user_id and config.admin.user_ids:
        if user_id in config.admin.user_ids:
            logger.debug(f"✅ User {user_id} is admin (found in ID list)")
            return True
    
    # Проверка по username
    if username and config.admin.usernames:
        clean_username = username.lower().replace('@', '')
        admin_usernames = [u.lower().strip() for u in config.admin.usernames if u.strip()]
        if clean_username in admin_usernames:
            logger.debug(f"✅ User @{username} is admin (found in username list)")
            return True
    
    # Проверка auto-admin manager
    from .core.auto_admin import auto_admin_manager
    admins = auto_admin_manager.get_all_admins()
    if user_id and str(user_id) in admins:
        logger.debug(f"✅ User {user_id} is admin (found in auto-admin)")
        return True
    
    logger.debug(f"❌ User {user_id} (@{username}) is NOT admin")
    return False


def get_user_mode(user_id: int, username: str = None, test_mode_override: dict = None) -> str:
    """
    Определяет режим работы бота для пользователя
    
    Args:
        user_id: Telegram User ID
        username: Telegram username
        test_mode_override: Словарь с тестовыми режимами {user_id: "admin"|"user"}
        
    Returns:
        str: "admin" или "user"
    """
    # Проверяем тестовый режим в первую очередь
    if test_mode_override and user_id in test_mode_override:
        test_mode = test_mode_override[user_id]
        if test_mode in ["admin", "user"]:
            return test_mode
    
    # Обычная проверка прав
    if is_admin(user_id, username):
        return "admin"
    return "user"


def admin_required(func):
    """
    Декоратор для функций, требующих админских прав
    
    Использование:
        @admin_required
        def admin_function(message_data):
            # Функция выполнится только для админа
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Предполагаем, что первый аргумент содержит данные сообщения
        message_data = args[0] if args else kwargs.get('message_data', {})
        
        # Извлекаем данные пользователя
        user_data = message_data.get('from', {})
        user_id = user_data.get('id')
        username = user_data.get('username')
        
        if not is_admin(user_id, username):
            logger.warning(f"❌ Попытка доступа к админской функции от пользователя {user_id} (@{username})")
            return None
        
        logger.info(f"✅ Админский доступ разрешен для пользователя {user_id} (@{username})")
        return func(*args, **kwargs)
    
    return wrapper


def log_user_access(user_id: int, username: str = None, command: str = None):
    """
    Логирует доступ пользователя к боту
    
    Args:
        user_id: Telegram User ID
        username: Telegram username
        command: Выполняемая команда
    """
    mode = get_user_mode(user_id, username)
    user_info = f"ID:{user_id}"
    if username:
        user_info += f" @{username}"
    
    if command:
        logger.info(f"🔑 [{mode.upper()}] {user_info} выполняет команду: {command}")
    else:
        logger.info(f"🔑 [{mode.upper()}] {user_info} отправил сообщение")


def get_permission_info() -> Dict[str, Any]:
    """
    Возвращает информацию о настройках прав доступа
    
    Returns:
        dict: Информация о правах доступа
    """
    from .config import MCP_ENABLED
    return {
        "admin_user_id": ADMIN_USER_ID,
        "admin_usernames": ADMIN_USERNAMES,
        "admin_configured": bool(ADMIN_USER_ID or ADMIN_USERNAMES),
        "security_mode": "enabled" if ADMIN_USER_ID else "disabled",
        "mcp_enabled": MCP_ENABLED
    }


def is_mcp_admin(user_id: int, username: str = None) -> bool:
    """
    Проверяет права доступа к MCP функциям
    
    Args:
        user_id: Telegram User ID
        username: Telegram username
        
    Returns:
        bool: True если пользователь имеет права на MCP
    """
    # Сейчас права на MCP есть у всех админов
    # В будущем можно добавить отдельную проверку
    return is_admin(user_id, username)


def get_mcp_permissions(user_id: int, username: str = None) -> Dict[str, List[str]]:
    """
    Получает список разрешенных MCP операций для пользователя
    
    Args:
        user_id: Telegram User ID
        username: Telegram username
        
    Returns:
        dict: Словарь с разрешениями по серверам
    """
    if not is_mcp_admin(user_id, username):
        return {}
    
    # Полные права для админов
    return {
        "supabase": ["read", "write", "admin"],
        "digitalocean": ["read", "deploy", "admin"],
        "context7": ["read"]
    }


def format_access_denied_message(user_id: int, username: str = None) -> str:
    """
    Форматирует сообщение об отказе в доступе
    
    Args:
        user_id: User ID пользователя
        username: Username пользователя
        
    Returns:
        str: Сообщение об отказе в доступе
    """
    user_info = f"ID: {user_id}"
    if username:
        user_info += f" (@{username})"
    
    return f"""🚫 Доступ к этой функции ограничен

👤 Пользователь: {user_info}
🔒 Требуются администраторские права

Для получения доступа обратитесь к администратору системы."""


def is_admin_token(token: str) -> bool:
    """
    Проверяет, является ли токен админским
    
    Args:
        token: Токен для проверки
        
    Returns:
        bool: True если токен админский
    """
    # Можно добавить список админских токенов в конфигурацию
    # Пока используем простую проверку через переменную окружения
    import os
    admin_token = os.getenv('ADMIN_TOKEN', 'secure-admin-token')
    return token == admin_token


def format_admin_welcome_message(user_id: int = None, username: str = None, test_mode_override: dict = None) -> str:
    """
    Форматирует приветственное сообщение для админа
    
    Args:
        user_id: User ID админа
        username: Username админа
        test_mode_override: Словарь с тестовыми режимами
        
    Returns:
        str: Приветственное сообщение для админа
    """
    # Проверяем тестовый режим
    test_mode_info = ""
    if test_mode_override and user_id in test_mode_override:
        test_mode = test_mode_override[user_id]
        test_mode_info = f"\n🧪 **ТЕСТОВЫЙ РЕЖИМ: {test_mode.upper()}**"
    
    # Проверяем доступность MCP
    from .config import MCP_ENABLED
    mcp_section = ""
    if MCP_ENABLED:
        mcp_section = """
🔌 **MCP команды:**
• /mcp status - статус MCP серверов
• /mcp projects - список Supabase проектов
• /db &lt;запрос&gt; - выполнить SQL запрос
• /mcp apps - список DigitalOcean приложений
• /docs &lt;библиотека&gt; &lt;запрос&gt; - поиск документации
• /mcp help - справка по MCP
"""
    
    return f"""🔑 Добро пожаловать, Администратор!{test_mode_info}

👤 ID: {user_id}
📛 Username: @{username or 'не указан'}

🎯 Доступные команды:
• /youtube <запрос> - поиск YouTube видео
• /instagram <запрос> - поиск Instagram реелов  
• /tiktok <запрос> - поиск TikTok видео
• /channel <канал> - анализ YouTube канала
• /admin_status - статус админской панели
• /social_config - настройки SocialMedia
{mcp_section}
🧪 Тестирование режимов:
• /test_user - переключиться в пользовательский режим
• /test_admin - переключиться в админский режим  
• /test_status - проверить текущий режим

📊 Также доступны все базовые функции консультанта."""


def format_user_welcome_message(user_name: str = None, user_id: int = None, test_mode_override: dict = None) -> str:
    """
    Форматирует приветственное сообщение для обычного пользователя
    
    Args:
        user_name: Имя пользователя
        user_id: ID пользователя (для проверки тестового режима)
        test_mode_override: Словарь с тестовыми режимами
        
    Returns:
        str: Приветственное сообщение для пользователя
    """
    # Проверяем тестовый режим
    test_mode_info = ""
    if test_mode_override and user_id and user_id in test_mode_override:
        test_mode = test_mode_override[user_id]
        test_mode_info = f"\n🧪 **ТЕСТОВЫЙ РЕЖИМ: {test_mode.upper()}**"
    
    greeting_name = user_name or "друг"
    return f"""👋 Привет, {greeting_name}!{test_mode_info}

Меня зовут Анастасия, я консультант Textile Pro.

💬 Задавайте любые вопросы о:
• Текстильном производстве
• Заказах из Китая
• Качестве материалов
• Логистике и доставке
• Ценах и условиях

Я готова помочь вам с любыми вопросами!"""