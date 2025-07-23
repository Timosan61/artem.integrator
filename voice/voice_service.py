"""
Voice Service - основной сервис для обработки голосовых сообщений
Объединяет скачивание аудио и транскрипцию в единый workflow
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from .telegram_audio import TelegramAudioDownloader
from .whisper_client import WhisperTranscriber
from .config import MAX_AUDIO_DURATION_SECONDS

logger = logging.getLogger(__name__)


class VoiceService:
    """Главный сервис для обработки голосовых сообщений"""
    
    def __init__(self, telegram_bot_token: str, openai_api_key: str):
        self.telegram_bot_token = telegram_bot_token
        self.openai_api_key = openai_api_key
        
        # Инициализируем клиенты
        self.whisper_client = None
        if openai_api_key:
            try:
                self.whisper_client = WhisperTranscriber(openai_api_key)
                logger.info("✅ Whisper клиент инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Whisper клиента: {e}")
                self.whisper_client = None
        else:
            logger.warning("⚠️ OpenAI API key не предоставлен, голосовые сообщения не будут обрабатываться")
    
    async def process_voice_message(
        self, 
        voice_data: Dict[str, Any], 
        user_id: str, 
        message_id: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Основная функция обработки голосового сообщения
        
        Args:
            voice_data: Данные голосового сообщения от Telegram
            user_id: ID пользователя
            message_id: ID сообщения
            language: Язык для транскрипции (опционально)
        
        Returns:
            Dict с результатом обработки
        """
        start_time = datetime.now()
        file_id = voice_data.get('file_id')
        
        logger.info(f"🎤 Обработка голосового сообщения от user_{user_id}, message_{message_id}")
        logger.debug(f"📋 Voice data: {voice_data}")
        
        # Проверяем что у нас есть все необходимое
        if not self.whisper_client:
            return {
                "success": False,
                "error": "Voice processing not available (OpenAI API key missing)",
                "text": None,
                "user_id": user_id,
                "message_id": message_id
            }
        
        if not file_id:
            return {
                "success": False,
                "error": "No file_id in voice data",
                "text": None,
                "user_id": user_id,
                "message_id": message_id
            }
        
        # Проверяем длительность аудио
        duration = voice_data.get('duration', 0)
        if duration > MAX_AUDIO_DURATION_SECONDS:
            return {
                "success": False,
                "error": f"Audio too long: {duration}s (max {MAX_AUDIO_DURATION_SECONDS}s)",
                "text": None,
                "user_id": user_id,
                "message_id": message_id
            }
        
        audio_file_path = None
        
        try:
            # Этап 1: Скачиваем аудио файл
            logger.info("📥 Этап 1: Скачивание аудио файла...")
            download_result = await self._download_audio(file_id, voice_data)
            
            if not download_result["success"]:
                return {
                    "success": False,
                    "error": f"Download failed: {download_result['error']}",
                    "text": None,
                    "user_id": user_id,
                    "message_id": message_id
                }
            
            audio_file_path = download_result["file_path"]
            
            # Этап 2: Транскрибируем аудио
            logger.info("🎯 Этап 2: Транскрипция аудио...")
            transcription_result = await self.whisper_client.transcribe(
                audio_file_path, 
                language=language
            )
            
            if not transcription_result["success"]:
                return {
                    "success": False,
                    "error": f"Transcription failed: {transcription_result['error']}",
                    "text": None,
                    "user_id": user_id,
                    "message_id": message_id,
                    "file_path": audio_file_path
                }
            
            # Успешная обработка
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "text": transcription_result["text"],
                "user_id": user_id,
                "message_id": message_id,
                "file_id": file_id,
                "duration": duration,
                "processing_time": processing_time,
                "char_count": transcription_result.get("char_count", 0),
                "language": transcription_result.get("language"),
                "file_path": audio_file_path
            }
            
            logger.info(f"✅ Голосовое сообщение обработано за {processing_time:.1f}с")
            logger.info(f"📝 Транскрипция: {result['text'][:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки голосового сообщения: {e}")
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "text": None,
                "user_id": user_id,
                "message_id": message_id,
                "file_path": audio_file_path
            }
        
        finally:
            # Очищаем временный файл
            if audio_file_path:
                self._cleanup_audio_file(audio_file_path)
    
    async def _download_audio(self, file_id: str, voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Скачивает аудио файл через Telegram API"""
        try:
            async with TelegramAudioDownloader(self.telegram_bot_token) as downloader:
                file_path = await downloader.download_voice_file(file_id, voice_data)
                
                if file_path:
                    return {
                        "success": True,
                        "file_path": file_path,
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "file_path": None,
                        "error": "Failed to download audio file"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания аудио: {e}")
            return {
                "success": False,
                "file_path": None,
                "error": str(e)
            }
    
    def _cleanup_audio_file(self, file_path: str):
        """Очищает временный аудио файл"""
        try:
            TelegramAudioDownloader.cleanup_file(file_path)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось очистить файл {file_path}: {e}")
    
    async def test_service(self) -> Dict[str, Any]:
        """Тестирует работоспособность сервиса"""
        test_results = {
            "telegram_token": bool(self.telegram_bot_token),
            "openai_key": bool(self.openai_api_key),
            "whisper_client": bool(self.whisper_client),
            "whisper_connection": False
        }
        
        # Тестируем подключение к Whisper API
        if self.whisper_client:
            try:
                test_results["whisper_connection"] = await self.whisper_client.test_connection()
            except Exception as e:
                logger.error(f"❌ Ошибка тестирования Whisper: {e}")
                test_results["whisper_connection"] = False
        
        # Общий статус
        test_results["service_ready"] = (
            test_results["telegram_token"] and 
            test_results["whisper_client"] and 
            test_results["whisper_connection"]
        )
        
        return test_results
    
    def get_service_info(self) -> Dict[str, Any]:
        """Возвращает информацию о сервисе"""
        return {
            "service_name": "Voice Processing Service",
            "version": "1.0.0",
            "components": {
                "telegram_downloader": bool(self.telegram_bot_token),
                "whisper_transcriber": bool(self.whisper_client)
            },
            "supported_formats": self.whisper_client.get_supported_formats() if self.whisper_client else [],
            "max_duration": MAX_AUDIO_DURATION_SECONDS,
            "status": "ready" if self.whisper_client else "not_configured"
        }
    
    @staticmethod
    def cleanup_old_files():
        """Очищает старые временные файлы"""
        try:
            TelegramAudioDownloader.cleanup_temp_files(older_than_hours=2)
        except Exception as e:
            logger.error(f"❌ Ошибка очистки временных файлов: {e}")

    async def process_voice_to_mcp(
        self, 
        voice_data: Dict[str, Any], 
        user_id: str, 
        message_id: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает голосовое сообщение и выполняет MCP команду через Claude Code SDK
        
        Args:
            voice_data: Данные голосового сообщения от Telegram
            user_id: ID пользователя
            message_id: ID сообщения
            language: Язык для транскрипции (опционально)
        
        Returns:
            Dict с результатом MCP команды
        """
        # Сначала обрабатываем голосовое сообщение и получаем транскрипцию
        voice_result = await self.process_voice_message(voice_data, user_id, message_id, language)
        
        if not voice_result["success"]:
            return {
                "success": False,
                "error": voice_result["error"],
                "voice_text": None,
                "mcp_response": None
            }
        
        voice_text = voice_result["text"]
        
        try:
            # Импортируем ClaudeCodeService
            from bot.services.claude_code_service import claude_code_service
            
            # Формируем команду для Claude Code SDK
            mcp_command = f"/voice {voice_text}"
            
            logger.info(f"🎤 Выполнение MCP команды из голоса: {voice_text}")
            
            # Выполняем команду через Claude Code SDK
            mcp_result = await claude_code_service.execute_mcp_command(
                command=mcp_command,
                user_id=user_id
            )
            
            if mcp_result["success"]:
                logger.info("✅ MCP команда успешно выполнена из голосового запроса")
                return {
                    "success": True,
                    "voice_text": voice_text,
                    "mcp_response": mcp_result["response"],
                    "processing_time": voice_result.get("processing_time", 0)
                }
            else:
                logger.error(f"❌ Ошибка MCP команды: {mcp_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Ошибка обработки запроса: {mcp_result.get('error', 'Неизвестная ошибка')}",
                    "voice_text": voice_text,
                    "mcp_response": None
                }
                
        except ImportError:
            logger.error("❌ ClaudeCodeService не доступен")
            return {
                "success": False,
                "error": "Сервис управления инфраструктурой временно недоступен",
                "voice_text": voice_text,
                "mcp_response": None
            }
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении MCP команды из голоса: {e}")
            return {
                "success": False,
                "error": f"Ошибка обработки запроса: {str(e)}",
                "voice_text": voice_text,
                "mcp_response": None
            }