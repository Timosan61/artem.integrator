#!/usr/bin/env python3
"""
Тестирование системы трассировки запросов

Этот скрипт проверяет работу системы трассировки через всю архитектуру бота
"""

import asyncio
import sys
import os
from dataclasses import dataclass
from typing import Optional

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

try:
    from bot.core.request_tracer import request_tracer, ComponentType, ComponentStep, TraceStatus
    from bot.core.interfaces import Message, User, UserRole
    from bot.core.base_agent import ChainedAgent
    from bot.core.agent_adapters import IntelligentAgentAdapter, DefaultAgentAdapter
    IMPORTS_OK = True
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

async def test_basic_tracing():
    """Тест базовой функциональности трассировки"""
    print("\n🧪 Тест 1: Базовая трассировка запросов")
    
    try:
        # Создаем трассировку
        trace_id = request_tracer.create_trace(
            user_id="test_user_123",
            session_id="test_session_456",
            metadata={"test": "basic_tracing"}
        )
        
        print(f"✅ Создана трассировка: {trace_id}")
        
        # Добавляем события
        request_tracer.add_event(
            trace_id, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED,
            details={"message": "test message"}, duration_ms=5.0
        )
        
        request_tracer.add_event(
            trace_id, ComponentType.AGENT, ComponentStep.AGENT_ROUTING,
            details={"available_agents": 2}, duration_ms=10.0
        )
        
        request_tracer.add_event(
            trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
            details={"selected_agent": "IntelligentAgent"}, duration_ms=150.0
        )
        
        print("✅ Добавлены события трассировки")
        
        # Завершаем трассировку
        request_tracer.complete_trace(
            trace_id, TraceStatus.COMPLETED,
            final_metadata={"result": "success", "response_length": 100}
        )
        
        print("✅ Трассировка завершена")
        
        # Проверяем данные трассировки
        trace = request_tracer.get_trace(trace_id)
        if trace:
            print(f"📊 Длительность трассировки: {trace.duration_ms:.1f}ms")
            print(f"📊 Количество событий: {len(trace.events)}")
            print(f"📊 Статус: {trace.status.value}")
            print(f"📊 Длительность по компонентам: {trace.component_durations}")
        
        return TestResult("basic_tracing", True, duration_ms=trace.duration_ms if trace else None)
        
    except Exception as e:
        print(f"❌ Ошибка в базовом тесте: {e}")
        return TestResult("basic_tracing", False, error=str(e))

async def test_context_manager():
    """Тест контекстного менеджера для трассировки"""
    print("\n🧪 Тест 2: Контекстный менеджер трассировки")
    
    try:
        trace_id = request_tracer.create_trace("test_user_456", metadata={"test": "context_manager"})
        
        # Тест успешной операции
        async with request_tracer.trace_operation(
            trace_id, ComponentType.MCP, ComponentStep.TOOL_EXECUTION,
            details={"tool": "test_tool"}
        ):
            await asyncio.sleep(0.01)  # Имитируем работу
            print("✅ Успешная операция через контекстный менеджер")
        
        # Тест операции с ошибкой
        try:
            async with request_tracer.trace_operation(
                trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
                details={"agent": "test_agent"}
            ):
                await asyncio.sleep(0.005)
                raise ValueError("Тестовая ошибка")
        except ValueError:
            print("✅ Ошибка корректно обработана контекстным менеджером")
        
        request_tracer.complete_trace(trace_id, TraceStatus.COMPLETED)
        
        # Проверяем события
        trace = request_tracer.get_trace(trace_id)
        if trace and len(trace.events) >= 2:
            success_event = trace.events[0]
            error_event = trace.events[1]
            
            print(f"📊 Успешное событие: {success_event.success}, время: {success_event.duration_ms:.1f}ms")
            print(f"📊 Событие с ошибкой: {error_event.success}, ошибка: {error_event.error}")
            
        return TestResult("context_manager", True)
        
    except Exception as e:
        print(f"❌ Ошибка в тесте контекстного менеджера: {e}")
        return TestResult("context_manager", False, error=str(e))

async def test_performance_metrics():
    """Тест метрик производительности"""
    print("\n🧪 Тест 3: Метрики производительности")
    
    try:
        # Создаем несколько трассировок для статистики
        for i in range(3):
            trace_id = request_tracer.create_trace(f"test_user_{i}", metadata={"test": "performance"})
            
            # Добавляем различные события
            request_tracer.add_event(
                trace_id, ComponentType.WEBHOOK, ComponentStep.WEBHOOK_RECEIVED,
                duration_ms=2.0 + i
            )
            request_tracer.add_event(
                trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
                duration_ms=50.0 + i * 10
            )
            
            if i % 2 == 0:
                request_tracer.complete_trace(trace_id, TraceStatus.COMPLETED)
            else:
                request_tracer.complete_trace(trace_id, TraceStatus.FAILED)
        
        # Получаем метрики
        metrics = request_tracer.get_performance_metrics()
        
        print("📊 Метрики производительности:")
        print(f"   Всего запросов: {metrics['total_requests']}")
        print(f"   Успешных: {metrics['successful_requests']}")
        print(f"   Неуспешных: {metrics['failed_requests']}")
        print(f"   Процент успеха: {metrics['success_rate']:.1%}")
        print(f"   Средняя длительность: {metrics['avg_duration_ms']:.1f}ms")
        print(f"   Активных трассировок: {metrics['active_traces']}")
        print(f"   Завершенных трассировок: {metrics['completed_traces']}")
        
        if metrics['component_performance']:
            print("   Производительность по компонентам:")
            for component, stats in metrics['component_performance'].items():
                print(f"     {component}: {stats['avg_ms']:.1f}ms (среднее)")
        
        return TestResult("performance_metrics", True)
        
    except Exception as e:
        print(f"❌ Ошибка в тесте метрик: {e}")
        return TestResult("performance_metrics", False, error=str(e))

