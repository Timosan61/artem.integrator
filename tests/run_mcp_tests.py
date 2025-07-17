#!/usr/bin/env python3
"""
Запуск всех MCP тестов

Использование:
    python tests/run_mcp_tests.py              # Запустить все тесты
    python tests/run_mcp_tests.py -v           # Подробный вывод
    python tests/run_mcp_tests.py -k manager   # Только тесты manager
    python tests/run_mcp_tests.py --cov        # С покрытием кода
"""

import sys
import os
import pytest

# Добавляем путь к корню проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Запуск всех MCP тестов"""
    # Базовые аргументы
    args = [
        "tests/mcp",  # Директория с тестами
        "-v",         # Подробный вывод
        "--tb=short", # Короткий traceback
    ]
    
    # Добавляем пользовательские аргументы
    args.extend(sys.argv[1:])
    
    # Опционально: покрытие кода
    if "--cov" in sys.argv:
        args.extend([
            "--cov=bot.mcp_agent",
            "--cov=bot.mcp_manager",
            "--cov=bot.services.mcp_service",
            "--cov=bot.formatters.mcp_formatter",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    print("🧪 Запуск тестов MCP...")
    print(f"📂 Директория: tests/mcp")
    print(f"🔧 Аргументы: {' '.join(args)}")
    print("-" * 50)
    
    # Запускаем pytest
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ Все тесты пройдены успешно!")
    else:
        print(f"\n❌ Тесты завершились с ошибкой (код: {exit_code})")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())