"""
Cloudflare Tunnel Service - замена ngrok для webhook
"""

import logging
import asyncio
import aiohttp
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CloudflareTunnelService:
    """
    Сервис для работы с Cloudflare Tunnel
    Обеспечивает постоянный публичный URL для webhook
    """
    
    def __init__(self):
        """Инициализация сервиса"""
        self.tunnel_token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN")
        self.webhook_url = None
        self.tunnel_status = "disconnected"
        
        # Проверка наличия токена
        if not self.tunnel_token:
            logger.warning("⚠️ CLOUDFLARE_TUNNEL_TOKEN не установлен")
            
    async def get_tunnel_info(self) -> Dict[str, Any]:
        """
        Получает информацию о туннеле
        
        Returns:
            Dict с информацией о туннеле
        """
        try:
            # Cloudflare Tunnel предоставляет фиксированный URL
            # основанный на токене туннеля
            # Формат: https://[tunnel-id].trycloudflare.com
            # или кастомный домен если настроен
            
            # Для Docker контейнера cloudflared автоматически
            # создает туннель и предоставляет URL
            
            # Проверяем переменную окружения которую устанавливает cloudflared
            tunnel_url = os.getenv("TUNNEL_URL")
            
            if tunnel_url:
                self.webhook_url = f"{tunnel_url}/webhook"
                self.tunnel_status = "connected"
                
                logger.info(f"✅ Cloudflare Tunnel подключен: {tunnel_url}")
                
                return {
                    "status": "connected",
                    "url": tunnel_url,
                    "webhook_url": self.webhook_url,
                    "type": "cloudflare"
                }
            else:
                # Если URL еще не доступен, ждем
                logger.warning("⏳ Ожидание подключения Cloudflare Tunnel...")
                return {
                    "status": "connecting",
                    "url": None,
                    "webhook_url": None,
                    "type": "cloudflare"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о туннеле: {e}")
            return {
                "status": "error",
                "error": str(e),
                "url": None,
                "webhook_url": None,
                "type": "cloudflare"
            }
    
    async def wait_for_tunnel(self, max_attempts: int = 30) -> Optional[str]:
        """
        Ожидает подключения туннеля
        
        Args:
            max_attempts: Максимальное количество попыток
            
        Returns:
            URL туннеля или None
        """
        logger.info("⏳ Ожидание подключения Cloudflare Tunnel...")
        
        for attempt in range(max_attempts):
            info = await self.get_tunnel_info()
            
            if info["status"] == "connected" and info["url"]:
                return info["url"]
                
            # Ждем 2 секунды между попытками
            await asyncio.sleep(2)
            
        logger.error("❌ Не удалось дождаться подключения туннеля")
        return None
    
    async def setup_webhook(self, bot_token: str, webhook_secret: str) -> bool:
        """
        Устанавливает webhook для Telegram бота
        
        Args:
            bot_token: Токен Telegram бота
            webhook_secret: Секретный токен для webhook
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Получаем URL туннеля
            tunnel_url = await self.wait_for_tunnel()
            if not tunnel_url:
                return False
                
            webhook_url = f"{tunnel_url}/webhook"
            
            # Устанавливаем webhook в Telegram
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
                data = {
                    "url": webhook_url,
                    "secret_token": webhook_secret,
                    "allowed_updates": ["message", "callback_query", "inline_query"]
                }
                
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        logger.info(f"✅ Webhook установлен: {webhook_url}")
                        self.webhook_url = webhook_url
                        return True
                    else:
                        logger.error(f"❌ Ошибка установки webhook: {result}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Ошибка настройки webhook: {e}")
            return False
    
    def get_webhook_url(self) -> Optional[str]:
        """
        Возвращает текущий URL webhook
        
        Returns:
            URL webhook или None
        """
        return self.webhook_url
    
    def get_status(self) -> Dict[str, Any]:
        """
        Возвращает статус туннеля
        
        Returns:
            Dict со статусом
        """
        return {
            "type": "cloudflare",
            "status": self.tunnel_status,
            "webhook_url": self.webhook_url,
            "token_set": bool(self.tunnel_token)
        }


# Глобальный экземпляр сервиса
cloudflare_tunnel = CloudflareTunnelService()