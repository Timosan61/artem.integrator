#!/usr/bin/env python3
"""
Тесты системы инструментов (Tool System)
ПРИМЕЧАНИЕ: Этот файл неактуален - MCPTool удален в Simple Agent архитектуре
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agent.tools import EchoTool, MCPTool
from agent.core.tool_registry import tool_registry
from agent.core.models import EchoToolParams, MCPCommandParams


async def test_echo_tool_direct():
    """Тест прямого вызова Echo инструмента"""
    print("\n🧪 Тест 1: Прямой вызов EchoTool")
    print("-" * 50)
    
    echo_tool = EchoTool()
    
    # Тест 1: Обычное эхо
    params = EchoToolParams(
        message="Hello Tool System",
        uppercase=False,
        user_id="test_user"
    )
    
    result = await echo_tool.execute(params)
    print(f"✅ Обычное эхо:")
    print(f"   Успех: {result.success}")
    print(f"   Данные: {result.data}")
    assert result.success
    assert result.data["echo"] == "Hello Tool System"
    
    # Тест 2: Эхо в верхнем регистре
    params_upper = EchoToolParams(
        message="test uppercase",
        uppercase=True,
        user_id="test_user"
    )
    
    result_upper = await echo_tool.execute(params_upper)
    print(f"\n✅ Эхо в верхнем регистре:")
    print(f"   Успех: {result_upper.success}")
    print(f"   Данные: {result_upper.data}")
    assert result_upper.success
    assert result_upper.data["echo"] == "TEST UPPERCASE"
    
    return True


async def test_tool_registry():
    """Тест реестра инструментов"""
    print("\n🧪 Тест 2: Tool Registry")
    print("-" * 50)
    
    # Регистрируем инструменты
    echo_tool = EchoTool()
    mcp_tool = MCPTool()
    
    tool_registry.register_tool(echo_tool)
    tool_registry.register_tool(mcp_tool)
    
    # Проверяем регистрацию
    print("✅ Зарегистрированные инструменты:")
    registry_info = tool_registry.get_registry_info()
    print(f"   Всего: {registry_info['total_tools']}")
    print(f"   Включено: {registry_info['enabled_tools']}")
    
    for tool_info in registry_info['tools']:
        status = "✅" if tool_info['enabled'] else "❌"
        print(f"   {status} {tool_info['name']} - {tool_info['description']}")
    
    assert registry_info['total_tools'] >= 2
    
    # Тест получения инструмента
    retrieved_tool = tool_registry.get_tool("echo_tool")
    assert retrieved_tool is not None
    assert retrieved_tool.metadata.name == "echo_tool"
    
    return True


async def test_tool_execution_via_registry():
    """Тест выполнения инструментов через реестр"""
    print("\n🧪 Тест 3: Выполнение через Registry")
    print("-" * 50)
    
    # Убедимся что инструменты зарегистрированы
    if not tool_registry.get_tool("echo_tool"):
        tool_registry.register_tool(EchoTool())
    
    # Выполняем echo через реестр
    params = {
        "message": "Registry test",
        "uppercase": True,
        "user_id": "registry_user"
    }
    
    result = await tool_registry.execute_tool("echo_tool", params)
    print(f"✅ Echo через реестр:")
    print(f"   Успех: {result.success}")
    print(f"   Данные: {result.data}")
    assert result.success
    assert result.data["echo"] == "REGISTRY TEST"
    
    # Тест с несуществующим инструментом
    result_invalid = await tool_registry.execute_tool("invalid_tool", {})
    print(f"\n✅ Несуществующий инструмент:")
    print(f"   Успех: {result_invalid.success}")
    print(f"   Ошибка: {result_invalid.error}")
    assert not result_invalid.success
    assert "не найден" in result_invalid.error
    
    return True


async def test_openai_schemas():
    """Тест генерации схем для OpenAI"""
    print("\n🧪 Тест 4: OpenAI Schemas")
    print("-" * 50)
    
    # Получаем схемы
    schemas = tool_registry.get_openai_schemas()
    
    print(f"✅ Сгенерировано схем: {len(schemas)}")
    
    for schema in schemas:
        func = schema["function"]
        print(f"\n📋 Схема: {func['name']}")
        print(f"   Описание: {func['description']}")
        print(f"   Параметры: {list(func['parameters']['properties'].keys())}")
        print(f"   Обязательные: {func['parameters'].get('required', [])}")
    
    # Проверяем структуру схем
    assert len(schemas) >= 2
    for schema in schemas:
        assert "type" in schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert "parameters" in schema["function"]
    
    return True


async def test_mcp_tool():
    """Тест MCP инструмента"""
    print("\n🧪 Тест 5: MCP Tool")
    print("-" * 50)
    
    mcp_tool = MCPTool()
    
    # Тест различных команд
    test_commands = [
        {
            "command": "list apps",
            "expected_type": "applications"
        },
        {
            "command": "показать базы данных",
            "expected_type": "databases"
        },
        {
            "command": "get deployments",
            "expected_type": "deployments"
        }
    ]
    
    for test in test_commands:
        params = MCPCommandParams(
            command=test["command"],
            user_id="test_mcp_user"
        )
        
        result = await mcp_tool.execute(params)
        print(f"\n✅ MCP команда: {test['command']}")
        print(f"   Успех: {result.success}")
        print(f"   Тип команды: {result.metadata.get('command_type')}")
        
        # Проверяем что команда выполнена (или эмулирована)
        assert result.success
        assert result.metadata.get("command_type") == test["expected_type"]
        
        # Если это эмуляция, проверяем флаг
        if result.metadata.get("emulated"):
            print(f"   ⚠️  Эмулированный ответ")
    
    return True


async def test_tool_validation():
    """Тест валидации параметров"""
    print("\n🧪 Тест 6: Валидация параметров")
    print("-" * 50)
    
    echo_tool = EchoTool()
    
    # Тест с невалидными параметрами (отсутствует user_id)
    invalid_params = {
        "message": "Test message"
        # user_id отсутствует
    }
    
    result = await echo_tool.execute_with_validation(invalid_params)
    print(f"✅ Невалидные параметры:")
    print(f"   Успех: {result.success}")
    print(f"   Ошибка: {result.error}")
    assert not result.success
    assert "user_id" in result.error.lower()
    
    # Тест с валидными параметрами
    valid_params = {
        "message": "Valid test",
        "user_id": "test_user",
        "uppercase": True
    }
    
    result_valid = await echo_tool.execute_with_validation(valid_params)
    print(f"\n✅ Валидные параметры:")
    print(f"   Успех: {result_valid.success}")
    print(f"   Данные: {result_valid.data}")
    assert result_valid.success
    
    return True


async def test_tool_enable_disable():
    """Тест включения/отключения инструментов"""
    print("\n🧪 Тест 7: Включение/отключение инструментов")
    print("-" * 50)
    
    # Проверяем что echo_tool включен
    assert tool_registry.is_enabled("echo_tool")
    print("✅ echo_tool включен по умолчанию")
    
    # Отключаем инструмент
    tool_registry.disable_tool("echo_tool")
    assert not tool_registry.is_enabled("echo_tool")
    print("✅ echo_tool успешно отключен")
    
    # Пытаемся выполнить отключенный инструмент
    result = await tool_registry.execute_tool("echo_tool", {
        "message": "test",
        "user_id": "test"
    })
    assert not result.success
    assert "отключен" in result.error
    print("✅ Отключенный инструмент не выполняется")
    
    # Включаем обратно
    tool_registry.enable_tool("echo_tool")
    assert tool_registry.is_enabled("echo_tool")
    print("✅ echo_tool успешно включен обратно")
    
    return True


async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов Tool System")
    print("=" * 60)
    
    tests = [
        ("Echo Tool Direct", test_echo_tool_direct),
        ("Tool Registry", test_tool_registry),
        ("Execution via Registry", test_tool_execution_via_registry),
        ("OpenAI Schemas", test_openai_schemas),
        ("MCP Tool", test_mcp_tool),
        ("Parameter Validation", test_tool_validation),
        ("Enable/Disable Tools", test_tool_enable_disable)
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