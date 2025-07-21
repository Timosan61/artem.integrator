"""
Обработчики webhook запросов
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.interfaces import Message, User, MessageType, UserRole
from ..core.agent import AgentFactory
from ..core.config import config
# Опциональные импорты сервисов
try:
    from ..services.voice_service import voice_service
except ImportError:
    voice_service = None

try:
    from ..services.social_media_service import social_media_service
except ImportError:
    social_media_service = None

try:
    from ..services.youtube_transcript_service import youtube_transcript_service
except ImportError:
    youtube_transcript_service = None

try:
    from ..services.claude_code_service import claude_code_service
except ImportError:
    claude_code_service = None

from ..auth import is_admin, get_user_mode

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Основной обработчик webhook запросов"""
    
    def __init__(self):
        """Инициализация обработчика"""
        self.agent = AgentFactory.get_agent()
        self.update_counter = 0
        self.last_updates = []
    
    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает входящий update от Telegram
        
        Args:
            update: Update от Telegram API
            
        Returns:
            Dict[str, Any]: Результат обработки
        """
        logger.info(f"📥 Received update: {update}")
        
        self.update_counter += 1
        update_id = update.get('update_id', self.update_counter)
        
        logger.info(f"📨 Processing update #{update_id}, total: {self.update_counter}")
        
        # Всегда сохраняем для отладки (не только в debug режиме)
        self._save_update_for_debug(update)
        logger.info(f"💾 Saved to debug. Total updates in memory: {len(self.last_updates)}")
        
        try:
            # Определяем тип update
            if 'message' in update:
                return await self._handle_message(update['message'])
            elif 'callback_query' in update:
                return await self._handle_callback_query(update['callback_query'])
            elif 'business_message' in update:
                return await self._handle_business_message(update['business_message'])
            elif 'business_connection' in update:
                return await self._handle_business_connection(update['business_connection'])
            else:
                logger.warning(f"❓ Неизвестный тип update: {list(update.keys())}")
                return {"ok": True, "description": "Unknown update type"}
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки update {update_id}: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    async def _handle_message(self, telegram_message: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает обычное сообщение"""
        try:
            logger.info(f"📩 Processing message: {telegram_message}")
            
            # Извлекаем данные
            user_data = telegram_message.get('from', {})
            chat_id = telegram_message.get('chat', {}).get('id')
            text = telegram_message.get('text')
            voice = telegram_message.get('voice')
            
            logger.info(f"👤 User: {user_data.get('username', 'Unknown')} ({user_data.get('id', 'Unknown')})")
            logger.info(f"💬 Text: {text}")
            logger.info(f"🎤 Voice: {bool(voice)}")
            
            # Создаем объект пользователя
            user = User(
                id=user_data.get('id'),
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                role=UserRole.ADMIN if is_admin(user_data.get('id')) else UserRole.USER
            )
            
            # Определяем тип сообщения
            if voice:
                message_type = MessageType.VOICE
                # Обрабатываем голос через Voice Service
                if voice_service and config.voice.enabled:
                    text = await self._process_voice(voice, user.id)
                    if not text:
                        return {"ok": True, "description": "Voice processing failed"}
                else:
                    return {"ok": True, "description": "Voice service disabled"}
            elif text:
                message_type = MessageType.TEXT
            else:
                message_type = MessageType.OTHER
            
            # Создаем объект сообщения
            message = Message(
                id=telegram_message.get('message_id'),
                user=user,
                chat_id=chat_id,
                text=text,
                type=message_type,
                timestamp=datetime.fromtimestamp(telegram_message.get('date', 0)),
                metadata={"telegram_message": telegram_message}
            )
            
            # Проверяем специальные команды
            if text and text.startswith('/'):
                special_response = await self._handle_special_command(message)
                if special_response:
                    return special_response
            
            # Проверяем Social Media интент
            if text and social_media_service:
                social_response = await self._handle_social_media(message)
                if social_response:
                    return social_response
            
            # Обрабатываем через AI агента
            response = await self.agent.process_message(message)
            
            # Отправляем ответ
            try:
                from ..telegram_bot import bot
                logger.info(f"📤 Sending response to {chat_id}: {response.text[:100]}...")
                result = bot.send_message(chat_id, response.text)
                logger.info(f"✅ Response sent successfully. Message ID: {result.message_id if hasattr(result, 'message_id') else 'Unknown'}")
                return {"ok": True, "response_sent": True, "message_id": result.message_id if hasattr(result, 'message_id') else None}
            except ImportError as e:
                logger.error(f"❌ Failed to import telegram bot: {e}", exc_info=True)
                # Fallback: используем requests для отправки
                import requests
                url = f"https://api.telegram.org/bot{config.telegram.token}/sendMessage"
                data = {"chat_id": chat_id, "text": response.text}
                try:
                    resp = requests.post(url, json=data)
                    if resp.ok:
                        logger.info(f"✅ Response sent via API")
                        return {"ok": True, "response_sent": True}
                    else:
                        logger.error(f"❌ API error: {resp.text}")
                        return {"ok": True, "response_sent": False, "error": resp.text}
                except Exception as api_error:
                    logger.error(f"❌ Failed to send via API: {api_error}")
                    return {"ok": True, "response_sent": False, "error": str(api_error)}
            except Exception as e:
                logger.error(f"❌ Failed to send response: {e}", exc_info=True)
                return {"ok": True, "response_sent": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    async def _handle_callback_query(self, callback_query: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает callback query"""
        # TODO: Реализовать обработку callback queries
        return {"ok": True, "description": "Callback query handled"}
    
    async def _handle_business_message(self, business_message: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает Business API сообщение"""
        # Обрабатываем как обычное сообщение, но с business_connection_id
        result = await self._handle_message(business_message)
        
        # Добавляем business_connection_id в метаданные
        if result.get('ok'):
            result['business_connection_id'] = business_message.get('business_connection_id')
        
        return result
    
    async def _handle_business_connection(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает Business API connection"""
        logger.info(f"📱 Business connection update: {connection}")
        
        connection_id = connection.get('id')
        is_enabled = connection.get('is_enabled', False)
        user_data = connection.get('user', {})
        
        if is_enabled:
            logger.info(f"✅ Business connection установлено: {connection_id}")
        else:
            logger.info(f"❌ Business connection отключено: {connection_id}")
        
        return {"ok": True, "description": f"Business connection {'enabled' if is_enabled else 'disabled'}"}
    
    async def _process_voice(self, voice_data: Dict[str, Any], user_id: int) -> Optional[str]:
        """Обрабатывает голосовое сообщение"""
        try:
            file_id = voice_data.get('file_id')
            if not file_id:
                return None
            
            # Транскрибируем через Voice Service
            result = await voice_service.process_voice_message(file_id, user_id)
            
            if result and result.get('success'):
                return result.get('text')
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки голоса: {e}")
            return None
    
    async def _handle_special_command(self, message: Message) -> Optional[Dict[str, Any]]:
        """Обрабатывает специальные команды"""
        command = message.text.split()[0].lower()
        
        # Команды для всех
        if command == '/start':
            from ..telegram_bot import bot
            welcome_text = self._get_welcome_message(message.user)
            try:
                # Временно отключаем HTML форматирование для отладки
                bot.send_message(message.chat_id, "👋 Добро пожаловать! Бот работает корректно.")
                logger.info(f"✅ Welcome message sent to {message.chat_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send welcome message: {e}", exc_info=True)
            return {"ok": True, "command": "start"}
        
        elif command == '/help':
            from ..telegram_bot import bot
            help_text = self._get_help_message(message.user)
            try:
                bot.send_message(message.chat_id, help_text, parse_mode='HTML')
                logger.info(f"✅ Help message sent to {message.chat_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send help message: {e}", exc_info=True)
            return {"ok": True, "command": "help"}
        
        # Админские команды
        if message.user.role == UserRole.ADMIN:
            if command == '/clear':
                success = await self.agent.clear_user_memory(message.user.id)
                from ..telegram_bot import bot
                try:
                    if success:
                        bot.send_message(message.chat_id, "✅ Память очищена")
                    else:
                        bot.send_message(message.chat_id, "❌ Ошибка очистки памяти")
                    logger.info(f"✅ Clear memory response sent to {message.chat_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send clear memory response: {e}", exc_info=True)
                return {"ok": True, "command": "clear"}
            
            # MCP команды (только для админов)
            elif claude_code_service and (
                command.startswith('/mcp') or 
                command == '/db' or 
                command == '/docs' or
                message.text.startswith('/mcp ') or
                message.text.startswith('/db ') or
                message.text.startswith('/docs ')
            ):
                logger.info(f"🔌 Processing MCP command: {message.text}")
                from ..telegram_bot import bot
                
                try:
                    # Отправляем сообщение о начале обработки
                    bot.send_message(message.chat_id, "⏳ Выполняю MCP команду...")
                    
                    # Выполняем команду через Claude Code
                    result = await claude_code_service.execute_mcp_command(
                        message.text, 
                        str(message.user.id)
                    )
                    
                    # Форматируем ответ
                    if result.get("success"):
                        response_text = result.get("response", "Команда выполнена")
                        # Ограничиваем длину сообщения
                        if len(response_text) > 4000:
                            response_text = response_text[:3997] + "..."
                    else:
                        response_text = f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}"
                    
                    # Отправляем результат
                    bot.send_message(message.chat_id, response_text, parse_mode='Markdown')
                    logger.info(f"✅ MCP response sent to {message.chat_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to execute MCP command: {e}", exc_info=True)
                    try:
                        bot.send_message(
                            message.chat_id, 
                            f"❌ Ошибка выполнения MCP команды: {str(e)}"
                        )
                    except:
                        pass
                
                return {"ok": True, "command": "mcp", "mcp_command": message.text}
        
        return None
    
    async def _handle_social_media(self, message: Message) -> Optional[Dict[str, Any]]:
        """Обрабатывает Social Media запросы"""
        # Проверяем интент через детектор
        from ..services.intent_detector import IntentDetector
        detector = IntentDetector()
        intent = await detector.detect(message)
        
        if intent['type'] in ['youtube_url', 'social_media'] and message.user.role == UserRole.ADMIN:
            # Обрабатываем через Social Media Service
            result = await social_media_service.process_message(
                message.text,
                message.user.id,
                message.user.full_name
            )
            
            if result and result.get('success'):
                from ..telegram_bot import bot
                try:
                    bot.send_message(message.chat_id, result.get('response'), parse_mode='HTML')
                    logger.info(f"✅ Social media response sent to {message.chat_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send social media response: {e}", exc_info=True)
                return {"ok": True, "social_media": True}
        
        return None
    
    def _get_welcome_message(self, user: User) -> str:
        """Генерирует приветственное сообщение"""
        if user.role == UserRole.ADMIN:
            from ..auth import format_admin_welcome_message
            return format_admin_welcome_message(user.id, user.username)
        else:
            from ..auth import format_user_welcome_message
            return format_user_welcome_message(user.full_name, user.id)
    
    def _get_help_message(self, user: User) -> str:
        """Генерирует help сообщение"""
        if user.role == UserRole.ADMIN:
            return """
<b>📋 Команды администратора:</b>

/help - Показать это сообщение
/clear - Очистить память бота
/youtube &lt;url&gt; - Анализ YouTube видео
/status - Статус всех сервисов
/test - Тестовый режим

<b>🎤 Голосовые сообщения:</b>
Отправьте голосовое сообщение для транскрипции

<b>💬 Обычный чат:</b>
Просто пишите сообщения для общения с AI
"""
        else:
            return """
<b>📋 Доступные команды:</b>

/help - Показать это сообщение
/start - Начать сначала

<b>💬 Как использовать:</b>
Просто отправьте мне сообщение, и я отвечу!

<b>🎤 Голосовые сообщения:</b>
Вы можете отправлять голосовые сообщения - я их расшифрую
"""
    
    def _save_update_for_debug(self, update: Dict[str, Any]):
        """Сохраняет update для отладки"""
        self.last_updates.append({
            "id": self.update_counter,
            "timestamp": datetime.now().isoformat(),
            "update": update
        })
        # Ограничиваем размер
        if len(self.last_updates) > 10:
            self.last_updates.pop(0)


# Создаем глобальный экземпляр обработчика
webhook_handler = WebhookHandler()