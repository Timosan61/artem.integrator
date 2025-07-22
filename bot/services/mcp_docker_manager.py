"""
MCP Docker Manager - управление MCP серверами через Docker
"""

import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
import docker
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPDockerManager:
    """
    Менеджер для управления MCP серверами в Docker контейнерах
    """
    
    def __init__(self):
        """Инициализация менеджера"""
        try:
            self.client = docker.from_env()
            self.enabled = True
            logger.info("✅ Docker client инициализирован")
        except Exception as e:
            logger.error(f"❌ Не удалось подключиться к Docker: {e}")
            self.client = None
            self.enabled = False
            
        self.mcp_servers = {
            "supabase": "artem-mcp-supabase",
            "digitalocean": "artem-mcp-digitalocean",
            "context7": "artem-mcp-context7",
            "cloudflare": "artem-mcp-cloudflare"
        }
    
    async def get_server_status(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает статус MCP сервера(ов)
        
        Args:
            server_name: Имя сервера или None для всех
            
        Returns:
            Dict со статусом
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Docker недоступен"
            }
            
        try:
            if server_name:
                # Статус одного сервера
                container_name = self.mcp_servers.get(server_name)
                if not container_name:
                    return {
                        "success": False,
                        "error": f"Неизвестный сервер: {server_name}"
                    }
                    
                try:
                    container = self.client.containers.get(container_name)
                    return {
                        "success": True,
                        "server": server_name,
                        "status": container.status,
                        "running": container.status == "running",
                        "health": self._get_container_health(container)
                    }
                except docker.errors.NotFound:
                    return {
                        "success": True,
                        "server": server_name,
                        "status": "not_found",
                        "running": False
                    }
            else:
                # Статус всех серверов
                statuses = {}
                for name, container_name in self.mcp_servers.items():
                    try:
                        container = self.client.containers.get(container_name)
                        statuses[name] = {
                            "status": container.status,
                            "running": container.status == "running",
                            "health": self._get_container_health(container)
                        }
                    except docker.errors.NotFound:
                        statuses[name] = {
                            "status": "not_found",
                            "running": False
                        }
                        
                return {
                    "success": True,
                    "servers": statuses
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_server(self, server_name: str) -> Dict[str, Any]:
        """
        Запускает MCP сервер
        
        Args:
            server_name: Имя сервера
            
        Returns:
            Dict с результатом
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Docker недоступен"
            }
            
        container_name = self.mcp_servers.get(server_name)
        if not container_name:
            return {
                "success": False,
                "error": f"Неизвестный сервер: {server_name}"
            }
            
        try:
            # Пробуем получить существующий контейнер
            try:
                container = self.client.containers.get(container_name)
                if container.status != "running":
                    container.start()
                    await asyncio.sleep(2)  # Даем время на запуск
                    
                return {
                    "success": True,
                    "message": f"Сервер {server_name} запущен"
                }
            except docker.errors.NotFound:
                # Контейнер не существует, создаем через docker-compose
                result = subprocess.run(
                    ["docker-compose", "up", "-d", f"mcp-{server_name}"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Сервер {server_name} создан и запущен"
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервера {server_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_server(self, server_name: str) -> Dict[str, Any]:
        """
        Останавливает MCP сервер
        
        Args:
            server_name: Имя сервера
            
        Returns:
            Dict с результатом
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Docker недоступен"
            }
            
        container_name = self.mcp_servers.get(server_name)
        if not container_name:
            return {
                "success": False,
                "error": f"Неизвестный сервер: {server_name}"
            }
            
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            
            return {
                "success": True,
                "message": f"Сервер {server_name} остановлен"
            }
            
        except docker.errors.NotFound:
            return {
                "success": True,
                "message": f"Сервер {server_name} не запущен"
            }
        except Exception as e:
            logger.error(f"❌ Ошибка остановки сервера {server_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def restart_server(self, server_name: str) -> Dict[str, Any]:
        """
        Перезапускает MCP сервер
        
        Args:
            server_name: Имя сервера
            
        Returns:
            Dict с результатом
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Docker недоступен"
            }
            
        # Останавливаем
        stop_result = await self.stop_server(server_name)
        if not stop_result["success"]:
            return stop_result
            
        # Ждем
        await asyncio.sleep(1)
        
        # Запускаем
        return await self.start_server(server_name)
    
    async def get_server_logs(self, server_name: str, lines: int = 50) -> Dict[str, Any]:
        """
        Получает логи MCP сервера
        
        Args:
            server_name: Имя сервера
            lines: Количество строк
            
        Returns:
            Dict с логами
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Docker недоступен"
            }
            
        container_name = self.mcp_servers.get(server_name)
        if not container_name:
            return {
                "success": False,
                "error": f"Неизвестный сервер: {server_name}"
            }
            
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            
            return {
                "success": True,
                "logs": logs,
                "lines": len(logs.split('\n'))
            }
            
        except docker.errors.NotFound:
            return {
                "success": False,
                "error": f"Контейнер {server_name} не найден"
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения логов {server_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_container_health(self, container) -> Optional[str]:
        """
        Получает health status контейнера
        
        Args:
            container: Docker контейнер
            
        Returns:
            Health status или None
        """
        try:
            if 'Health' in container.attrs['State']:
                return container.attrs['State']['Health']['Status']
        except:
            pass
        return None
    
    async def run_health_check(self) -> Dict[str, Any]:
        """
        Проверяет здоровье всех MCP серверов
        
        Returns:
            Dict с результатами проверки
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Docker недоступен"
            }
            
        health_results = {}
        unhealthy_count = 0
        
        for server_name in self.mcp_servers:
            status = await self.get_server_status(server_name)
            
            if status["success"]:
                is_healthy = (
                    status.get("running", False) and 
                    status.get("health") in ["healthy", None]
                )
                health_results[server_name] = {
                    "healthy": is_healthy,
                    "status": status.get("status", "unknown"),
                    "health": status.get("health")
                }
                
                if not is_healthy:
                    unhealthy_count += 1
            else:
                health_results[server_name] = {
                    "healthy": False,
                    "error": status.get("error")
                }
                unhealthy_count += 1
        
        return {
            "success": True,
            "healthy": unhealthy_count == 0,
            "unhealthy_count": unhealthy_count,
            "servers": health_results
        }


# Глобальный экземпляр менеджера
mcp_docker_manager = MCPDockerManager()