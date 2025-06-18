#!/usr/bin/env python3
"""
Скрипт автоматического деплоя через Portainer API
Используется для обновления стека textil-pro-bot
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

class PortainerAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def get_endpoints(self) -> list:
        """Получить список эндпоинтов"""
        response = requests.get(f"{self.base_url}/api/endpoints", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_stacks(self, endpoint_id: int = 2) -> list:
        """Получить список стеков"""
        response = requests.get(
            f"{self.base_url}/api/stacks",
            headers=self.headers,
            params={'endpointId': endpoint_id}
        )
        response.raise_for_status()
        return response.json()
    
    def find_stack_by_name(self, name: str, endpoint_id: int = 2) -> Optional[Dict[str, Any]]:
        """Найти стек по имени"""
        stacks = self.get_stacks(endpoint_id)
        for stack in stacks:
            if stack['Name'] == name:
                return stack
        return None
    
    def create_stack_from_git(self, 
                            stack_name: str,
                            repository_url: str,
                            compose_file: str = "docker-compose.yaml",
                            repository_reference: str = "refs/heads/main",
                            auto_update: bool = True,
                            env_vars: Dict[str, str] = None,
                            endpoint_id: int = 2) -> Dict[str, Any]:
        """Создать стек из Git репозитория"""
        
        payload = {
            "name": stack_name,
            "repositoryURL": repository_url,
            "repositoryReferenceName": repository_reference,
            "composeFile": compose_file,
            "autoUpdate": {
                "interval": "5m" if auto_update else "",
                "webhook": ""
            },
            "env": [{"name": k, "value": v} for k, v in (env_vars or {}).items()]
        }
        
        response = requests.post(
            f"{self.base_url}/api/stacks",
            headers=self.headers,
            params={'type': 2, 'method': 'repository', 'endpointId': endpoint_id},
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def update_stack(self, stack_id: int, endpoint_id: int = 2) -> Dict[str, Any]:
        """Обновить стек (принудительно подтянуть изменения из Git)"""
        
        response = requests.put(
            f"{self.base_url}/api/stacks/{stack_id}",
            headers=self.headers,
            params={'endpointId': endpoint_id},
            json={"pullImage": True}
        )
        response.raise_for_status()
        return response.json()
    
    def restart_stack(self, stack_id: int, endpoint_id: int = 2) -> bool:
        """Перезапустить все контейнеры в стеке"""
        
        # Сначала останавливаем стек
        stop_response = requests.post(
            f"{self.base_url}/api/stacks/{stack_id}/stop",
            headers=self.headers,
            params={'endpointId': endpoint_id}
        )
        stop_response.raise_for_status()
        
        time.sleep(3)  # Ждем остановки
        
        # Затем запускаем
        start_response = requests.post(
            f"{self.base_url}/api/stacks/{stack_id}/start",
            headers=self.headers,
            params={'endpointId': endpoint_id}
        )
        start_response.raise_for_status()
        
        return True
    
    def get_stack_logs(self, stack_name: str, lines: int = 50, endpoint_id: int = 2) -> str:
        """Получить логи контейнеров стека"""
        stack = self.find_stack_by_name(stack_name, endpoint_id)
        if not stack:
            return f"Стек {stack_name} не найден"
        
        # Получаем контейнеры стека
        containers_response = requests.get(
            f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/json",
            headers=self.headers,
            params={'filters': json.dumps({'label': [f'com.docker.compose.project={stack_name}']})}
        )
        containers_response.raise_for_status()
        containers = containers_response.json()
        
        logs = []
        for container in containers:
            container_id = container['Id']
            container_name = container['Names'][0].lstrip('/')
            
            # Получаем логи контейнера
            logs_response = requests.get(
                f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/logs",
                headers=self.headers,
                params={
                    'stdout': 1,
                    'stderr': 1,
                    'tail': lines,
                    'timestamps': 1
                }
            )
            
            if logs_response.status_code == 200:
                logs.append(f"=== {container_name} ===")
                logs.append(logs_response.text)
                logs.append("")
        
        return "\n".join(logs)
    
    def get_stack_status(self, stack_name: str, endpoint_id: int = 2) -> Dict[str, Any]:
        """Получить статус стека"""
        stack = self.find_stack_by_name(stack_name, endpoint_id)
        if not stack:
            return {"error": f"Стек {stack_name} не найден"}
        
        # Получаем контейнеры стека
        containers_response = requests.get(
            f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/json",
            headers=self.headers,
            params={'all': True, 'filters': json.dumps({'label': [f'com.docker.compose.project={stack_name}']})}
        )
        containers_response.raise_for_status()
        containers = containers_response.json()
        
        status = {
            "stack_id": stack['Id'],
            "stack_name": stack_name,
            "status": stack.get('Status', 'unknown'),
            "containers": []
        }
        
        for container in containers:
            status["containers"].append({
                "name": container['Names'][0].lstrip('/'),
                "state": container['State'],
                "status": container['Status'],
                "image": container['Image']
            })
        
        return status

def main():
    """Главная функция для выполнения команд деплоя"""
    
    # Конфигурация
    PORTAINER_URL = "http://185.135.83.197:9000"
    API_KEY = "ptr_W0/YcW+mOfXDut1onRvf7lYpOGn6yhHKu+5K/DrZt9Q="
    STACK_NAME = "textil-pro-bot"
    REPOSITORY_URL = "https://github.com/Timosan61/Textill_PRO_BOT.git"
    
    # Переменные окружения для стека
    ENV_VARS = {
        "TELEGRAM_BOT_TOKEN": "7902755829:AAH-WUhXSYq8NckAjFb22E-4D1O7ix_kzPM",
        "OPENAI_API_KEY": "test_key",
        "ZEP_API_KEY": "test_key",
        "BOT_USERNAME": "@textilprofi_bot"
    }
    
    portainer = PortainerAPI(PORTAINER_URL, API_KEY)
    
    # Обработка аргументов командной строки
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python portainer_deploy.py status     - проверить статус")
        print("  python portainer_deploy.py logs       - показать логи")
        print("  python portainer_deploy.py update     - обновить из Git")
        print("  python portainer_deploy.py restart    - перезапустить")
        print("  python portainer_deploy.py create     - создать новый стек")
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "status":
            print("🔍 Проверка статуса стека...")
            status = portainer.get_stack_status(STACK_NAME)
            print(json.dumps(status, indent=2, ensure_ascii=False))
        
        elif command == "logs":
            print("📝 Получение логов...")
            logs = portainer.get_stack_logs(STACK_NAME, lines=30)
            print(logs)
        
        elif command == "update":
            print("🔄 Обновление стека из Git...")
            stack = portainer.find_stack_by_name(STACK_NAME)
            if stack:
                result = portainer.update_stack(stack['Id'])
                print("✅ Стек обновлен:", result)
            else:
                print("❌ Стек не найден")
        
        elif command == "restart":
            print("🔄 Перезапуск стека...")
            stack = portainer.find_stack_by_name(STACK_NAME)
            if stack:
                portainer.restart_stack(stack['Id'])
                print("✅ Стек перезапущен")
            else:
                print("❌ Стек не найден")
        
        elif command == "create":
            print("🚀 Создание нового стека...")
            result = portainer.create_stack_from_git(
                STACK_NAME, 
                REPOSITORY_URL,
                env_vars=ENV_VARS,
                auto_update=True
            )
            print("✅ Стек создан:", result)
        
        else:
            print(f"❌ Неизвестная команда: {command}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка API: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()