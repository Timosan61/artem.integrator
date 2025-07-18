"""
Мониторинг производительности и метрики
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil
import threading

from .logging import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """
    Монитор производительности
    
    Собирает метрики:
    - Время выполнения функций
    - Использование памяти
    - CPU нагрузка
    - Количество запросов
    - Ошибки
    """
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "errors": 0,
            "last_called": None,
            "history": deque(maxlen=100)  # Последние 100 вызовов
        })
        
        self.system_metrics = {
            "cpu_percent": deque(maxlen=60),  # Последняя минута
            "memory_percent": deque(maxlen=60),
            "memory_mb": deque(maxlen=60),
            "active_threads": deque(maxlen=60),
            "timestamp": deque(maxlen=60)
        }
        
        # Запускаем мониторинг системы
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_system(self):
        """Фоновый мониторинг системных ресурсов"""
        process = psutil.Process()
        
        while self._monitoring:
            try:
                # Собираем метрики
                cpu_percent = process.cpu_percent(interval=None)
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()
                memory_mb = memory_info.rss / 1024 / 1024
                threads = threading.active_count()
                
                # Сохраняем
                self.system_metrics["cpu_percent"].append(cpu_percent)
                self.system_metrics["memory_percent"].append(memory_percent)
                self.system_metrics["memory_mb"].append(memory_mb)
                self.system_metrics["active_threads"].append(threads)
                self.system_metrics["timestamp"].append(datetime.now())
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
            
            time.sleep(1)  # Обновляем каждую секунду
    
    def track_function(self, name: str, execution_time: float, error: Optional[Exception] = None):
        """Трекает выполнение функции"""
        metrics = self.metrics[name]
        
        metrics["count"] += 1
        metrics["total_time"] += execution_time
        metrics["min_time"] = min(metrics["min_time"], execution_time)
        metrics["max_time"] = max(metrics["max_time"], execution_time)
        metrics["last_called"] = datetime.now()
        
        if error:
            metrics["errors"] += 1
        
        # Добавляем в историю
        metrics["history"].append({
            "time": execution_time,
            "timestamp": datetime.now(),
            "error": error is not None
        })
    
    def get_function_stats(self, name: str) -> Dict[str, Any]:
        """Получает статистику функции"""
        metrics = self.metrics.get(name)
        if not metrics or metrics["count"] == 0:
            return {}
        
        avg_time = metrics["total_time"] / metrics["count"]
        
        return {
            "count": metrics["count"],
            "avg_time": avg_time,
            "min_time": metrics["min_time"],
            "max_time": metrics["max_time"],
            "total_time": metrics["total_time"],
            "errors": metrics["errors"],
            "error_rate": metrics["errors"] / metrics["count"],
            "last_called": metrics["last_called"].isoformat() if metrics["last_called"] else None
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Получает системную статистику"""
        if not self.system_metrics["cpu_percent"]:
            return {}
        
        return {
            "cpu": {
                "current": self.system_metrics["cpu_percent"][-1] if self.system_metrics["cpu_percent"] else 0,
                "avg_1min": sum(self.system_metrics["cpu_percent"]) / len(self.system_metrics["cpu_percent"])
            },
            "memory": {
                "current_mb": self.system_metrics["memory_mb"][-1] if self.system_metrics["memory_mb"] else 0,
                "current_percent": self.system_metrics["memory_percent"][-1] if self.system_metrics["memory_percent"] else 0,
                "avg_1min_mb": sum(self.system_metrics["memory_mb"]) / len(self.system_metrics["memory_mb"])
            },
            "threads": {
                "current": self.system_metrics["active_threads"][-1] if self.system_metrics["active_threads"] else 0,
                "max_1min": max(self.system_metrics["active_threads"]) if self.system_metrics["active_threads"] else 0
            }
        }
    
    def get_top_functions(self, limit: int = 10, sort_by: str = "count") -> List[Dict[str, Any]]:
        """Получает топ функций по метрике"""
        functions = []
        
        for name, metrics in self.metrics.items():
            if metrics["count"] > 0:
                stats = self.get_function_stats(name)
                stats["name"] = name
                functions.append(stats)
        
        # Сортируем
        if sort_by == "count":
            functions.sort(key=lambda x: x["count"], reverse=True)
        elif sort_by == "avg_time":
            functions.sort(key=lambda x: x["avg_time"], reverse=True)
        elif sort_by == "total_time":
            functions.sort(key=lambda x: x["total_time"], reverse=True)
        elif sort_by == "errors":
            functions.sort(key=lambda x: x["errors"], reverse=True)
        
        return functions[:limit]
    
    def reset_metrics(self):
        """Сбрасывает все метрики"""
        self.metrics.clear()
    
    def stop(self):
        """Останавливает мониторинг"""
        self._monitoring = False


