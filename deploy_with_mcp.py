#!/usr/bin/env python3
"""
Deploy Artem Integrator using MCP DigitalOcean
Использует MCP для создания и управления приложением в DigitalOcean
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Добавляем путь к модулям бота
sys.path.append(str(Path(__file__).parent))

from bot.services.claude_code_service import claude_code_service
from bot.core.config import config


class MCPDeployer:
    """Класс для деплоя через MCP DigitalOcean"""
    
    def __init__(self):
        self.claude_service = claude_code_service
        self.app_name = "artem-integrator"
        self.region = "fra"  # Frankfurt region
        self.github_repo = "anetov/artem.integrator"
        self.github_branch = "main"
        
    async def check_mcp_status(self) -> bool:
        """Проверяет статус MCP"""
        print("🔌 Проверка MCP статуса...")
        
        result = await self.claude_service.execute_mcp_command("/mcp status")
        
        if result.get("success"):
            print("✅ MCP подключен и работает")
            print(f"📝 Ответ: {result.get('response', '')[:200]}...")
            return True
        else:
            print(f"❌ MCP не работает: {result.get('error')}")
            return False
    
    async def list_apps(self) -> Optional[Dict[str, Any]]:
        """Получает список приложений в DigitalOcean"""
        print("\n📱 Получение списка приложений...")
        
        result = await self.claude_service.execute_mcp_command("/mcp apps")
        
        if result.get("success"):
            print("✅ Список приложений получен")
            return result
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            return None
    
    async def create_app_spec(self) -> Dict[str, Any]:
        """Создает спецификацию приложения для DigitalOcean"""
        return {
            "name": self.app_name,
            "region": self.region,
            "services": [
                {
                    "name": "web",
                    "github": {
                        "repo": self.github_repo,
                        "branch": self.github_branch,
                        "deploy_on_push": True
                    },
                    "build_command": "pip install -r requirements.txt",
                    "run_command": "python -m uvicorn bot.webhook:app --host 0.0.0.0 --port 8080",
                    "environment_slug": "python",
                    "instance_size_slug": "basic-xs",
                    "instance_count": 1,
                    "http_port": 8080,
                    "health_check": {
                        "http_path": "/",
                        "initial_delay_seconds": 10,
                        "period_seconds": 30,
                        "timeout_seconds": 5,
                        "success_threshold": 1,
                        "failure_threshold": 3
                    },
                    "envs": [
                        {"key": "PYTHON_VERSION", "value": "3.10"},
                        {"key": "TELEGRAM_TOKEN", "value": "${TELEGRAM_TOKEN}", "type": "SECRET"},
                        {"key": "TELEGRAM_WEBHOOK_SECRET", "value": "${TELEGRAM_WEBHOOK_SECRET}", "type": "SECRET"},
                        {"key": "OPENAI_API_KEY", "value": "${OPENAI_API_KEY}", "type": "SECRET"},
                        {"key": "ANTHROPIC_API_KEY", "value": "${ANTHROPIC_API_KEY}", "type": "SECRET"},
                        {"key": "MCP_ENABLED", "value": "true"},
                        {"key": "SUPABASE_ENABLED", "value": "true"},
                        {"key": "SUPABASE_URL", "value": "${SUPABASE_URL}", "type": "SECRET"},
                        {"key": "SUPABASE_KEY", "value": "${SUPABASE_KEY}", "type": "SECRET"},
                        {"key": "DIGITALOCEAN_ENABLED", "value": "true"},
                        {"key": "DIGITALOCEAN_TOKEN", "value": "${DIGITALOCEAN_TOKEN}", "type": "SECRET"},
                        {"key": "CONTEXT7_ENABLED", "value": "true"},
                        {"key": "VOICE_ENABLED", "value": "true"},
                        {"key": "ENVIRONMENT", "value": "production"}
                    ]
                }
            ]
        }
    
    async def create_app(self) -> Optional[str]:
        """Создает приложение в DigitalOcean через MCP"""
        print(f"\n🚀 Создание приложения {self.app_name}...")
        
        # Генерируем спецификацию
        app_spec = await self.create_app_spec()
        
        # Команда для создания приложения через MCP
        command = f"/mcp create app {json.dumps(app_spec)}"
        
        result = await self.claude_service.execute_mcp_command(command)
        
        if result.get("success"):
            print("✅ Приложение создано успешно")
            # Извлекаем ID приложения из ответа
            app_id = self._extract_app_id(result.get("response", ""))
            return app_id
        else:
            print(f"❌ Ошибка создания приложения: {result.get('error')}")
            return None
    
    async def get_app_status(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Получает статус приложения"""
        print(f"\n📊 Проверка статуса приложения {app_id}...")
        
        command = f"/mcp get app {app_id}"
        result = await self.claude_service.execute_mcp_command(command)
        
        if result.get("success"):
            print("✅ Статус получен")
            return result
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            return None
    
    async def get_deployment_logs(self, app_id: str) -> Optional[str]:
        """Получает логи деплоя"""
        print(f"\n📝 Получение логов деплоя для {app_id}...")
        
        command = f"/mcp logs {app_id}"
        result = await self.claude_service.execute_mcp_command(command)
        
        if result.get("success"):
            print("✅ Логи получены")
            return result.get("response")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            return None
    
    async def update_app_env(self, app_id: str, env_vars: Dict[str, str]) -> bool:
        """Обновляет переменные окружения приложения"""
        print(f"\n🔧 Обновление переменных окружения для {app_id}...")
        
        # Формируем команду для обновления
        env_list = [{"key": k, "value": v, "type": "SECRET"} for k, v in env_vars.items()]
        command = f"/mcp update app {app_id} env {json.dumps(env_list)}"
        
        result = await self.claude_service.execute_mcp_command(command)
        
        if result.get("success"):
            print("✅ Переменные окружения обновлены")
            return True
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            return False
    
    async def trigger_deployment(self, app_id: str) -> bool:
        """Запускает новый деплой"""
        print(f"\n🚀 Запуск нового деплоя для {app_id}...")
        
        command = f"/mcp deploy {app_id}"
        result = await self.claude_service.execute_mcp_command(command)
        
        if result.get("success"):
            print("✅ Деплой запущен")
            return True
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            return False
    
    def _extract_app_id(self, response: str) -> Optional[str]:
        """Извлекает ID приложения из ответа"""
        # Простой парсинг - ищем паттерн app ID
        import re
        match = re.search(r'app[_-]?id["\s:]+([a-f0-9-]+)', response, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    async def full_deploy(self):
        """Полный процесс деплоя"""
        print("🚀 Начинаем деплой Artem Integrator через MCP DigitalOcean")
        print("=" * 60)
        
        # 1. Проверяем MCP
        if not await self.check_mcp_status():
            print("\n❌ MCP не настроен. Проверьте конфигурацию.")
            return
        
        # 2. Проверяем существующие приложения
        apps = await self.list_apps()
        
        # 3. Создаем или обновляем приложение
        app_id = None
        
        if apps and "artem-integrator" in str(apps):
            print("\n⚠️ Приложение уже существует")
            # TODO: Извлечь ID существующего приложения
        else:
            app_id = await self.create_app()
            
            if not app_id:
                print("\n❌ Не удалось создать приложение")
                return
        
        # 4. Ждем готовности
        print("\n⏳ Ожидание готовности приложения...")
        await asyncio.sleep(30)
        
        # 5. Проверяем статус
        if app_id:
            status = await self.get_app_status(app_id)
            if status:
                print(f"\n📊 Статус: {status.get('response', '')[:200]}...")
        
        # 6. Получаем логи
        if app_id:
            logs = await self.get_deployment_logs(app_id)
            if logs:
                print(f"\n📝 Последние логи:\n{logs[:500]}...")
        
        print("\n✅ Процесс деплоя завершен!")
        print("\n📋 Дальнейшие шаги:")
        print("1. Проверьте приложение в DigitalOcean App Platform")
        print("2. Настройте переменные окружения через панель управления")
        print("3. Настройте webhook URL в Telegram после получения домена")
        print("4. Мониторьте логи через DigitalOcean или MCP команды")


async def main():
    """Главная функция"""
    deployer = MCPDeployer()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            await deployer.check_mcp_status()
        elif command == "list":
            await deployer.list_apps()
        elif command == "deploy":
            await deployer.full_deploy()
        elif command == "logs" and len(sys.argv) > 2:
            app_id = sys.argv[2]
            await deployer.get_deployment_logs(app_id)
        else:
            print("Использование:")
            print("  python deploy_with_mcp.py status  - проверить MCP")
            print("  python deploy_with_mcp.py list    - список приложений")
            print("  python deploy_with_mcp.py deploy  - полный деплой")
            print("  python deploy_with_mcp.py logs <app_id> - логи приложения")
    else:
        # По умолчанию запускаем полный деплой
        await deployer.full_deploy()


if __name__ == "__main__":
    asyncio.run(main())