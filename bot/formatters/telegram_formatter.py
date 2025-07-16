"""
Форматтер для Telegram сообщений

Адаптирует данные из SocialMedia сервиса для отображения в Telegram
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)


class TelegramFormatter:
    """
    Форматтер для создания красивых сообщений в Telegram
    """
    
    @staticmethod
    def format_youtube_video(video: Dict) -> str:
        """
        Форматирует YouTube видео для Telegram
        
        Args:
            video: Данные видео
            
        Returns:
            str: Отформатированное сообщение
        """
        title = video.get('title', 'Без названия')
        channel = video.get('channel', 'Неизвестный канал')
        views = TelegramFormatter._format_number(video.get('views', 0))
        likes = TelegramFormatter._format_number(video.get('likes', 0))
        comments = TelegramFormatter._format_number(video.get('comments', 0))
        duration = TelegramFormatter._format_duration(video.get('duration', 'PT0S'))
        published = TelegramFormatter._format_date(video.get('published_at', ''))
        url = video.get('url', '')
        
        return f"""🎥 **{title}**

👤 **Канал:** {channel}
⏱️ **Длительность:** {duration}
📅 **Опубликовано:** {published}

📊 **Статистика:**
👁️ {views} просмотров
👍 {likes} лайков
💬 {comments} комментариев

🔗 [Смотреть видео]({url})"""
    
    @staticmethod
    def format_youtube_channel(channel: Dict) -> str:
        """
        Форматирует YouTube канал для Telegram
        
        Args:
            channel: Данные канала
            
        Returns:
            str: Отформатированное сообщение
        """
        title = channel.get('title', 'Без названия')
        description = channel.get('description', 'Нет описания')[:200] + '...' if len(channel.get('description', '')) > 200 else channel.get('description', '')
        subscribers = TelegramFormatter._format_number(channel.get('subscribers', 0))
        video_count = TelegramFormatter._format_number(channel.get('video_count', 0))
        view_count = TelegramFormatter._format_number(channel.get('view_count', 0))
        created = TelegramFormatter._format_date(channel.get('created_at', ''))
        url = channel.get('url', '')
        
        return f"""📺 **{title}**

📝 **Описание:** {description}
📅 **Создан:** {created}

📊 **Статистика:**
👥 {subscribers} подписчиков
🎬 {video_count} видео
👁️ {view_count} общих просмотров

