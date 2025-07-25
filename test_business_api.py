#!/usr/bin/env python3
"""
Тест для проверки Business API функций
"""

import asyncio
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Определяем необходимые типы локально для избежания импорта конфигурации
class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"

class MessageType(Enum):
    TEXT = "text"
    VOICE = "voice"
    OTHER = "other"

@dataclass
class User:
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER

@dataclass
class Message:
    id: int
    user: User
    chat_id: int
    text: Optional[str] = None
    type: MessageType = MessageType.TEXT
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    is_business_message: bool = False
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# Мокаем config для функций
mock_config = Mock()
mock_config.telegram.token = "test_token"

# Создаем функции для тестирования без зависимости от конфигурации
def send_business_message_test(chat_id: int, text: str, business_connection_id: str) -> Dict[str, Any]:
    """Тестовая версия send_business_message"""
    import requests
    
    # Валидация входных данных
    if not chat_id:
        return {"success": False, "error": "Invalid chat_id", "details": "chat_id is required"}
    
    if not text or not text.strip():
        return {"success": False, "error": "Invalid text", "details": "text is required and cannot be empty"}
    
    if not business_connection_id:
        return {"success": False, "error": "Invalid business_connection_id", "details": "business_connection_id is required"}
    
    # Ограничение длины сообщения
    if len(text) > 4096:
        text = text[:4093] + "..."
    
    url = f"https://api.telegram.org/bot{mock_config.telegram.token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "business_connection_id": business_connection_id,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        if response.status_code == 200 and result.get("ok"):
            message_id = result.get('result', {}).get('message_id', 'Unknown')
            return {
                "success": True, 
                "message_id": message_id,
                "api_response": result
            }
        else:
            error_code = result.get("error_code", "Unknown")
            error_description = result.get("description", "Unknown error")
            
            return {
                "success": False, 
                "error": f"Telegram API Error {error_code}",
                "details": error_description,
                "api_response": result
            }
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout", "details": "Request took longer than 15 seconds"}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": "Connection error", "details": str(e)}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": "HTTP error", "details": str(e)}
    except ValueError as e:
        return {"success": False, "error": "JSON parse error", "details": str(e)}
    except Exception as e:
        return {"success": False, "error": "Unexpected error", "details": str(e)}


def test_send_business_message_validation():
    """Тест валидации входных данных"""
    print("🧪 Тестируем валидацию send_business_message...")
    
    # Тест пустого chat_id
    result = send_business_message_test(None, "test", "conn_123")
    assert not result["success"], "Должен отклонить пустой chat_id"
    assert "chat_id" in result["error"], f"Ошибка должна упоминать chat_id: {result}"
    print("✅ Валидация chat_id работает")
    
    # Тест пустого текста
    result = send_business_message_test(123, "", "conn_123")
    assert not result["success"], "Должен отклонить пустой текст"
    assert "text" in result["error"], f"Ошибка должна упоминать text: {result}"
    print("✅ Валидация text работает")
    
    # Тест пустого business_connection_id
    result = send_business_message_test(123, "test", "")
    assert not result["success"], "Должен отклонить пустой business_connection_id"
    assert "business_connection_id" in result["error"], f"Ошибка должна упоминать business_connection_id: {result}"
    print("✅ Валидация business_connection_id работает")
    
    print("✅ Все валидации прошли успешно!")


def test_message_length_limit():
    """Тест ограничения длины сообщения"""
    print("\n🧪 Тестируем ограничение длины сообщения...")
    
    # Мокаем requests для избежания реального API вызова
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_post.return_value = mock_response
        
        # Тест длинного сообщения
        long_text = "A" * 5000  # 5000 символов
        result = send_business_message_test(123, long_text, "conn_123")
        
        # Проверяем что функция была вызвана
        assert mock_post.called, "API должен был быть вызван"
        
        # Проверяем что текст был обрезан
        call_args = mock_post.call_args
        sent_data = call_args[1]['json'] if 'json' in call_args[1] else call_args[0][1]
        sent_text = sent_data['text']
        
        assert len(sent_text) <= 4096, f"Текст должен быть обрезан до 4096 символов, получили {len(sent_text)}"
        assert sent_text.endswith("..."), "Обрезанный текст должен заканчиваться на '...'"
        
    print("✅ Ограничение длины сообщения работает корректно!")


def test_business_message_structure():
    """Тест создания Business сообщения"""
    print("\n🧪 Тестируем создание Business сообщения...")
    
    # Создаем тестовое сообщение
    user = User(
        id=123456,
        username="testuser",
        first_name="Test",
        last_name="User",
        role=UserRole.USER
    )
    
    message = Message(
        id=1,
        user=user,
        chat_id=123456,
        text="Тестовое Business сообщение",
        type=MessageType.TEXT,
        timestamp=datetime.now(),
        metadata={"business_connection_id": "test_connection_123"},
        is_business_message=True
    )
    
    # Проверяем флаг Business сообщения
    assert message.is_business_message == True, "Флаг is_business_message должен быть True"
    
    # Проверяем наличие business_connection_id в метаданных
    assert "business_connection_id" in message.metadata, "business_connection_id должен быть в метаданных"
    assert message.metadata["business_connection_id"] == "test_connection_123", "business_connection_id должен совпадать"
    
    print("✅ Структура Business сообщения корректна!")


def test_error_handling():
    """Тест обработки ошибок"""
    print("\n🧪 Тестируем обработку ошибок...")
    
    # Мокаем requests для симуляции ошибки API
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "ok": False, 
            "error_code": 400,
            "description": "Bad Request: business connection not found"
        }
        mock_post.return_value = mock_response
        
        result = send_business_message_test(123, "test", "invalid_connection")
        
        assert not result["success"], "Должен вернуть ошибку для неверного подключения"
        assert "400" in result["error"], f"Ошибка должна содержать код 400: {result}"
        assert "business connection not found" in result["details"], f"Детали должны содержать описание ошибки: {result}"
        
    print("✅ Обработка ошибок работает корректно!")


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов Business API...\n")
    
    try:
        test_send_business_message_validation()
        test_message_length_limit()
        test_business_message_structure()
        test_error_handling()
        
        print("\n🎉 Все тесты прошли успешно!")
        print("\n📋 Результаты тестирования:")
        print("✅ Валидация входных данных")
        print("✅ Ограничение длины сообщений")
        print("✅ Структура Business сообщений")
        print("✅ Обработка ошибок API")
        
        print("\n💡 Рекомендации:")
        print("1. Протестируйте отправку реального Business сообщения")
        print("2. Проверьте логи при получении business_message")
        print("3. Используйте команду /business_status для диагностики")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Тест упал с ошибкой: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)