# Глобальный монитор
_monitor = PerformanceMonitor()


def monitor_performance(name: Optional[str] = None):
    """
    Декоратор для мониторинга производительности
    
    Args:
        name: Имя метрики (по умолчанию имя функции)
    """
    def decorator(func):
        metric_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                execution_time = time.time() - start_time
                _monitor.track_function(metric_name, execution_time, error)
                
                if execution_time > 1:  # Логируем медленные операции
                    logger.warning(
                        f"Slow operation: {metric_name} took {execution_time:.2f}s",
                        extra={
                            "function": metric_name,
                            "execution_time": execution_time
                        }
                    )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                execution_time = time.time() - start_time
                _monitor.track_function(metric_name, execution_time, error)
                
                if execution_time > 1:  # Логируем медленные операции
                    logger.warning(
                        f"Slow operation: {metric_name} took {execution_time:.2f}s",
                        extra={
                            "function": metric_name,
                            "execution_time": execution_time
                        }
                    )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class Timer:
    """
    Контекстный менеджер для измерения времени
    
    Использование:
    ```python
    with Timer("operation_name") as timer:
        # код
        pass
    
    print(f"Took {timer.elapsed:.2f} seconds")
    ```
    """
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        
        _monitor.track_function(
            self.name, 
            self.elapsed, 
            exc_value if exc_type else None
        )
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        
        _monitor.track_function(
            self.name, 
            self.elapsed, 
            exc_value if exc_type else None
        )


def get_performance_stats() -> Dict[str, Any]:
    """Получает общую статистику производительности"""
    return {
        "system": _monitor.get_system_stats(),
        "top_functions_by_count": _monitor.get_top_functions(5, "count"),
        "top_functions_by_time": _monitor.get_top_functions(5, "total_time"),
        "slowest_functions": _monitor.get_top_functions(5, "avg_time"),
        "most_errors": _monitor.get_top_functions(5, "errors")
    }


def format_performance_report() -> str:
    """Форматирует отчет о производительности"""
    stats = get_performance_stats()
    
    lines = ["📊 Performance Report\n"]
    
    # Системные метрики
    system = stats.get("system", {})
    if system:
        lines.append("🖥️ System:")
        lines.append(f"  CPU: {system['cpu']['current']:.1f}% (avg: {system['cpu']['avg_1min']:.1f}%)")
        lines.append(f"  Memory: {system['memory']['current_mb']:.1f}MB ({system['memory']['current_percent']:.1f}%)")
        lines.append(f"  Threads: {system['threads']['current']}")
        lines.append("")
    
    # Топ функций
    for category, title in [
        ("top_functions_by_count", "🔥 Most Called"),
        ("slowest_functions", "🐌 Slowest"),
        ("most_errors", "❌ Most Errors")
    ]:
        functions = stats.get(category, [])
        if functions:
            lines.append(f"{title}:")
            for func in functions[:3]:
                if category == "top_functions_by_count":
                    lines.append(f"  • {func['name']}: {func['count']} calls")
                elif category == "slowest_functions":
                    lines.append(f"  • {func['name']}: {func['avg_time']:.3f}s avg")
                elif category == "most_errors":
                    lines.append(f"  • {func['name']}: {func['errors']} errors ({func['error_rate']:.1%})")
            lines.append("")
    
    return "\n".join(lines)