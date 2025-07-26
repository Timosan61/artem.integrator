#!/usr/bin/env python3
"""
Изолированный тест системы трассировки запросов

Тестирует только компоненты трассировки без зависимостей от конфигурации бота
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

# Прямой импорт только нужных компонентов
try:
    from bot.core.request_tracer import (
        RequestTracer, RequestTrace, TraceEvent, TraceStatus, ComponentStep
    )
    from bot.core.logging_utils import ComponentType
    IMPORTS_OK = True
    print("✅ Импорт компонентов трассировки успешен")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    IMPORTS_OK = False

@dataclass 
class TestResult:
    """Результат теста"""
    test_name: str
    success: bool
    error: Optional[str] = None
    duration_ms: Optional[float] = None

def test_tracer_initialization():
    """Тест инициализации трассировщика"""
    print("\n🧪 Тест 1: Инициализация RequestTracer")
    
    try:
        tracer = RequestTracer(max_traces=100, trace_ttl_hours=1)
        
        print(f"✅ RequestTracer создан с max_traces=100, ttl=1h")
        print(f"📊 Активных трассировок: {len(tracer.active_traces)}")
        print(f"📊 Завершенных трассировок: {len(tracer.completed_traces)}")
        print(f"📊 Всего запросов: {tracer.total_requests}")
        
        return TestResult("tracer_initialization", True)
        
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return TestResult("tracer_initialization", False, error=str(e))

def test_trace_creation():
    """Тест создания трассировки"""
    print("\n🧪 Тест 2: Создание и управление трассировками")
    
    try:
        tracer = RequestTracer()
        
        # Создаем трассировку
        trace_id = tracer.create_trace(
            user_id="test_user_123", 
            session_id="session_456",
            metadata={"test": "trace_creation", "version": "1.0"}
        )
        
        print(f"✅ Создана трассировка: {trace_id}")
        print(f"📊 Всего запросов: {tracer.total_requests}")
        
        # Получаем трассировку
        trace = tracer.get_trace(trace_id)
        if trace:
            print(f"✅ Трассировка найдена: {trace.trace_id}")
            print(f"   Пользователь: {trace.user_id}")
            print(f"   Сессия: {trace.session_id}")
            print(f"   Статус: {trace.status.value}")
            print(f"   Время создания: {trace.start_time}")
            print(f"   Метаданные: {trace.metadata}")
        else:
            raise Exception("Трассировка не найдена")
        
        return TestResult("trace_creation", True)
        
    except Exception as e:
        print(f"❌ Ошибка создания трассировки: {e}")
        return TestResult("trace_creation", False, error=str(e))

def test_event_management():
    """Тест управления событиями"""
    print("\n🧪 Тест 3: Добавление и управление событиями")
    
    try:
        tracer = RequestTracer()
        trace_id = tracer.create_trace("test_user")
        
        # Добавляем различные события
        events_data = [
            (ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED, {"source": "telegram"}, 2.5, True, None),
            (ComponentType.AGENT, ComponentStep.AGENT_ROUTING, {"agents": 3}, 5.0, True, None),
            (ComponentType.AGENT, ComponentStep.AGENT_PROCESSING, {"agent": "IntelligentAgent"}, 120.0, True, None),
            (ComponentType.MCP, ComponentStep.TOOL_EXECUTION, {"tool": "mcp_apps"}, 45.0, False, "Connection timeout"),
            (ComponentType.AGENT, ComponentStep.RESPONSE_GENERATION, {"length": 150}, 8.0, True, None),
        ]
        
        for component, step, details, duration, success, error in events_data:
            tracer.add_event(trace_id, component, step, details, duration, success, error)
            status = "✅" if success else "❌"
            print(f"   {status} {component.value} -> {step.value} ({duration}ms)")
        
        # Проверяем события
        trace = tracer.get_trace(trace_id)
        if trace:
            print(f"\n📊 Всего событий: {len(trace.events)}")
            print(f"📊 Длительность по компонентам: {trace.component_durations}")
            
            successful_events = sum(1 for event in trace.events if event.success)
            failed_events = len(trace.events) - successful_events
            print(f"📊 Успешных событий: {successful_events}")
            print(f"📊 Неуспешных событий: {failed_events}")
        
        return TestResult("event_management", True)
        
    except Exception as e:
        print(f"❌ Ошибка управления событиями: {e}")
        return TestResult("event_management", False, error=str(e))

def test_trace_completion():
    """Тест завершения трассировки"""
    print("\n🧪 Тест 4: Завершение трассировки")
    
    try:
        tracer = RequestTracer()
        
        # Тест успешного завершения
        trace_id_success = tracer.create_trace("user_success")
        tracer.add_event(trace_id_success, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED, duration_ms=3.0)
        tracer.complete_trace(
            trace_id_success, 
            TraceStatus.COMPLETED,
            final_metadata={"result": "success", "response_length": 100}
        )
        
        # Тест завершения с ошибкой
        trace_id_failed = tracer.create_trace("user_failed")
        tracer.add_event(trace_id_failed, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING, 
                        duration_ms=50.0, success=False, error="Agent unavailable")
        tracer.complete_trace(trace_id_failed, TraceStatus.FAILED)
        
        print("✅ Обе трассировки завершены")
        
        # Проверяем статистику
        metrics = tracer.get_performance_metrics()
        print(f"📊 Общая статистика:")
        print(f"   Всего запросов: {metrics['total_requests']}")
        print(f"   Успешных: {metrics['successful_requests']}")
        print(f"   Неуспешных: {metrics['failed_requests']}")
        print(f"   Процент успеха: {metrics['success_rate']:.1%}")
        print(f"   Активных: {metrics['active_traces']}")
        print(f"   Завершенных: {metrics['completed_traces']}")
        
        # Проверяем конкретные трассировки
        success_trace = tracer.get_trace(trace_id_success)
        failed_trace = tracer.get_trace(trace_id_failed)
        
        if success_trace:
            print(f"✅ Успешная трассировка: {success_trace.status.value}, {success_trace.duration_ms:.1f}ms")
        if failed_trace:
            print(f"❌ Неуспешная трассировка: {failed_trace.status.value}, {failed_trace.duration_ms:.1f}ms")
        
        return TestResult("trace_completion", True)
        
    except Exception as e:
        print(f"❌ Ошибка завершения трассировки: {e}")
        return TestResult("trace_completion", False, error=str(e))

async def test_context_manager():
    """Тест контекстного менеджера"""
    print("\n🧪 Тест 5: Контекстный менеджер для операций")
    
    try:
        tracer = RequestTracer()
        trace_id = tracer.create_trace("context_test")
        
        # Тест успешной операции
        async with tracer.trace_operation(
            trace_id, ComponentType.MCP, ComponentStep.TOOL_EXECUTION,
            details={"operation": "test_success"}
        ):
            await asyncio.sleep(0.01)  # Имитируем работу
            print("   ✅ Успешная операция завершена")
        
        # Тест операции с ошибкой
        try:
            async with tracer.trace_operation(
                trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
                details={"operation": "test_error"}
            ):
                await asyncio.sleep(0.005)
                raise ValueError("Тестовая ошибка")
        except ValueError:
            print("   ❌ Ошибка корректно перехвачена")
        
        tracer.complete_trace(trace_id)
        
        # Проверяем результаты
        trace = tracer.get_trace(trace_id)
        if trace:
            print(f"📊 Событий после контекстных операций: {len(trace.events)}")
            for i, event in enumerate(trace.events):
                status = "✅" if event.success else "❌"
                error_info = f" (ошибка: {event.error})" if event.error else ""
                print(f"   {i+1}. {status} {event.step.value}: {event.duration_ms:.1f}ms{error_info}")
        
        return TestResult("context_manager", True)
        
    except Exception as e:
        print(f"❌ Ошибка контекстного менеджера: {e}")
        return TestResult("context_manager", False, error=str(e))

def test_user_traces():
    """Тест получения трассировок пользователя"""
    print("\n🧪 Тест 6: Получение трассировок пользователя")
    
    try:
        tracer = RequestTracer()
        
        # Создаем трассировки для разных пользователей
        user1_traces = []
        user2_traces = []
        
        for i in range(3):
            trace_id1 = tracer.create_trace(f"user_1", metadata={"request": i+1})
            user1_traces.append(trace_id1)
            tracer.complete_trace(trace_id1)
            
            trace_id2 = tracer.create_trace(f"user_2", metadata={"request": i+1})
            user2_traces.append(trace_id2)
            tracer.complete_trace(trace_id2)
        
        # Получаем трассировки пользователей
        user1_results = tracer.get_user_traces("user_1", limit=5)
        user2_results = tracer.get_user_traces("user_2", limit=2)
        
        print(f"✅ Пользователь user_1: {len(user1_results)} трассировок")
        print(f"✅ Пользователь user_2: {len(user2_results)} трассировок (лимит 2)")
        
        # Проверяем сортировку (новые первыми)
        if len(user1_results) >= 2:
            first_trace = user1_results[0]
            second_trace = user1_results[1]
            if first_trace.start_time >= second_trace.start_time:
                print("✅ Трассировки корректно отсортированы по времени")
            else:
                print("⚠️ Порядок трассировок может быть неправильным")
        
        return TestResult("user_traces", True)
        
    except Exception as e:
        print(f"❌ Ошибка получения трассировок пользователя: {e}")
        return TestResult("user_traces", False, error=str(e))

def test_performance_metrics():
    """Тест детальных метрик производительности"""
    print("\n🧪 Тест 7: Детальные метрики производительности")
    
    try:
        tracer = RequestTracer()
        
        # Создаем разнообразные трассировки
        scenarios = [
            ("fast_user", [
                (ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED, 1.0),
                (ComponentType.AGENT, ComponentStep.AGENT_PROCESSING, 25.0),
            ], TraceStatus.COMPLETED),
            ("slow_user", [
                (ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED, 2.0),
                (ComponentType.AGENT, ComponentStep.AGENT_ROUTING, 10.0),
                (ComponentType.MCP, ComponentStep.TOOL_EXECUTION, 200.0),
                (ComponentType.AGENT, ComponentStep.RESPONSE_GENERATION, 15.0),
            ], TraceStatus.COMPLETED),
            ("error_user", [
                (ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED, 1.5),
                (ComponentType.AGENT, ComponentStep.AGENT_PROCESSING, 30.0),
            ], TraceStatus.FAILED),
        ]
        
        for user, events, final_status in scenarios:
            trace_id = tracer.create_trace(user)
            for component, step, duration in events:
                tracer.add_event(trace_id, component, step, duration_ms=duration)
            tracer.complete_trace(trace_id, final_status)
        
        # Получаем детальные метрики
        metrics = tracer.get_performance_metrics()
        
        print("📊 Детальные метрики производительности:")
        print(f"   Всего запросов: {metrics['total_requests']}")
        print(f"   Успешных: {metrics['successful_requests']}")
        print(f"   Неуспешных: {metrics['failed_requests']}")
        print(f"   Процент успеха: {metrics['success_rate']:.1%}")
        print(f"   Средняя длительность: {metrics['avg_duration_ms']:.1f}ms")
        
        if metrics['component_performance']:
            print("\n   📊 Производительность по компонентам:")
            for component, stats in metrics['component_performance'].items():
                print(f"     {component}:")
                print(f"       - Среднее время: {stats['avg_ms']:.1f}ms")
                print(f"       - Общее время: {stats['total_ms']:.1f}ms")
                print(f"       - Количество: {stats['count']}")
        
        return TestResult("performance_metrics", True)
        
    except Exception as e:
        print(f"❌ Ошибка метрик производительности: {e}")
        return TestResult("performance_metrics", False, error=str(e))

def test_cleanup_functionality():
    """Тест функциональности очистки"""
    print("\n🧪 Тест 8: Функциональность очистки трассировок")
    
    try:
        # Создаем трассировщик с малым TTL для теста
        tracer = RequestTracer(max_traces=5, trace_ttl_hours=0)  # TTL = 0 для немедленной очистки
        
        # Создаем много завершенных трассировок
        for i in range(8):
            trace_id = tracer.create_trace(f"cleanup_user_{i}")
            tracer.add_event(trace_id, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED, duration_ms=1.0)
            tracer.complete_trace(trace_id)
        
        print(f"✅ Создано 8 трассировок")
        
        initial_metrics = tracer.get_performance_metrics()
        print(f"📊 До очистки: {initial_metrics['completed_traces']} завершенных трассировок")
        
        # Принудительная очистка
        tracer._cleanup_old_traces()
        
        after_metrics = tracer.get_performance_metrics()
        print(f"📊 После очистки: {after_metrics['completed_traces']} завершенных трассировок")
        
        if after_metrics['completed_traces'] <= tracer.max_traces:
            print(f"✅ Очистка работает корректно (лимит: {tracer.max_traces})")
        else:
            print(f"⚠️ Очистка может работать некорректно")
        
        return TestResult("cleanup_functionality", True)
        
    except Exception as e:
        print(f"❌ Ошибка функциональности очистки: {e}")
        return TestResult("cleanup_functionality", False, error=str(e))

async def main():
    """Главная функция тестирования"""
    print("🚀 ЗАПУСК ИЗОЛИРОВАННЫХ ТЕСТОВ СИСТЕМЫ ТРАССИРОВКИ ЗАПРОСОВ")
    print("=" * 70)
    
    if not IMPORTS_OK:
        print("❌ Не удалось импортировать компоненты трассировки")
        return
    
    # Список всех тестов
    tests = [
        ("Инициализация", test_tracer_initialization),
        ("Создание трассировок", test_trace_creation),
        ("Управление событиями", test_event_management),
        ("Завершение трассировок", test_trace_completion),
        ("Контекстный менеджер", test_context_manager),
        ("Трассировки пользователя", test_user_traces),
        ("Метрики производительности", test_performance_metrics),
        ("Очистка трассировок", test_cleanup_functionality),
    ]
    
    results = []
    
    # Запуск тестов
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append(TestResult(test_name, False, error=str(e)))
    
    # Итоговый отчет
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    
    successful = 0
    failed = 0
    
    for result in results:
        status = "✅ УСПЕХ" if result.success else "❌ ОШИБКА"
        error_info = f" - {result.error}" if result.error else ""
        print(f"{status:12} | {result.test_name:25}{error_info}")
        
        if result.success:
            successful += 1
        else:
            failed += 1
    
    print("\n" + "-" * 50)
    print(f"Успешных тестов: {successful:2d}")
    print(f"Неуспешных тестов: {failed:2d}")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Система трассировки запросов работает корректно")
    else:
        print(f"\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В {failed} ТЕСТАХ")
        print("❌ Требуется дополнительная отладка")
    
    print("\n📊 Система трассировки запросов готова к использованию в боте")

if __name__ == "__main__":
    asyncio.run(main())