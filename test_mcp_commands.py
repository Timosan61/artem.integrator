#!/usr/bin/env python3
"""
Тестирование MCP команд через Telegram бота
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from colorama import init, Fore, Style
import subprocess

# Инициализация colorama
init(autoreset=True)

class MCPTester:
    """Тестер MCP функциональности"""
    
    def __init__(self):
        self.webhook_url = "https://16bf5c25554f.ngrok-free.app/webhook"
        self.bot_token = "6658269281:AAETA0vTXiRCMPcL1y_DzEeU_Fc6DiqdpFk"
        self.chat_id = 229838448
        self.admin_username = "aaatema"
        self.update_id = int(time.time() * 1000)
        self.log_process = None
        
    def start_log_monitoring(self):
        """Запускает мониторинг логов"""
        self.log_process = subprocess.Popen(
            ['tail', '-f', 'webhook.log'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
    def stop_log_monitoring(self):
        """Останавливает мониторинг логов"""
        if self.log_process:
            self.log_process.terminate()
            
    def print_logs(self):
        """Выводит последние строки логов с MCP"""
        try:
            result = subprocess.run(
                ['grep', '-E', 'MCP|mcp|supabase|digitalocean|context7', 'webhook.log', '-A', '2', '-B', '2'],
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(f"\n{Fore.CYAN}📋 Логи MCP:{Style.RESET_ALL}")
                for line in result.stdout.split('\n')[-20:]:  # Последние 20 строк
                    if 'ERROR' in line or '❌' in line:
                        print(f"{Fore.RED}{line}")
                    elif 'SUCCESS' in line or '✅' in line:
                        print(f"{Fore.GREEN}{line}")
                    elif 'MCP' in line or 'mcp' in line:
                        print(f"{Fore.YELLOW}{line}")
                    else:
                        print(line)
        except Exception as e:
            print(f"{Fore.RED}Ошибка чтения логов: {e}")
    
    def _create_update(self, text: str) -> dict:
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
    
    async def send_command(self, command: str, description: str):
        """Отправляет MCP команду и показывает результат"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}🧪 Тест: {description}")
        print(f"{Fore.CYAN}📝 Команда: {command}")
        print(f"{Fore.CYAN}{'='*60}")
        
        update = self._create_update(command)
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
                    if response.status == 200:
                        print(f"{Fore.GREEN}✅ Webhook принял запрос: {result}")
                    else:
                        print(f"{Fore.RED}❌ Ошибка webhook: {response.status}")
                        
            except Exception as e:
                print(f"{Fore.RED}❌ Ошибка отправки: {e}")
        
        # Ждем обработки
        await asyncio.sleep(3)
        
        # Показываем логи
        self.print_logs()
    
    async def run_tests(self):
        """Запускает все MCP тесты"""
        print(f"{Fore.MAGENTA}🚀 Тестирование MCP функциональности")
        print(f"{Fore.MAGENTA}📍 Webhook URL: {self.webhook_url}")
        print(f"{Fore.MAGENTA}👤 Admin User: @{self.admin_username} ({self.chat_id})")
        print(f"{Fore.MAGENTA}{'='*60}")
        
        # Сначала проверим, что MCP включен
        print(f"\n{Fore.YELLOW}🔍 Проверка конфигурации MCP...")
        result = subprocess.run(['grep', 'MCP_ENABLED', '.env'], capture_output=True, text=True)
        if 'true' in result.stdout:
            print(f"{Fore.GREEN}✅ MCP включен в .env")
        else:
            print(f"{Fore.RED}❌ MCP отключен в .env!")
            
        # Тесты MCP команд
        mcp_tests = [
            # Базовые MCP команды
            ("/mcp status", "Статус MCP серверов"),
            ("/mcp help", "Справка по MCP"),
            
            # Supabase команды
            ("/mcp projects", "Список Supabase проектов"),
            ("/mcp organizations", "Список организаций"),
            ("/db SELECT version()", "SQL запрос к базе"),
            
            # DigitalOcean команды  
            ("/mcp apps", "Список DigitalOcean приложений"),
            ("/mcp do apps", "Альтернативная команда DO apps"),
            
            # Context7 команды
            ("/docs react hooks", "Поиск документации React"),
            ("/mcp context7 vue composition", "Документация Vue"),
            
            # Проверка прав доступа
            ("/admin status", "Проверка админских прав"),
        ]
        
        # Запускаем мониторинг логов
        self.start_log_monitoring()
        
        try:
            for command, description in mcp_tests:
                await self.send_command(command, description)
                await asyncio.sleep(2)  # Пауза между тестами
                
        finally:
            self.stop_log_monitoring()
        
        # Итоговый анализ
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}📊 ИТОГОВЫЙ АНАЛИЗ MCP")
        print(f"{Fore.MAGENTA}{'='*60}")
        
        # Проверяем наличие MCP в логах
        result = subprocess.run(
            ['grep', '-c', 'MCP', 'webhook.log'],
            capture_output=True,
            text=True
        )
        mcp_count = int(result.stdout.strip() or 0)
        
        if mcp_count > 0:
            print(f"{Fore.GREEN}✅ MCP упоминается в логах {mcp_count} раз")
        else:
            print(f"{Fore.RED}❌ MCP не найден в логах - возможно отключен")
            
        # Проверяем ошибки MCP
        result = subprocess.run(
            ['grep', '-E', 'MCP.*ERROR|MCP.*error|MCP.*failed', 'webhook.log'],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"{Fore.RED}❌ Найдены ошибки MCP:")
            print(result.stdout)
        else:
            print(f"{Fore.GREEN}✅ Ошибок MCP не найдено")


async def main():
    """Главная функция"""
    tester = MCPTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())