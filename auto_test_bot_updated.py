#!/usr/bin/env python3
"""
Автоматический тестер бота с мониторингом логов
Адаптирован под последние изменения (MCP, Docker, Cloudflare)
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import re
from colorama import init, Fore, Style
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Инициализация colorama
init(autoreset=True)

class BotAutoTester:
    """Автоматический тестер с мониторингом логов"""
    
    def __init__(self):
        # Динамическое определение URL
        self.base_url = self._detect_webhook_url()
        self.webhook_url = f"{self.base_url}/webhook"
        
        # Загружаем токены из .env
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = int(os.getenv("ADMIN_USER_ID", "229838448"))
        self.admin_username = os.getenv("ADMIN_USERNAME", "aaatema")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET_TOKEN", "default-secret-token")
        
        self.update_id = int(time.time() * 1000)
        self.log_file = "bot.log"
        self.log_monitor_thread = None
        self.monitoring = False
        self.log_buffer = []
        
    def _detect_webhook_url(self) -> str:
        """Определяет URL webhook на основе запущенных сервисов"""
        # Проверяем локальный сервер
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Обнаружен локальный сервер")
                return "http://localhost:8000"
        except:
            pass
            
        # Проверяем Cloudflare Tunnel через переменную окружения
        tunnel_url = os.getenv("TUNNEL_URL")
        if tunnel_url:
            print(f"{Fore.GREEN}✅ Используется Cloudflare Tunnel: {tunnel_url}")
            return tunnel_url
            
        # Проверяем ngrok
        try:
            import requests
            response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("tunnels"):
                    url = data["tunnels"][0]["public_url"]
                    print(f"{Fore.GREEN}✅ Используется ngrok: {url}")
                    return url
        except:
            pass
            
        # По умолчанию используем localhost
        print(f"{Fore.YELLOW}⚠️ Используется localhost по умолчанию")
        return "http://localhost:8000"
        
    def start_log_monitoring(self):
        """Запускает мониторинг логов в отдельном потоке"""
        self.monitoring = True
        self.log_monitor_thread = threading.Thread(target=self._monitor_logs)
        self.log_monitor_thread.daemon = True
        self.log_monitor_thread.start()
        
    def stop_log_monitoring(self):
        """Останавливает мониторинг логов"""
        self.monitoring = False
        if self.log_monitor_thread:
            self.log_monitor_thread.join(timeout=2)
    
    def _monitor_logs(self):
        """Следит за логами в реальном времени"""
        try:
            # Используем tail -f для отслеживания новых строк
            process = subprocess.Popen(
                ['tail', '-f', self.log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            while self.monitoring:
                line = process.stdout.readline()
                if line:
                    self.log_buffer.append(line.strip())
                    # Выводим важные логи
                    if any(key in line for key in ['📥', '📤', '✅', '❌', 'ERROR', 'Sending', 'MCP', 'Docker']):
                        self._print_log_line(line.strip())
                        
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка мониторинга логов: {e}")
    
    def _print_log_line(self, line: str):
        """Красиво выводит строку лога"""
        if 'ERROR' in line or '❌' in line:
            print(f"{Fore.RED}{line}")
        elif '✅' in line:
            print(f"{Fore.GREEN}{line}")
        elif '📥' in line or '📤' in line:
            print(f"{Fore.BLUE}{line}")
        elif 'Sending' in line:
            print(f"{Fore.YELLOW}{line}")
        elif 'MCP' in line:
            print(f"{Fore.MAGENTA}{line}")
        elif 'Docker' in line:
            print(f"{Fore.CYAN}{line}")
        else:
            print(line)
    
    def _create_update(self, text: str, is_admin: bool = True) -> Dict:
        """Создает Telegram Update объект"""
        self.update_id += 1
        user_id = self.chat_id if is_admin else 987654321
        username = self.admin_username if is_admin else "test_user"
        
        return {
            "update_id": self.update_id,
            "message": {
                "message_id": self.update_id,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": username,
                    "language_code": "ru"
                },
                "chat": {
                    "id": user_id,
                    "first_name": "Test",
                    "username": username,
                    "type": "private"
                },
                "date": int(time.time()),
                "text": text
            }
        }
    
    async def send_to_webhook(self, text: str, is_admin: bool = True) -> Tuple[bool, str]:
        """Отправляет сообщение в webhook"""
        update = self._create_update(text, is_admin)
        
        headers = {
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": self.webhook_secret
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=update,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    return response.status == 200, str(result)
            except Exception as e:
                return False, str(e)
    
    async def check_bot_response(self, wait_time: int = 3) -> Optional[Dict]:
        """Проверяет ответ бота через Telegram API"""
        await asyncio.sleep(wait_time)  # Ждем обработки
        
        # В тестовом режиме просто анализируем логи
        print(f"{Fore.YELLOW}⚠️ Проверка ответа через логи (Telegram API требует реального бота)")
        
        # Ищем в логах подтверждение отправки
        for line in reversed(self.log_buffer[-20:]):
            if "Response sent successfully" in line or "✅ Response sent" in line:
                return {"text": "Ответ отправлен (из логов)", "date": int(time.time())}
                
        return None
    
    def analyze_logs_for_errors(self) -> List[str]:
        """Анализирует буфер логов на наличие ошибок"""
        errors = []
        for line in self.log_buffer[-50:]:  # Последние 50 строк
            if any(error in line for error in ['ERROR', 'Failed', 'Exception', 'Traceback']):
                errors.append(line)
        return errors
    
    async def run_test(self, command: str, description: str, is_admin: bool = True):
        """Выполняет один тест"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}🧪 Тест: {description}")
        print(f"{Fore.CYAN}📝 Команда: {command}")
        print(f"{Fore.CYAN}👤 От имени: {'Админ' if is_admin else 'Обычный пользователь'}")
        print(f"{Fore.CYAN}{'='*60}")
        
        # Очищаем буфер логов
        self.log_buffer.clear()
        
        # Отправляем команду
        print(f"\n{Fore.YELLOW}📤 Отправка в webhook...")
        success, result = await self.send_to_webhook(command, is_admin)
        
        if success:
            print(f"{Fore.GREEN}✅ Webhook принял запрос: {result}")
        else:
            print(f"{Fore.RED}❌ Ошибка webhook: {result}")
            return
        
        # Ждем и проверяем ответ
        print(f"\n{Fore.YELLOW}⏳ Ожидание ответа бота...")
        bot_response = await self.check_bot_response()
        
        if bot_response:
            print(f"{Fore.GREEN}✅ Бот ответил:")
            print(f"{Fore.WHITE}   Текст: {bot_response.get('text', 'Нет текста')}")
        else:
            print(f"{Fore.YELLOW}⚠️ Ответ не обнаружен в логах")
            
        # Анализируем ошибки в логах
        errors = self.analyze_logs_for_errors()
        if errors:
            print(f"\n{Fore.RED}🔍 Найдены ошибки в логах:")
            for error in errors[:3]:  # Показываем первые 3 ошибки
                print(f"{Fore.RED}   - {error}")
    
    async def run_all_tests(self):
        """Запускает все тесты"""
        print(f"{Fore.MAGENTA}🚀 Запуск автоматического тестирования бота")
        print(f"{Fore.MAGENTA}📍 Webhook URL: {self.webhook_url}")
        print(f"{Fore.MAGENTA}👤 Admin ID: {self.chat_id}")
        print(f"{Fore.MAGENTA}🔑 Secret Token: {self.webhook_secret[:10]}...")
        
        # Проверяем доступность сервера
        print(f"\n{Fore.YELLOW}🔍 Проверка доступности сервера...")
        try:
            import requests
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✅ Сервер доступен")
                health_data = response.json()
                print(f"{Fore.WHITE}   Статус: {health_data}")
            else:
                print(f"{Fore.RED}❌ Сервер недоступен: {response.status_code}")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка подключения: {e}")
        
        # Запускаем мониторинг логов
        print(f"\n{Fore.YELLOW}📊 Запуск мониторинга логов...")
        self.start_log_monitoring()
        await asyncio.sleep(1)  # Даем время на запуск
        
        # Тесты для админа
        admin_tests = [
            ("/start", "Команда приветствия (админ)"),
            ("/help", "Команда помощи (админ)"),
            ("Привет, бот!", "Обычное сообщение"),
            ("/clear", "Очистка памяти"),
            ("/mcp status", "MCP статус"),
            ("/mcp health", "Проверка здоровья MCP серверов"),
            ("/db SELECT version()", "SQL запрос через MCP"),
            ("/docs react hooks", "Поиск документации"),
        ]
        
        print(f"\n{Fore.MAGENTA}📋 Тесты администратора")
        for command, description in admin_tests:
            await self.run_test(command, description, is_admin=True)
            await asyncio.sleep(2)  # Пауза между тестами
        
        # Тесты для обычного пользователя
        user_tests = [
            ("/start", "Команда приветствия (пользователь)"),
            ("/help", "Команда помощи (пользователь)"),
            ("/mcp_enable", "Запрос доступа к MCP"),
            ("Как дела?", "Обычное сообщение от пользователя"),
        ]
        
        print(f"\n{Fore.MAGENTA}📋 Тесты обычного пользователя")
        for command, description in user_tests:
            await self.run_test(command, description, is_admin=False)
            await asyncio.sleep(2)  # Пауза между тестами
        
        # Останавливаем мониторинг
        print(f"\n{Fore.YELLOW}📊 Остановка мониторинга логов...")
        self.stop_log_monitoring()
        
        # Финальный анализ
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}📋 ИТОГОВЫЙ ОТЧЕТ")
        print(f"{Fore.MAGENTA}{'='*60}")
        
        all_errors = self.analyze_logs_for_errors()
        if all_errors:
            print(f"{Fore.RED}❌ Обнаружено {len(all_errors)} ошибок")
            unique_errors = list(set(all_errors))[:5]  # Уникальные ошибки
            for i, error in enumerate(unique_errors, 1):
                print(f"{Fore.RED}{i}. {error}")
        else:
            print(f"{Fore.GREEN}✅ Ошибок не обнаружено")
            
        # Статистика из логов
        mcp_count = sum(1 for line in self.log_buffer if 'MCP' in line)
        docker_count = sum(1 for line in self.log_buffer if 'Docker' in line)
        
        print(f"\n{Fore.CYAN}📊 Статистика:")
        print(f"{Fore.CYAN}   - MCP упоминаний: {mcp_count}")
        print(f"{Fore.CYAN}   - Docker упоминаний: {docker_count}")
        print(f"{Fore.CYAN}   - Всего строк в логах: {len(self.log_buffer)}")


async def main():
    """Главная функция"""
    print(f"{Fore.YELLOW}🔍 Проверка окружения...")
    
    # Проверяем наличие .env
    if not os.path.exists(".env"):
        print(f"{Fore.RED}❌ Файл .env не найден!")
        print(f"{Fore.YELLOW}Создайте .env файл с необходимыми переменными")
        return
        
    # Проверяем необходимые переменные
    required_vars = ["TELEGRAM_BOT_TOKEN", "ADMIN_USER_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"{Fore.RED}❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        return
        
    tester = BotAutoTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # Устанавливаем необходимые пакеты если их нет
    try:
        import colorama
        import aiohttp
        import dotenv
    except ImportError:
        print("Установка необходимых пакетов...")
        subprocess.run([sys.executable, "-m", "pip", "install", "colorama", "aiohttp", "python-dotenv", "requests"])
        
    asyncio.run(main())