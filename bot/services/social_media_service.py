"""
SocialMedia Service для Telegram бота

Адаптированный из проекта SocialGirl для работы с YouTube, Instagram, TikTok API
Обеспечивает унифицированный поиск контента и получение аналитики
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from ..config import YOUTUBE_API_KEY, INSTAGRAM_API_KEY, TIKTOK_API_KEY

logger = logging.getLogger(__name__)


class SocialMediaService:
    """
    Основной класс для работы с социальными медиа API
    """
    
    def __init__(self):
        self.youtube_enabled = bool(YOUTUBE_API_KEY)
        self.instagram_enabled = bool(INSTAGRAM_API_KEY)
        self.tiktok_enabled = bool(TIKTOK_API_KEY)
        
        # Инициализируем стратегии
        self.strategies = {}
        
        if self.youtube_enabled:
            self.strategies['youtube'] = YouTubeStrategy()
            
        if self.instagram_enabled:
            self.strategies['instagram'] = InstagramStrategy()
            
        if self.tiktok_enabled:
            self.strategies['tiktok'] = TikTokStrategy()
        
        logger.info(f"✅ SocialMedia сервис инициализирован")
        logger.info(f"📊 Доступные платформы: {list(self.strategies.keys())}")
    
    async def search(self, platform: str, query: str, search_type: str = 'videos', limit: int = 10) -> List[Dict]:
        """
        Универсальный поиск по платформе
        
        Args:
            platform: Платформа (youtube, instagram, tiktok)
            query: Поисковый запрос
            search_type: Тип поиска (videos, channels, users)
            limit: Количество результатов
            
        Returns:
            List[Dict]: Список найденных элементов
        """
        if platform not in self.strategies:
            raise ValueError(f"Платформа '{platform}' не поддерживается или не настроена")
        
        strategy = self.strategies[platform]
        
        try:
            logger.info(f"🔍 Поиск на {platform}: '{query}' (тип: {search_type}, лимит: {limit})")
            results = await strategy.search(query, search_type, limit)
            logger.info(f"✅ Найдено {len(results)} результатов на {platform}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска на {platform}: {e}")
            raise
    
    async def get_channel_info(self, platform: str, channel_id: str) -> Dict:
        """
        Получение информации о канале/пользователе
        
        Args:
            platform: Платформа
            channel_id: ID канала/пользователя
            
        Returns:
            Dict: Информация о канале
        """
        if platform not in self.strategies:
            raise ValueError(f"Платформа '{platform}' не поддерживается")
        
        strategy = self.strategies[platform]
        
        if hasattr(strategy, 'get_channel_info'):
            return await strategy.get_channel_info(channel_id)
        else:
            raise NotImplementedError(f"Получение информации о канале не реализовано для {platform}")
    
    def get_available_platforms(self) -> List[str]:
        """
        Получить список доступных платформ
        
        Returns:
            List[str]: Список платформ
        """
        return list(self.strategies.keys())
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Получить статус сервиса
        
        Returns:
            Dict: Статус сервиса
        """
        return {
            'youtube_enabled': self.youtube_enabled,
            'instagram_enabled': self.instagram_enabled,
            'tiktok_enabled': self.tiktok_enabled,
            'available_platforms': self.get_available_platforms(),
            'strategies_count': len(self.strategies)
        }


