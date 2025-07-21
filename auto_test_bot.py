#!/usr/bin/env python3
"""
Автоматический тестер бота с мониторингом логов
Отправляет сообщения и следит за результатами в реальном времени
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

# Инициализация colorama
init(autoreset=True)

class BotAutoTester:
    """Автоматический тестер с мониторингом логов"""
    
    def __init__(self):
        self.webhook_url = "https://16bf5c25554f.ngrok-free.app/webhook"
        self.bot_token = "6658269281:AAETA0vTXiRCMPcL1y_DzEeU_Fc6DiqdpFk"
        self.chat_id = 229838448
        self.admin_username = "aaatema"
        self.update_id = int(time.time() * 1000)
        self.log_file = "webhook.log"
        self.log_monitor_thread = None
        self.monitoring = False
        self.log_buffer = []
        
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
                    if any(key in line for key in ['📥', '📤', '✅', '❌', 'ERROR', 'Sending']):
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
        else:
            print(line)
    
    def _create_update(self, text: str) -> Dict:
        """Создает Telegram Update объект"""
        self.update_id += 1
        return {
            "update_id": self.update_id,
            "message": {
                "message_id": self.update_id,
                "from": {
                    "id": self.chat_id,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": self.admin_username,
                    "language_code": "ru"
                },
                "chat": {
                    "id": self.chat_id,
                    "first_name": "Test",
                    "username": self.admin_username,
                    "type": "private"
                },
                "date": int(time.time()),
                "text": text
            }
        }
    
    async def send_to_webhook(self, text: str) -> Tuple[bool, str]:
        """Отправляет сообщение в webhook"""
        update = self._create_update(text)
        
        headers = {
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": "artyom_integrator_secret_2025"
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
        
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"offset": -10, "limit": 10}  # Последние 10 сообщений
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    if data.get("ok") and data.get("result"):
                        # Ищем сообщения от бота
                        for update in reversed(data["result"]):
                            msg = update.get("message", {})
                            if msg.get("from", {}).get("is_bot") and msg.get("chat", {}).get("id") == self.chat_id:
                                return msg
                return None
            except Exception as e:
                print(f"{Fore.RED}❌ Ошибка проверки ответа: {e}")
                return None
    
    def analyze_logs_for_errors(self) -> List[str]:
        """Анализирует буфер логов на наличие ошибок"""
        errors = []
        for line in self.log_buffer[-50:]:  # Последние 50 строк
            if 'ERROR' in line or 'Failed' in line or 'Exception' in line:
                errors.append(line)
        return errors
    
    async def run_test(self, command: str, description: str):
        """Выполняет один тест"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}🧪 Тест: {description}")
        print(f"{Fore.CYAN}📝 Команда: {command}")
        print(f"{Fore.CYAN}{'='*60}")
        
        # Очищаем буфер логов
        self.log_buffer.clear()
        
        # Отправляем команду
        print(f"\n{Fore.YELLOW}📤 Отправка в webhook...")
        success, result = await self.send_to_webhook(command)
        
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
            print(f"{Fore.WHITE}   Время: {datetime.fromtimestamp(bot_response.get('date', 0))}")
        else:
            print(f"{Fore.RED}❌ Бот не ответил")
            
            # Анализируем ошибки в логах
            errors = self.analyze_logs_for_errors()
            if errors:
                print(f"\n{Fore.RED}🔍 Найдены ошибки в логах:")
                for error in errors:
                    print(f"{Fore.RED}   - {error}")
    
    async def run_all_tests(self):
        """Запускает все тесты"""
        print(f"{Fore.MAGENTA}🚀 Запуск автоматического тестирования бота")
        print(f"{Fore.MAGENTA}📍 Webhook URL: {self.webhook_url}")
        print(f"{Fore.MAGENTA}👤 User ID: {self.chat_id}")
        
        # Запускаем мониторинг логов
        print(f"\n{Fore.YELLOW}📊 Запуск мониторинга логов...")
        self.start_log_monitoring()
        await asyncio.sleep(1)  # Даем время на запуск
        
        # Тесты
        tests = [
            ("/start", "Команда приветствия"),
            ("/help", "Команда помощи"),
            ("Привет", "Обычное сообщение"),
            ("/mcp status", "MCP статус"),
            ("/clear", "Очистка памяти")
        ]
        
        for command, description in tests:
            await self.run_test(command, description)
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
            for i, error in enumerate(all_errors[:5], 1):
                print(f"{Fore.RED}{i}. {error}")
        else:
            print(f"{Fore.GREEN}✅ Ошибок не обнаружено")


async def main():
    """Главная функция"""
    tester = BotAutoTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())