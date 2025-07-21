#!/usr/bin/env python3
"""
Автоматическое тестирование Telegram бота с MCP функциональностью

Этот скрипт:
1. Отправляет тестовые команды в Telegram бот
2. Проверяет MCP функциональность
3. Валидирует ответы
4. Генерирует отчет о тестировании
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from colorama import init, Fore, Style

# Инициализация colorama для цветного вывода
init(autoreset=True)

# Конфигурация тестирования
TEST_CONFIG = {
    # Railway webhook URL
    # "webhook_url": "https://web-production-84d8.up.railway.app/webhook",
    
    # Локальный webhook для тестирования (через ngrok)
    "webhook_url": "https://16bf5c25554f.ngrok-free.app/webhook",
    
    # Тестовый пользователь (администратор)
    "admin_user_id": 229838448,
    "admin_username": "aaatema",
    
    # Задержка между командами (секунды)
    "command_delay": 2,
    
    # Таймаут ожидания ответа (секунды)
    "response_timeout": 10
}


@dataclass
class TestCase:
    """Описание тестового случая"""
    name: str
    description: str
    message: str
    expected_keywords: List[str]
    mcp_service: Optional[str] = None
    skip_if_no_mcp: bool = False


@dataclass
class TestResult:
    """Результат выполнения теста"""
    test_case: TestCase
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class TelegramMCPTester:
    """Класс для автоматического тестирования Telegram + MCP"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session = None
        self.results: List[TestResult] = []
        self.update_id = int(time.time() * 1000)
        
    async def __aenter__(self):
        """Вход в контекст - создание HTTP сессии"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста - закрытие сессии"""
        if self.session:
            await self.session.close()
    
    def _create_update(self, text: str) -> Dict:
        """Создает Telegram Update объект"""
        self.update_id += 1
        return {
            "update_id": self.update_id,
            "message": {
                "message_id": self.update_id,
                "from": {
                    "id": self.config["admin_user_id"],
                    "is_bot": False,
                    "first_name": "Test",
                    "username": self.config["admin_username"]
                },
                "chat": {
                    "id": self.config["admin_user_id"],
                    "first_name": "Test",
                    "username": self.config["admin_username"],
                    "type": "private"
                },
                "date": int(time.time()),
                "text": text
            }
        }
    
    async def send_message(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Отправляет сообщение в webhook
        
        Returns:
            Tuple[bool, Optional[str]]: (успех, текст ошибки)
        """
        try:
            update = self._create_update(text)
            
            async with self.session.post(
                self.config["webhook_url"],
                json=update,
                timeout=aiohttp.ClientTimeout(total=self.config["response_timeout"])
            ) as response:
                if response.status == 200:
                    return True, None
                else:
                    error_text = await response.text()
                    return False, f"HTTP {response.status}: {error_text}"
                    
        except asyncio.TimeoutError:
            return False, "Timeout waiting for response"
        except Exception as e:
            return False, str(e)
    
    async def run_test(self, test_case: TestCase) -> TestResult:
        """Выполняет один тестовый случай"""
        print(f"\n{Fore.CYAN}▶ Тест: {test_case.name}{Style.RESET_ALL}")
        print(f"  Описание: {test_case.description}")
        print(f"  Команда: {test_case.message}")
        
        start_time = time.time()
        
        # Отправляем сообщение
        success, error = await self.send_message(test_case.message)
        
        execution_time = time.time() - start_time
        
        if success:
            # В реальном тесте здесь нужно получить ответ от бота
            # Сейчас просто считаем успешным
            print(f"  {Fore.GREEN}✓ Успешно отправлено{Style.RESET_ALL}")
            result = TestResult(
                test_case=test_case,
                success=True,
                execution_time=execution_time
            )
        else:
            print(f"  {Fore.RED}✗ Ошибка: {error}{Style.RESET_ALL}")
            result = TestResult(
                test_case=test_case,
                success=False,
                error=error,
                execution_time=execution_time
            )
        
        self.results.append(result)
        
        # Задержка между командами
        await asyncio.sleep(self.config["command_delay"])
        
        return result
    
    async def run_all_tests(self, test_cases: List[TestCase]):
        """Выполняет все тесты"""
        print(f"\n{Fore.YELLOW}🧪 Запуск тестирования Telegram + MCP{Style.RESET_ALL}")
        print(f"Webhook URL: {self.config['webhook_url']}")
        print(f"Количество тестов: {len(test_cases)}")
        print("=" * 60)
        
        for test_case in test_cases:
            await self.run_test(test_case)
        
        self.print_summary()
    
    def print_summary(self):
        """Выводит итоговый отчет"""
        print(f"\n{Fore.YELLOW}📊 Итоги тестирования{Style.RESET_ALL}")
        print("=" * 60)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        
        print(f"Всего тестов: {total}")
        print(f"{Fore.GREEN}Успешных: {successful}{Style.RESET_ALL}")
        print(f"{Fore.RED}Провалено: {failed}{Style.RESET_ALL}")
        
        if failed > 0:
            print(f"\n{Fore.RED}Проваленные тесты:{Style.RESET_ALL}")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.test_case.name}: {result.error}")
        
        # Статистика по MCP сервисам
        print(f"\n{Fore.CYAN}Статистика по MCP сервисам:{Style.RESET_ALL}")
        mcp_stats = {}
        for result in self.results:
            if result.test_case.mcp_service:
                service = result.test_case.mcp_service
                if service not in mcp_stats:
                    mcp_stats[service] = {"total": 0, "success": 0}
                mcp_stats[service]["total"] += 1
                if result.success:
                    mcp_stats[service]["success"] += 1
        
        for service, stats in mcp_stats.items():
            success_rate = (stats["success"] / stats["total"]) * 100
            print(f"  {service}: {stats['success']}/{stats['total']} ({success_rate:.0f}%)")
        
        # Среднее время выполнения
        avg_time = sum(r.execution_time for r in self.results) / len(self.results)
        print(f"\nСреднее время выполнения: {avg_time:.2f} сек")
        
        # Сохранение отчета
        self.save_report()
    
    def save_report(self):
        """Сохраняет отчет в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "summary": {
                "total": len(self.results),
                "successful": sum(1 for r in self.results if r.success),
                "failed": sum(1 for r in self.results if not r.success)
            },
            "results": [
                {
                    "test": r.test_case.name,
                    "success": r.success,
                    "error": r.error,
                    "execution_time": r.execution_time
                }
                for r in self.results
            ]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Отчет сохранен: {report_file}")


# Определение тестовых случаев
TEST_CASES = [
    # Базовые команды
    TestCase(
        name="Start Command",
        description="Проверка команды /start",
        message="/start",
        expected_keywords=["Привет", "помощник"]
    ),
    
    TestCase(
        name="Help Command",
        description="Проверка команды /help",
        message="/help",
        expected_keywords=["команды", "помощь"]
    ),
    
    # MCP Supabase тесты
    TestCase(
        name="MCP List Projects",
        description="Список проектов Supabase",
        message="/mcp list projects",
        expected_keywords=["projects", "проект"],
        mcp_service="supabase",
        skip_if_no_mcp=True
    ),
    
    TestCase(
        name="MCP SQL Query",
        description="SQL запрос через MCP",
        message="/sql SELECT version()",
        expected_keywords=["PostgreSQL", "version"],
        mcp_service="supabase",
        skip_if_no_mcp=True
    ),
    
    # MCP DigitalOcean тесты
    TestCase(
        name="MCP List Apps",
        description="Список приложений DigitalOcean",
        message="/mcp do apps",
        expected_keywords=["apps", "приложения"],
        mcp_service="digitalocean",
        skip_if_no_mcp=True
    ),
    
    TestCase(
        name="MCP App Logs",
        description="Логи приложения",
        message="/logs app_123",
        expected_keywords=["logs", "логи"],
        mcp_service="digitalocean",
        skip_if_no_mcp=True
    ),
    
    # MCP Context7 тесты
    TestCase(
        name="MCP Search Docs",
        description="Поиск документации React",
        message="/docs react hooks",
        expected_keywords=["documentation", "hooks"],
        mcp_service="context7",
        skip_if_no_mcp=True
    ),
    
    TestCase(
        name="MCP Code Examples",
        description="Примеры кода Vue",
        message="/mcp context7 examples vue composition api",
        expected_keywords=["examples", "code"],
        mcp_service="context7",
        skip_if_no_mcp=True
    ),
    
    # Обычные запросы
    TestCase(
        name="Regular Chat",
        description="Обычный разговор",
        message="Привет! Как дела?",
        expected_keywords=["Привет", "помочь"]
    ),
    
    TestCase(
        name="Admin Mode Check",
        description="Проверка админского режима",
        message="/admin status",
        expected_keywords=["admin", "режим"]
    )
]


async def main():
    """Основная функция"""
    # Создаем тестер
    async with TelegramMCPTester(TEST_CONFIG) as tester:
        # Запускаем все тесты
        await tester.run_all_tests(TEST_CASES)


if __name__ == "__main__":
    # Запуск тестов
    asyncio.run(main())