🔗 [Перейти на канал]({url})"""
    
    @staticmethod
    def format_search_results(results: List[Dict], platform: str, query: str) -> str:
        """
        Форматирует результаты поиска для Telegram
        
        Args:
            results: Список результатов
            platform: Платформа (youtube, instagram, tiktok)
            query: Поисковый запрос
            
        Returns:
            str: Отформатированное сообщение
        """
        if not results:
            return f"🔍 **Поиск на {platform.upper()}:** `{query}`\n\n❌ Результаты не найдены"
        
        platform_emoji = {
            'youtube': '🎥',
            'instagram': '📸',
            'tiktok': '🎵'
        }
        
        emoji = platform_emoji.get(platform, '🔍')
        
        header = f"{emoji} **Поиск на {platform.upper()}:** `{query}`\n\n"
        header += f"📊 **Найдено:** {len(results)} результатов\n\n"
        
        items = []
        for i, result in enumerate(results[:5], 1):  # Показываем только первые 5
            if platform == 'youtube':
                item = TelegramFormatter._format_youtube_short(result, i)
            elif platform == 'instagram':
                item = TelegramFormatter._format_instagram_short(result, i)
            elif platform == 'tiktok':
                item = TelegramFormatter._format_tiktok_short(result, i)
            else:
                item = f"{i}. {result.get('title', 'Без названия')}"
            
            items.append(item)
        
        footer = ""
        if len(results) > 5:
            footer = f"\n\n💡 Показаны первые 5 из {len(results)} результатов"
        
        return header + "\n\n".join(items) + footer
    
    @staticmethod
    def _format_youtube_short(video: Dict, index: int) -> str:
        """
        Краткое форматирование YouTube видео
        """
        title = video.get('title', 'Без названия')[:50] + '...' if len(video.get('title', '')) > 50 else video.get('title', '')
        channel = video.get('channel', 'Неизвестный канал')
        views = TelegramFormatter._format_number(video.get('views', 0))
        duration = TelegramFormatter._format_duration(video.get('duration', 'PT0S'))
        url = video.get('url', '')
        
        return f"**{index}.** [{title}]({url})\n👤 {channel} • 👁️ {views} • ⏱️ {duration}"
    
    @staticmethod
    def _format_instagram_short(post: Dict, index: int) -> str:
        """
        Краткое форматирование Instagram поста
        """
        title = post.get('title', 'Без названия')[:50] + '...' if len(post.get('title', '')) > 50 else post.get('title', '')
        username = post.get('username', 'Неизвестный пользователь')
        likes = TelegramFormatter._format_number(post.get('likes', 0))
        url = post.get('url', '')
        
        return f"**{index}.** [{title}]({url})\n👤 @{username} • ❤️ {likes}"
    
    @staticmethod
    def _format_tiktok_short(video: Dict, index: int) -> str:
        """
        Краткое форматирование TikTok видео
        """
        title = video.get('title', 'Без названия')[:50] + '...' if len(video.get('title', '')) > 50 else video.get('title', '')
        username = video.get('username', 'Неизвестный пользователь')
        likes = TelegramFormatter._format_number(video.get('likes', 0))
        url = video.get('url', '')
        
        return f"**{index}.** [{title}]({url})\n👤 @{username} • ❤️ {likes}"
    
    @staticmethod
    def _format_number(num: int) -> str:
        """
        Форматирует большие числа (1000 -> 1K, 1000000 -> 1M)
        """
        if num >= 1000000:
            return f"{num / 1000000:.1f}M"
        elif num >= 1000:
            return f"{num / 1000:.1f}K"
        else:
            return str(num)
    
    @staticmethod
    def _format_duration(duration: str) -> str:
        """
        Форматирует YouTube duration (PT1H2M3S -> 1:02:03)
        """
        if not duration or duration == 'PT0S':
            return '0:00'
        
        # Парсим ISO 8601 duration
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)
        
        if not match:
            return duration
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    @staticmethod
    def _format_date(date_str: str) -> str:
        """
        Форматирует дату в читаемый вид
        """
        if not date_str:
            return 'Неизвестно'
        
        try:
            # Парсим ISO 8601 дату
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Конвертируем в локальное время
            now = datetime.now(timezone.utc)
            diff = now - dt
            
            if diff.days == 0:
                return 'Сегодня'
            elif diff.days == 1:
                return 'Вчера'
            elif diff.days < 7:
                return f'{diff.days} дней назад'
            elif diff.days < 30:
                weeks = diff.days // 7
                return f'{weeks} недель назад'
            elif diff.days < 365:
                months = diff.days // 30
                return f'{months} месяцев назад'
            else:
                years = diff.days // 365
                return f'{years} лет назад'
                
        except Exception as e:
            logger.warning(f"Ошибка форматирования даты '{date_str}': {e}")
            return date_str
    
    @staticmethod
    def format_admin_command_help() -> str:
        """
        Форматирует справку по админским командам
        """
        return """🔑 **Админские команды:**

**🎥 YouTube:**
• `/youtube <запрос>` - поиск видео
• `/channel <канал>` - анализ канала
• `/youtube_channel <канал>` - видео с канала

**📸 Instagram:**
• `/instagram <запрос>` - поиск постов
• `/insta_user <username>` - посты пользователя

**🎵 TikTok:**
• `/tiktok <запрос>` - поиск видео
• `/tiktok_user <username>` - видео пользователя

**⚙️ Управление:**
• `/admin_status` - статус системы
• `/social_config` - конфигурация API
• `/help_admin` - эта справка

💡 Все команды доступны только администратору"""
    
    @staticmethod
    def format_error_message(error: str, platform: str = None) -> str:
        """
        Форматирует сообщение об ошибке
        """
        platform_text = f" на {platform.upper()}" if platform else ""
        
        return f"""❌ **Ошибка{platform_text}**

🔍 **Описание:** {error}

💡 **Возможные причины:**
• Неверный API ключ
• Превышена квота запросов
• Проблемы с интернетом
• Неверный формат запроса

🔧 Обратитесь к администратору если ошибка повторяется"""
    
    @staticmethod
    def format_admin_status(status: Dict) -> str:
        """
        Форматирует статус админской панели
        """
        platforms = status.get('available_platforms', [])
        platforms_text = ', '.join(platforms) if platforms else 'Нет доступных'
        
        youtube_status = '✅' if status.get('youtube_enabled') else '❌'
        instagram_status = '✅' if status.get('instagram_enabled') else '❌'
        tiktok_status = '✅' if status.get('tiktok_enabled') else '❌'
        
        return f"""🔑 **Статус админской панели**

📊 **Доступные платформы:** {platforms_text}

**🎥 YouTube:** {youtube_status}
**📸 Instagram:** {instagram_status}
**🎵 TikTok:** {tiktok_status}

⚙️ **Стратегий загружено:** {status.get('strategies_count', 0)}

💡 Используйте `/help_admin` для списка команд"""


# Создаем глобальный экземпляр форматтера
telegram_formatter = TelegramFormatter()