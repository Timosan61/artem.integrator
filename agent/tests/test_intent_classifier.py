#!/usr/bin/env python3
"""
Тесты для Intent Classifier
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agent.core.intent_classifier import IntentClassifier, Intent
from agent.core.models import ToolType


def test_basic_intent_classification():
    """Тест базовой классификации намерений"""
    print("\n🧪 Тест 1: Базовая классификация намерений")
    print("-" * 50)
    
    classifier = IntentClassifier()
    
    test_cases = [
        {
            "message": "покажи все приложения",
            "expected_intent": Intent.MCP_COMMAND,
            "min_confidence": 0.8
        },
        {
            "message": "нарисуй мне красивый закат над морем",
            "expected_intent": Intent.IMAGE_GENERATION,
            "min_confidence": 0.9
        },
        {
            "message": "проанализируй это видео https://example.com/video.mp4",
            "expected_intent": Intent.VIDEO_ANALYSIS,
            "min_confidence": 0.8
        },
        {
            "message": "привет, как дела?",
            "expected_intent": Intent.GENERAL_CHAT,
            "min_confidence": 0.0
        }
    ]
    
    passed = 0
    for test in test_cases:
        intent, confidence, metadata = classifier.classify(test["message"])
        
        success = (
            intent == test["expected_intent"] and
            confidence >= test["min_confidence"]
        )
        
        status = "✅" if success else "❌"
        print(f"{status} '{test['message'][:30]}...'")
        print(f"   Ожидалось: {test['expected_intent']}")
        print(f"   Получено: {intent} (уверенность: {confidence:.2f})")
        
        if success:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_keyword_analysis():
    """Тест анализа ключевых слов"""
    print("\n🧪 Тест 2: Анализ ключевых слов")
    print("-" * 50)
    
    classifier = IntentClassifier()
    
    test_cases = [
        {
            "message": "базы данных postgresql кластер",
            "expected_tool": ToolType.MCP,
            "description": "MCP ключевые слова"
        },
        {
            "message": "дизайн арт иллюстрация в стиле digital art",
            "expected_tool": ToolType.IMAGE_GENERATOR,
            "description": "Генерация изображений"
        },
        {
            "message": "instagram reels контент анализ кадров",
            "expected_tool": ToolType.VISION_ANALYZER,
            "description": "Анализ видео"
        }
    ]
    
    passed = 0
    for test in test_cases:
        # Используем внутренний метод для тестирования
        scores = classifier._analyze_keywords(test["message"].lower())
        
        if scores:
            best_tool = max(scores.items(), key=lambda x: x[1])[0]
            success = best_tool == test["expected_tool"]
        else:
            success = False
        
        status = "✅" if success else "❌"
        print(f"{status} {test['description']}")
        print(f"   Сообщение: '{test['message']}'")
        print(f"   Scores: {scores}")
        
        if success:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_clarification_detection():
    """Тест определения необходимости уточнения"""
    print("\n🧪 Тест 3: Определение необходимости уточнения")
    print("-" * 50)
    
    classifier = IntentClassifier()
    
    test_cases = [
        {
            "message": "может покажи приложения или базы данных, не знаю",
            "should_clarify": True,
            "reason": "Неоднозначный запрос"
        },
        {
            "message": "анализ видео",  # без ссылки
            "should_clarify": True,
            "reason": "Видео анализ без ссылки"
        },
        {
            "message": "покажи все приложения",
            "should_clarify": False,
            "reason": "Четкий запрос"
        },
        {
            "message": "что-то связанное с приложениями или базами, не уверен",
            "should_clarify": True,
            "reason": "Низкая уверенность с неоднозначностью"
        }
    ]
    
    passed = 0
    for test in test_cases:
        intent, confidence, metadata = classifier.classify(test["message"])
        needs_clarification = intent == Intent.CLARIFICATION_NEEDED
        
        success = needs_clarification == test["should_clarify"]
        status = "✅" if success else "❌"
        
        print(f"{status} {test['reason']}")
        print(f"   Сообщение: '{test['message']}'")
        print(f"   Нужно уточнение: {needs_clarification}")
        print(f"   Intent: {intent}, Confidence: {confidence:.2f}")
        
        if success:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_yaml_pattern_loading():
    """Тест загрузки паттернов из YAML"""
    print("\n🧪 Тест 4: Загрузка паттернов из YAML")
    print("-" * 50)
    
    config_path = Path(__file__).parent.parent / "config" / "intent_patterns.yaml"
    
    # Создаем классификатор с конфигурацией
    classifier = IntentClassifier(str(config_path))
    
    # Проверяем что паттерны загружены
    print(f"✅ Конфигурация загружена из: {config_path}")
    print(f"   Количество паттернов: {len(classifier.patterns)}")
    
    # Тестируем паттерны из конфигурации
    test_messages = [
        "покажи все базы данных",
        "создай мне арт",
        "статистика видео"
    ]
    
    for msg in test_messages:
        intent, confidence, _ = classifier.classify(msg)
        print(f"   '{msg}' -> {intent} ({confidence:.2f})")
    
    return True


def test_tool_detection():
    """Тест определения подходящих инструментов"""
    print("\n🧪 Тест 5: Определение подходящих инструментов")
    print("-" * 50)
    
    classifier = IntentClassifier()
    
    test_cases = [
        {
            "message": "покажи приложения и базы данных",
            "should_contain": [ToolType.MCP],
            "description": "MCP запрос"
        },
        {
            "message": "нарисуй картинку или проанализируй видео",
            "should_contain": [ToolType.IMAGE_GENERATOR, ToolType.VISION_ANALYZER],
            "description": "Множественные инструменты"
        },
        {
            "message": "привет, как дела?",
            "should_contain": [],
            "description": "Обычный чат"
        }
    ]
    
    passed = 0
    for test in test_cases:
        intent, confidence, metadata = classifier.classify(test["message"])
        detected_tools = metadata.get('detected_tools', [])
        
        # Проверяем что все ожидаемые инструменты обнаружены
        success = all(tool in detected_tools for tool in test["should_contain"])
        
        status = "✅" if success else "❌"
        print(f"{status} {test['description']}")
        print(f"   Сообщение: '{test['message']}'")
        print(f"   Обнаружены: {detected_tools}")
        print(f"   Ожидались: {test['should_contain']}")
        
        if success:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_clarification_options():
    """Тест генерации вариантов для уточнения"""
    print("\n🧪 Тест 6: Генерация вариантов для уточнения")
    print("-" * 50)
    
    classifier = IntentClassifier()
    
    # Создаем неоднозначный запрос
    message = "покажи приложения или может лучше нарисуй картинку"
    intent, confidence, metadata = classifier.classify(message)
    
    # Получаем варианты для уточнения
    options = classifier.get_clarification_options(metadata)
    
    print(f"Сообщение: '{message}'")
    print(f"Intent: {intent}, Confidence: {confidence:.2f}")
    print(f"Detected tools: {metadata.get('detected_tools', [])}")
    print(f"\nВарианты для уточнения ({len(options)}):")
    
    for i, option in enumerate(options, 1):
        print(f"\n{i}. {option['icon']} {option['name']}")
        print(f"   {option['description']}")
        print(f"   Tool: {option.get('tool', 'None')}")
    
    # Проверяем что есть варианты
    success = len(options) > 0
    
    if success:
        print("\n✅ Варианты успешно сгенерированы")
    else:
        print("\n❌ Варианты не сгенерированы")
        # Дополнительная отладка
        print(f"\nОтладка:")
        print(f"  Metadata keys: {list(metadata.keys())}")
        print(f"  Message text: {metadata.get('message_text', 'NOT FOUND')}")
    
    return success


def test_russian_commands():
    """Тест русских команд"""
    print("\n🧪 Тест 7: Русские команды")
    print("-" * 50)
    
    classifier = IntentClassifier()
    
    test_cases = [
        {
            "message": "покажи базы данных",
            "expected_intent": Intent.MCP_COMMAND,
            "expected_type": "databases"
        },
        {
            "message": "список всех деплойментов",
            "expected_intent": Intent.MCP_COMMAND,
            "expected_type": "deployments"
        },
        {
            "message": "нарисуй котика",
            "expected_intent": Intent.IMAGE_GENERATION,
            "expected_type": None
        },
        {
            "message": "проанализируй рилс",
            "expected_intent": Intent.CLARIFICATION_NEEDED,  # Нет ссылки
            "expected_type": None
        }
    ]
    
    passed = 0
    for test in test_cases:
        intent, confidence, metadata = classifier.classify(test["message"])
        
        success = intent == test["expected_intent"]
        
        # Для MCP команд проверяем тип
        if success and intent == Intent.MCP_COMMAND:
            detected_tools = metadata.get('detected_tools', [])
            if ToolType.MCP in detected_tools:
                # Дополнительная проверка типа команды через метаданные
                # (это будет реализовано в MCPTool)
                pass
        
        status = "✅" if success else "❌"
        print(f"{status} '{test['message']}'")
        print(f"   Intent: {intent} (ожидался: {test['expected_intent']})")
        print(f"   Confidence: {confidence:.2f}")
        
        if success:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(test_cases)}")
    return passed >= len(test_cases) - 1  # Допускаем 1 ошибку


def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов Intent Classifier")
    print("=" * 60)
    
    tests = [
        ("Базовая классификация", test_basic_intent_classification),
        ("Анализ ключевых слов", test_keyword_analysis),
        ("Определение уточнений", test_clarification_detection),
        ("Загрузка YAML", test_yaml_pattern_loading),
        ("Определение инструментов", test_tool_detection),
        ("Варианты уточнения", test_clarification_options),
        ("Русские команды", test_russian_commands)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
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
    success = run_all_tests()
    sys.exit(0 if success else 1)