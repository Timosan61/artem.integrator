"""
YouTube Transcript Service для Artyom Integrator

Сервис для получения транскрипций YouTube видео.
Принимает ссылку на видео и возвращает .txt файл с полной транскрипцией.
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)


class YouTubeTranscriptService:
    """
    Сервис для получения транскрипций YouTube видео
    """
    
    def __init__(self):
        self.supported_languages = ['ru', 'en', 'uk', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh']
        logger.info("✅ YouTube Transcript Service инициализирован")
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Извлекает ID видео из YouTube URL
        
        Args:
            url: URL видео
            
        Returns:
            str: ID видео или None
        """
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v%3D([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'(?:m\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Если это уже video ID (11 символов)
        if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
            
        return None
    
    def get_transcript(self, video_url: str, language: str = 'ru') -> Dict[str, Any]:
        """
        Получает транскрипцию видео
        
        Args:
            video_url: URL или ID видео
            language: Предпочтительный язык ('ru', 'en', и т.д.)
            
        Returns:
            Dict: Результат с транскрипцией или ошибкой
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api.formatters import TextFormatter
            
            # Извлекаем ID видео
            video_id = self.extract_video_id(video_url)
            if not video_id:
                return {
                    'success': False,
                    'error': 'Не удалось извлечь ID видео из URL',
                    'url': video_url
                }
            
            logger.info(f"🎬 Получение транскрипции для видео: {video_id}")
            
            # Получаем список доступных языков
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                available_languages = [t.language_code for t in transcript_list]
                logger.info(f"📋 Доступные языки: {available_languages}")
                
                # Пытаемся найти транскрипцию на предпочтительном языке
                transcript = None
                used_language = None
                
                # Сначала ищем точное совпадение
                if language in available_languages:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
                    used_language = language
                    logger.info(f"✅ Найдена транскрипция на языке: {language}")
                
                # Если нет, пытаемся найти русскую
                elif 'ru' in available_languages and language != 'ru':
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'])
                    used_language = 'ru'
                    logger.info(f"✅ Найдена транскрипция на русском языке")
                
                # Если нет русской, берем английскую
                elif 'en' in available_languages:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                    used_language = 'en'
                    logger.info(f"✅ Найдена транскрипция на английском языке")
                
                # Если нет ни русской, ни английской, берем первую доступную
                elif available_languages:
                    first_lang = available_languages[0]
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_lang])
                    used_language = first_lang
                    logger.info(f"✅ Найдена транскрипция на языке: {first_lang}")
                
                if not transcript:
                    return {
                        'success': False,
                        'error': 'Транскрипция не найдена для данного видео',
                        'available_languages': available_languages,
                        'video_id': video_id
                    }
                
                # Форматируем транскрипцию
                formatter = TextFormatter()
                text_formatted = formatter.format_transcript(transcript)
                
                # Получаем информацию о видео
                video_info = self._get_video_info(video_id)
                
                # Создаем заголовок для файла
                header = f"Транскрипция YouTube видео\n"
                header += f"URL: https://www.youtube.com/watch?v={video_id}\n"
                if video_info.get('title'):
                    header += f"Название: {video_info['title']}\n"
                if video_info.get('channel'):
                    header += f"Канал: {video_info['channel']}\n"
                header += f"Язык транскрипции: {used_language}\n"
                header += f"Дата получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                header += f"{'='*50}\n\n"
                
                # Объединяем заголовок и транскрипцию
                full_text = header + text_formatted
                
                return {
                    'success': True,
                    'text': full_text,
                    'language': used_language,
                    'video_id': video_id,
                    'video_info': video_info,
                    'available_languages': available_languages
                }
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения транскрипции: {e}")
                return {
                    'success': False,
                    'error': f'Ошибка API: {str(e)}',
                    'video_id': video_id
                }
                
        except ImportError:
            logger.error("❌ youtube_transcript_api не установлен")
            return {
                'success': False,
                'error': 'youtube_transcript_api не установлен'
            }
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {str(e)}'
            }
    
    def _get_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        Получает базовую информацию о видео
        
        Args:
            video_id: ID видео
            
        Returns:
            Dict: Информация о видео
        """
        try:
            # Пытаемся получить информацию через YouTube API если доступен
            from ..config import YOUTUBE_API_KEY
            
            if YOUTUBE_API_KEY:
                import aiohttp
                import asyncio
                
                async def fetch_info():
                    url = f"https://www.googleapis.com/youtube/v3/videos"
                    params = {
                        'part': 'snippet',
                        'id': video_id,
                        'key': YOUTUBE_API_KEY
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get('items'):
                                    snippet = data['items'][0]['snippet']
                                    return {
                                        'title': snippet.get('title'),
                                        'channel': snippet.get('channelTitle'),
                                        'description': snippet.get('description', '')[:200] + '...'
                                    }
                    return {}
                
                # Запускаем в event loop
                try:
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(fetch_info())
                except:
                    # Если не удалось получить через API, возвращаем пустую информацию
                    return {}
            else:
                return {}
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить информацию о видео: {e}")
            return {}
    
    def save_transcript_to_file(self, transcript_text: str, video_id: str, video_title: str = None) -> str:
        """
        Сохраняет транскрипцию в временный файл
        
        Args:
            transcript_text: Текст транскрипции
            video_id: ID видео
            video_title: Название видео (опционально)
            
        Returns:
            str: Путь к сохраненному файлу
        """
        try:
            # Создаем безопасное имя файла
            safe_title = ""
            if video_title:
                # Убираем небезопасные символы
                safe_title = re.sub(r'[<>:"/\\|?*]', '', video_title)
                safe_title = safe_title[:50]  # Ограничиваем длину
                safe_title = f"_{safe_title}" if safe_title else ""
            
            filename = f"youtube_transcript_{video_id}{safe_title}.txt"
            
            # Создаем временный файл
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)
            
            # Сохраняем файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            
            logger.info(f"💾 Транскрипция сохранена: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения файла: {e}")
            raise
    
    def format_transcript_message(self, result: Dict[str, Any]) -> str:
        """
        Форматирует сообщение с результатом транскрипции
        
        Args:
            result: Результат получения транскрипции
            
        Returns:
            str: Отформатированное сообщение
        """
        if result['success']:
            video_info = result.get('video_info', {})
            title = video_info.get('title', 'Неизвестно')
            channel = video_info.get('channel', 'Неизвестно')
            language = result.get('language', 'Неизвестно')
            
            message = f"🎬 **Транскрипция получена**\n\n"
            message += f"📝 **Название:** {title}\n"
            message += f"👤 **Канал:** {channel}\n"
            message += f"🌐 **Язык:** {language}\n"
            message += f"🆔 **ID видео:** {result['video_id']}\n\n"
            message += f"📄 Файл с полной транскрипцией прикреплен выше"
            
            return message
        else:
            error_message = f"❌ **Ошибка получения транскрипции**\n\n"
            error_message += f"🔍 **Проблема:** {result['error']}\n"
            
            if result.get('available_languages'):
                error_message += f"📋 **Доступные языки:** {', '.join(result['available_languages'])}\n"
            
            error_message += f"\n💡 **Возможные причины:**\n"
            error_message += f"• Видео не имеет субтитров\n"
            error_message += f"• Субтитры отключены автором\n"
            error_message += f"• Видео приватное или удалено\n"
            error_message += f"• Неверная ссылка на видео"
            
            return error_message


# Создаем глобальный экземпляр сервиса
youtube_transcript_service = YouTubeTranscriptService()