class YouTubeStrategy:
    """
    Стратегия для работы с YouTube API
    """
    
    def __init__(self):
        self.base_url = 'https://www.googleapis.com/youtube/v3'
        self.api_key = YOUTUBE_API_KEY
        
    async def search(self, query: str, search_type: str, limit: int) -> List[Dict]:
        """
        Поиск на YouTube
        """
        import aiohttp
        
        if search_type == 'videos':
            return await self._search_videos(query, limit)
        elif search_type == 'channels':
            return await self._search_channels(query, limit)
        elif search_type == 'channel_videos':
            return await self._get_channel_videos(query, limit)
        else:
            raise ValueError(f"Неподдерживаемый тип поиска: {search_type}")
    
    async def _search_videos(self, query: str, limit: int) -> List[Dict]:
        """
        Поиск видео на YouTube
        """
        import aiohttp
        
        # Поиск видео
        search_url = f"{self.base_url}/search"
        search_params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'order': 'relevance',
            'maxResults': min(limit, 50),
            'key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=search_params) as response:
                if response.status != 200:
                    raise Exception(f"YouTube API ошибка: {response.status}")
                
                search_data = await response.json()
                
                if not search_data.get('items'):
                    return []
                
                # Получаем ID видео
                video_ids = [item['id']['videoId'] for item in search_data['items']]
                
                # Получаем статистику
                stats_url = f"{self.base_url}/videos"
                stats_params = {
                    'part': 'statistics,contentDetails',
                    'id': ','.join(video_ids),
                    'key': self.api_key
                }
                
                async with session.get(stats_url, params=stats_params) as stats_response:
                    if stats_response.status != 200:
                        raise Exception(f"YouTube Stats API ошибка: {stats_response.status}")
                    
                    stats_data = await stats_response.json()
                    
                    # Объединяем данные
                    results = []
                    stats_dict = {item['id']: item for item in stats_data.get('items', [])}
                    
                    for item in search_data['items']:
                        video_id = item['id']['videoId']
                        stats = stats_dict.get(video_id, {})
                        
                        result = {
                            'platform': 'youtube',
                            'id': video_id,
                            'title': item['snippet']['title'],
                            'description': item['snippet']['description'][:200] + '...' if len(item['snippet']['description']) > 200 else item['snippet']['description'],
                            'channel': item['snippet']['channelTitle'],
                            'published_at': item['snippet']['publishedAt'],
                            'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'views': int(stats.get('statistics', {}).get('viewCount', 0)),
                            'likes': int(stats.get('statistics', {}).get('likeCount', 0)),
                            'comments': int(stats.get('statistics', {}).get('commentCount', 0)),
                            'duration': stats.get('contentDetails', {}).get('duration', 'PT0S')
                        }
                        results.append(result)
                    
                    return results
    
    async def _search_channels(self, query: str, limit: int) -> List[Dict]:
        """
        Поиск каналов на YouTube
        """
        import aiohttp
        
        search_url = f"{self.base_url}/search"
        search_params = {
            'part': 'snippet',
            'q': query,
            'type': 'channel',
            'order': 'relevance',
            'maxResults': min(limit, 50),
            'key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=search_params) as response:
                if response.status != 200:
                    raise Exception(f"YouTube API ошибка: {response.status}")
                
                data = await response.json()
                
                results = []
                for item in data.get('items', []):
                    result = {
                        'platform': 'youtube',
                        'id': item['id']['channelId'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'][:200] + '...' if len(item['snippet']['description']) > 200 else item['snippet']['description'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                        'url': f"https://www.youtube.com/channel/{item['id']['channelId']}",
                        'published_at': item['snippet']['publishedAt']
                    }
                    results.append(result)
                
                return results
    
    async def _get_channel_videos(self, channel_handle: str, limit: int) -> List[Dict]:
        """
        Получение видео с канала по handle
        """
        import aiohttp
        
        # Сначала находим канал по handle
        channel_id = await self._get_channel_id_by_handle(channel_handle)
        if not channel_id:
            raise ValueError(f"Канал '{channel_handle}' не найден")
        
        # Получаем видео с канала
        search_url = f"{self.base_url}/search"
        search_params = {
            'part': 'snippet',
            'channelId': channel_id,
            'type': 'video',
            'order': 'date',
            'maxResults': min(limit, 50),
            'key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=search_params) as response:
                if response.status != 200:
                    raise Exception(f"YouTube API ошибка: {response.status}")
                
                data = await response.json()
                
                if not data.get('items'):
                    return []
                
                # Получаем статистику для видео
                video_ids = [item['id']['videoId'] for item in data['items']]
                return await self._get_videos_stats(video_ids)
    
    async def _get_channel_id_by_handle(self, handle: str) -> Optional[str]:
        """
        Получение ID канала по handle
        """
        import aiohttp
        
        clean_handle = handle.replace('@', '').strip()
        
        search_url = f"{self.base_url}/search"
        search_params = {
            'part': 'snippet',
            'q': clean_handle,
            'type': 'channel',
            'maxResults': 1,
            'key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=search_params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if data.get('items'):
                    return data['items'][0]['id']['channelId']
                
                return None
    
    async def _get_videos_stats(self, video_ids: List[str]) -> List[Dict]:
        """
        Получение статистики для видео
        """
        import aiohttp
        
        stats_url = f"{self.base_url}/videos"
        stats_params = {
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids),
            'key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(stats_url, params=stats_params) as response:
                if response.status != 200:
                    raise Exception(f"YouTube Stats API ошибка: {response.status}")
                
                data = await response.json()
                
                results = []
                for item in data.get('items', []):
                    result = {
                        'platform': 'youtube',
                        'id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'][:200] + '...' if len(item['snippet']['description']) > 200 else item['snippet']['description'],
                        'channel': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                        'url': f"https://www.youtube.com/watch?v={item['id']}",
                        'views': int(item.get('statistics', {}).get('viewCount', 0)),
                        'likes': int(item.get('statistics', {}).get('likeCount', 0)),
                        'comments': int(item.get('statistics', {}).get('commentCount', 0)),
                        'duration': item.get('contentDetails', {}).get('duration', 'PT0S')
                    }
                    results.append(result)
                
                return results
    
    async def get_channel_info(self, channel_id: str) -> Dict:
        """
        Получение информации о канале
        """
        import aiohttp
        
        url = f"{self.base_url}/channels"
        params = {
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"YouTube API ошибка: {response.status}")
                
                data = await response.json()
                
                if not data.get('items'):
                    raise ValueError(f"Канал '{channel_id}' не найден")
                
                item = data['items'][0]
                
                return {
                    'platform': 'youtube',
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                    'url': f"https://www.youtube.com/channel/{item['id']}",
                    'subscribers': int(item.get('statistics', {}).get('subscriberCount', 0)),
                    'video_count': int(item.get('statistics', {}).get('videoCount', 0)),
                    'view_count': int(item.get('statistics', {}).get('viewCount', 0)),
                    'created_at': item['snippet']['publishedAt']
                }


class InstagramStrategy:
    """
    Стратегия для работы с Instagram API
    (Заглушка - требует реализации с соответствующим API)
    """
    
    def __init__(self):
        self.api_key = INSTAGRAM_API_KEY
        
    async def search(self, query: str, search_type: str, limit: int) -> List[Dict]:
        """
        Поиск в Instagram
        """
        # Заглушка - требует реализации с Instagram API
        logger.warning("Instagram API не реализован")
        return []


class TikTokStrategy:
    """
    Стратегия для работы с TikTok API
    (Заглушка - требует реализации с соответствующим API)
    """
    
    def __init__(self):
        self.api_key = TIKTOK_API_KEY
        
    async def search(self, query: str, search_type: str, limit: int) -> List[Dict]:
        """
        Поиск в TikTok
        """
        # Заглушка - требует реализации с TikTok API
        logger.warning("TikTok API не реализован")
        return []


# Создаем глобальный экземпляр сервиса
social_media_service = SocialMediaService()