async def test_agent_integration():
    """Тест интеграции с системой агентов"""
    print("\n🧪 Тест 4: Интеграция с системой агентов")
    
    try:
        # Создаем тестовое сообщение
        test_user = User(id=12345, role=UserRole.ADMIN)
        test_message = Message(
            text="Тестовое сообщение для проверки трассировки",
            user=test_user,
            chat_id=67890
        )
        
        # Создаем агентов (если доступны)
        agents = []
        
        try:
            intelligent_agent = IntelligentAgentAdapter()
            agents.append(intelligent_agent)
            print("✅ IntelligentAgentAdapter создан")
        except Exception as e:
            print(f"⚠️ IntelligentAgent недоступен: {e}")
        
        try:
            default_agent = DefaultAgentAdapter()
            agents.append(default_agent)
            print("✅ DefaultAgentAdapter создан")
        except Exception as e:
            print(f"⚠️ DefaultAgent недоступен: {e}")
        
        if not agents:
            print("⚠️ Нет доступных агентов для теста")
            return TestResult("agent_integration", False, error="No agents available")
        
        # Создаем ChainedAgent
        chained_agent = ChainedAgent(agents)
        print(f"✅ ChainedAgent создан с {len(agents)} агентами")
        
        # Добавляем trace_id к сообщению
        trace_id = request_tracer.create_trace(
            str(test_user.id), 
            session_id=str(test_message.chat_id),
            metadata={"test": "agent_integration"}
        )
        test_message.trace_id = trace_id
        
        print(f"✅ Создана трассировка для агентов: {trace_id}")
        
        # Тестируем процесс can_handle (не process_message, чтобы избежать реальных вызовов)
        print("\n🔍 Тестируем проверку агентов...")
        for i, agent in enumerate(agents):
            try:
                can_handle = await agent.can_handle(test_message)
                print(f"   Агент {i+1} ({agent.get_name()}): can_handle = {can_handle}")
            except Exception as e:
                print(f"   Агент {i+1} ({agent.get_name()}): ошибка = {e}")
        
        request_tracer.complete_trace(trace_id, TraceStatus.COMPLETED)
        
        # Проверяем трассировку
        trace = request_tracer.get_trace(trace_id)
        if trace:
            print(f"\n📊 Результаты трассировки агентов:")
            print(f"   События: {len(trace.events)}")
            for event in trace.events:
                print(f"   - {event.component.value} -> {event.step.value}: {event.success}")
        
        return TestResult("agent_integration", True)
        
    except Exception as e:
        print(f"❌ Ошибка в тесте интеграции агентов: {e}")
        return TestResult("agent_integration", False, error=str(e))

async def test_cleanup():
    """Тест очистки старых трассировок"""
    print("\n🧪 Тест 5: Очистка трассировок")
    
    try:
        initial_metrics = request_tracer.get_performance_metrics()
        initial_completed = initial_metrics['completed_traces']
        
        print(f"📊 Начальное количество завершенных трассировок: {initial_completed}")
        
        # Принудительная очистка
        request_tracer._cleanup_old_traces()
        
        after_cleanup_metrics = request_tracer.get_performance_metrics()
        after_completed = after_cleanup_metrics['completed_traces']
        
        print(f"📊 После очистки: {after_completed}")
        print("✅ Очистка завершена успешно")
        
        return TestResult("cleanup", True)
        
    except Exception as e:
        print(f"❌ Ошибка в тесте очистки: {e}")
        return TestResult("cleanup", False, error=str(e))

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестов системы трассировки запросов")
    print("=" * 60)
    
    if not IMPORTS_OK:
        print("❌ Не удалось импортировать модули. Проверьте установку.")
        return
    
    # Список тестов
    tests = [
        test_basic_tracing,
        test_context_manager,
        test_performance_metrics,
        test_agent_integration,
        test_cleanup
    ]
    
    results = []
    
    # Запускаем тесты
    for test_func in tests:
        try:
            result = await test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test_func.__name__}: {e}")
            results.append(TestResult(test_func.__name__, False, error=str(e)))
    
    # Выводим итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for result in results:
        status = "✅ УСПЕХ" if result.success else "❌ ОШИБКА"
        duration_info = f" ({result.duration_ms:.1f}ms)" if result.duration_ms else ""
        error_info = f" - {result.error}" if result.error else ""
        
        print(f"{status}: {result.test_name}{duration_info}{error_info}")
        
        if result.success:
            successful += 1
        else:
            failed += 1
    
    print("\n" + "-" * 40)
    print(f"Успешных тестов: {successful}")
    print(f"Неуспешных тестов: {failed}")
    print(f"Общий результат: {'✅ ВСЕ ТЕСТЫ ПРОШЛИ' if failed == 0 else '❌ ЕСТЬ ОШИБКИ'}")
    
    # Финальные метрики
    try:
        final_metrics = request_tracer.get_performance_metrics()
        print(f"\n📊 Финальная статистика трассировщика:")
        print(f"   Всего запросов: {final_metrics['total_requests']}")
        print(f"   Активных трассировок: {final_metrics['active_traces']}")
        print(f"   Завершенных трассировок: {final_metrics['completed_traces']}")
    except Exception as e:
        print(f"⚠️ Не удалось получить финальные метрики: {e}")

if __name__ == "__main__":
    asyncio.run(main())