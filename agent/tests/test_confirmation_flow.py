#!/usr/bin/env python3
"""
Тесты для Confirmation Manager и ConversationState
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем корневую директорию в path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agent.core.confirmation_manager import (
    ConfirmationManager, 
    ConfirmationStatus,
    ConfirmationSession
)
from agent.core.conversation_state import (
    ConversationStateManager,
    StateType
)
from agent.core.confirmation_formatter import ConfirmationFormatter
from agent.tools import MCPTool, EchoTool
from agent.core.models import MCPCommandParams, EchoToolParams, ToolType


async def test_confirmation_request():
    """Тест создания запроса подтверждения"""
    print("\n🧪 Тест 1: Создание запроса подтверждения")
    print("-" * 50)
    
    manager = ConfirmationManager(default_timeout=60)
    tool = MCPTool()
    params = MCPCommandParams(
        command="delete app production",
        user_id="test_user"
    )
    
    # Создаем запрос
    session_id = await manager.request_confirmation(
        user_id="test_user",
        tool=tool,
        params=params
    )
    
    print(f"✅ Создан запрос подтверждения: {session_id}")
    
    # Проверяем сессию
    session = manager.get_session(session_id)
    assert session is not None
    assert session.status == ConfirmationStatus.PENDING
    assert session.user_id == "test_user"
    assert session.tool == tool
    
    print(f"   Статус: {session.status}")
    print(f"   Инструмент: {session.tool.metadata.name}")
    print(f"   Истекает через: {(session.expires_at - datetime.now()).seconds}с")
    
    # Проверяем список ожидающих сессий
    pending = manager.get_pending_sessions("test_user")
    assert len(pending) == 1
    assert pending[0].session_id == session_id
    
    return True


async def test_confirmation_response():
    """Тест обработки ответа на подтверждение"""
    print("\n🧪 Тест 2: Обработка ответа на подтверждение")
    print("-" * 50)
    
    manager = ConfirmationManager()
    tool = EchoTool()
    params = EchoToolParams(
        message="Test confirmation",
        uppercase=True,
        user_id="test_user"
    )
    
    # Создаем запрос
    session_id = await manager.request_confirmation(
        user_id="test_user",
        tool=tool,
        params=params
    )
    
    # Тест 1: Подтверждение
    print("✅ Тестируем подтверждение...")
    result = await manager.handle_response(session_id, confirmed=True)
    
    assert result is not None
    assert result.success
    assert result.data["echo"] == "TEST CONFIRMATION"
    
    session = manager.get_session(session_id)
    assert session.status == ConfirmationStatus.CONFIRMED
    
    print(f"   Результат: {result.data['echo']}")
    print(f"   Статус сессии: {session.status}")
    
    # Тест 2: Отмена
    params2 = EchoToolParams(
        message="Test cancellation",
        user_id="test_user"
    )
    
    session_id2 = await manager.request_confirmation(
        user_id="test_user",
        tool=tool,
        params=params2
    )
    
    print("\n✅ Тестируем отмену...")
    result2 = await manager.handle_response(session_id2, confirmed=False)
    
    assert result2 is None
    session2 = manager.get_session(session_id2)
    assert session2.status == ConfirmationStatus.CANCELLED
    
    print(f"   Статус сессии: {session2.status}")
    
    return True


async def test_confirmation_timeout():
    """Тест таймаута подтверждения"""
    print("\n🧪 Тест 3: Таймаут подтверждения")
    print("-" * 50)
    
    # Создаем менеджер с коротким таймаутом
    manager = ConfirmationManager(default_timeout=1)
    tool = EchoTool()
    params = EchoToolParams(
        message="Test timeout",
        user_id="test_user"
    )
    
    session_id = await manager.request_confirmation(
        user_id="test_user",
        tool=tool,
        params=params
    )
    
    print("⏰ Ждем истечения таймаута...")
    await asyncio.sleep(2)
    
    # Пытаемся обработать истекший запрос
    result = await manager.handle_response(session_id, confirmed=True)
    
    assert result is None
    session = manager.get_session(session_id)
    assert session.status == ConfirmationStatus.EXPIRED
    
    print(f"✅ Сессия истекла: {session.status}")
    
    # Проверяем очистку истекших сессий
    expired_count = manager.cleanup_expired()
    print(f"✅ Очищено истекших сессий: {expired_count}")
    
    return True


async def test_conversation_states():
    """Тест управления состояниями разговора"""
    print("\n🧪 Тест 4: Управление состояниями разговора")
    print("-" * 50)
    
    state_manager = ConversationStateManager(default_ttl=60)
    
    # Тест 1: Создание состояния подтверждения
    print("✅ Создаем состояние подтверждения...")
    conf_state = state_manager.set_confirmation_state(
        user_id="test_user",
        original_message="удали приложение production",
        tool_name="mcp_executor",
        parameters={"command": "delete app production"},
        confirmation_session_id="test_session_123"
    )
    
    assert conf_state.state_type == StateType.CONFIRMATION.value
    assert conf_state.tool_to_execute == "mcp_executor"
    assert conf_state.parameters["confirmation_session_id"] == "test_session_123"
    
    print(f"   Тип состояния: {conf_state.state_type}")
    print(f"   Инструмент: {conf_state.tool_to_execute}")
    
    # Тест 2: Создание состояния уточнения
    print("\n✅ Создаем состояние уточнения...")
    clarif_state = state_manager.set_clarification_state(
        user_id="test_user2",
        original_message="сделай что-нибудь с данными",
        clarification_options=[
            {"tool": "mcp_executor", "name": "Управление инфраструктурой"},
            {"tool": None, "name": "Обычный разговор"}
        ]
    )
    
    assert clarif_state.state_type == StateType.CLARIFICATION.value
    assert len(clarif_state.parameters["options"]) == 2
    
    print(f"   Тип состояния: {clarif_state.state_type}")
    print(f"   Вариантов: {len(clarif_state.parameters['options'])}")
    
    # Тест 3: Обновление состояния
    print("\n✅ Обновляем состояние...")
    updated = state_manager.update_state(
        user_id="test_user",
        parameters={"command": "delete app staging", "updated": True}
    )
    
    assert updated is not None
    assert updated.parameters["updated"] is True
    
    # Тест 4: История состояний
    print("\n✅ Проверяем историю...")
    state_manager.clear_state("test_user")
    history = state_manager.get_state_history("test_user")
    
    assert len(history) > 0
    print(f"   Записей в истории: {len(history)}")
    
    return True


async def test_confirmation_formatting():
    """Тест форматирования сообщений подтверждения"""
    print("\n🧪 Тест 5: Форматирование сообщений")
    print("-" * 50)
    
    tool = MCPTool()
    params = MCPCommandParams(
        command="delete database production_db",
        user_id="test_user"
    )
    
    expires_at = datetime.now() + timedelta(minutes=5)
    
    # Тест форматирования подтверждения
    message = ConfirmationFormatter.format_confirmation_message(
        tool=tool,
        params=params,
        session_id="test_123",
        expires_at=expires_at
    )
    
    print("✅ Сообщение подтверждения:")
    print(message)
    
    assert "Требуется подтверждение" in message
    assert "delete database" in message
    assert "⚠️" in message  # Должно быть предупреждение для delete
    
    # Тест форматирования уточнения
    clarif_message = ConfirmationFormatter.format_clarification_message(
        original_message="покажи что-нибудь",
        options=[
            {
                "tool": ToolType.MCP,
                "name": "Управление инфраструктурой",
                "description": "Просмотр приложений и баз данных",
                "icon": "🔧"
            },
            {
                "tool": None,
                "name": "Обычный разговор",
                "description": "Просто поговорить",
                "icon": "💬"
            }
        ]
    )
    
    print("\n✅ Сообщение уточнения:")
    print(clarif_message)
    
    assert "Уточните" in clarif_message
    assert "покажи что-нибудь" in clarif_message
    assert "🔧" in clarif_message
    
    # Тест форматирования успеха
    success_message = ConfirmationFormatter.format_success_message(
        tool_type=ToolType.MCP,
        operation="Удаление базы данных",
        result={"status": "deleted", "database": "test_db"}
    )
    
    print("\n✅ Сообщение успеха:")
    print(success_message)
    
    assert "успешно" in success_message
    assert "deleted" in success_message
    
    return True


async def test_confirmation_buttons():
    """Тест генерации кнопок для Telegram"""
    print("\n🧪 Тест 6: Генерация кнопок")
    print("-" * 50)
    
    manager = ConfirmationManager()
    session_id = "test_session_456"
    
    buttons = manager.format_confirmation_buttons(session_id)
    
    assert len(buttons) == 2
    assert buttons[0]["text"] == "✅ Подтвердить"
    assert buttons[0]["callback_data"] == f"confirm:{session_id}:yes"
    assert buttons[1]["text"] == "❌ Отменить"
    assert buttons[1]["callback_data"] == f"confirm:{session_id}:no"
    
    print("✅ Кнопки подтверждения:")
    for btn in buttons:
        print(f"   {btn['text']} -> {btn['callback_data']}")
    
    return True


async def test_state_export_import():
    """Тест экспорта/импорта состояний"""
    print("\n🧪 Тест 7: Экспорт/импорт состояний")
    print("-" * 50)
    
    manager = ConversationStateManager()
    
    # Создаем состояние
    original_state = manager.set_confirmation_state(
        user_id="export_user",
        original_message="test export",
        tool_name="test_tool",
        parameters={"test": True},
        confirmation_session_id="export_123"
    )
    
    # Экспортируем
    exported = manager.export_state("export_user")
    assert exported is not None
    
    print("✅ Экспортировано состояние:")
    print(f"   user_id: {exported['user_id']}")
    print(f"   state_type: {exported['state_type']}")
    
    # Очищаем и импортируем обратно
    manager.clear_state("export_user")
    imported = manager.import_state(exported)
    
    assert imported is not None
    assert imported.user_id == original_state.user_id
    assert imported.state_type == original_state.state_type
    assert imported.parameters["test"] is True
    
    print("✅ Импортировано состояние успешно")
    
    return True


async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов Confirmation Flow")
    print("=" * 60)
    
    tests = [
        ("Создание запроса подтверждения", test_confirmation_request),
        ("Обработка ответа", test_confirmation_response),
        ("Таймаут подтверждения", test_confirmation_timeout),
        ("Управление состояниями", test_conversation_states),
        ("Форматирование сообщений", test_confirmation_formatting),
        ("Генерация кнопок", test_confirmation_buttons),
        ("Экспорт/импорт состояний", test_state_export_import)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("-" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    print("-" * 60)
    print(f"Пройдено: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
    else:
        print(f"\n⚠️  Некоторые тесты не прошли ({total - passed} из {total})")
    
    return passed == total


if __name__ == "__main__":
    # Запуск тестов
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)