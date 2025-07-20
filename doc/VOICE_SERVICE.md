# Voice Service для Artyom Integrator

Модуль для обработки голосовых сообщений в Telegram боте с использованием OpenAI Whisper.

## Возможности

- 🎤 Обработка голосовых сообщений из Telegram
- 📥 Автоматическое скачивание аудио файлов
- 🎯 Транскрипция речи в текст через OpenAI Whisper
- 🧠 Интеграция с AI агентом для ответов
- 🔒 Безопасная обработка и очистка временных файлов

## Архитектура

```
voice/
├── __init__.py           # Экспорт VoiceService
├── config.py            # Настройки сервиса
├── telegram_audio.py    # Скачивание аудио из Telegram
├── whisper_client.py    # Клиент OpenAI Whisper
├── voice_service.py     # Основной сервис
└── README.md           # Документация
```

## Компоненты

### VoiceService
Главный класс для обработки голосовых сообщений:
- `process_voice_message()` - основная точка входа
- `test_service()` - тестирование готовности
- `get_service_info()` - информация о сервисе

### TelegramAudioDownloader
Скачивание аудио файлов:
- `download_voice_file()` - скачивание по file_id
- `get_file_info()` - получение метаданных
- `cleanup_temp_files()` - очистка временных файлов

### WhisperTranscriber
Транскрипция аудио:
- `transcribe()` - преобразование речи в текст
- `validate_audio_file()` - проверка формата файла
- `test_connection()` - проверка API подключения

## Настройки

### Переменные окружения
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `OPENAI_API_KEY` - ключ OpenAI для Whisper

### Лимиты
- Максимальный размер файла: 25MB
- Максимальная длительность: 10 минут
- Поддерживаемые форматы: mp3, mp4, mpeg, mpga, m4a, wav, webm

## Использование

```python
from voice import VoiceService

# Инициализация
voice_service = VoiceService(telegram_token, openai_key)

# Обработка голосового сообщения
result = await voice_service.process_voice_message(
    voice_data, user_id, message_id
)

if result['success']:
    transcribed_text = result['text']
    # Обработка транскрипции
```

## Интеграция с webhook.py

Voice Service автоматически интегрирован в основной webhook сервер:
- Обнаружение голосовых сообщений
- Автоматическая транскрипция
- Передача текста в AI агента
- Graceful fallback при ошибках

## Тестирование

Запустите тесты:
```bash
python test_voice_service.py
```

## Логирование

Все операции логируются с префиксами:
- 🎤 Обработка голосовых сообщений
- 📥 Скачивание файлов
- 🎯 Транскрипция
- ✅ Успешные операции
- ❌ Ошибки

## Безопасность

- Валидация размера и формата файлов
- Автоматическая очистка временных файлов
- Таймауты для всех сетевых операций
- Обработка ошибок API

## Troubleshooting

1. **Voice Service не инициализируется**
   - Проверьте OPENAI_API_KEY
   - Убедитесь что все зависимости установлены

2. **Ошибки скачивания**
   - Проверьте TELEGRAM_BOT_TOKEN
   - Убедитесь в доступности интернета

3. **Ошибки транскрипции**
   - Проверьте лимиты OpenAI API
   - Убедитесь в поддержке формата файла