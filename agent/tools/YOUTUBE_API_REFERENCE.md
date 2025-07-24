# YouTube Data API v3 - Полный обзор возможностей с API ключом

## 1. Данные о видео (все доступные поля)

### Часть `snippet` (основная информация):
- `publishedAt` - дата публикации
- `channelId` - ID канала
- `title` - название (макс. 100 символов)
- `description` - описание (макс. 5000 байт)
- `thumbnails` - превью в разных разрешениях (default, medium, high, standard, maxres)
- `channelTitle` - название канала
- `tags` - теги видео
- `categoryId` - категория видео
- `liveBroadcastContent` - статус трансляции
- `defaultLanguage` - основной язык
- `localized` - локализованные название и описание
- `defaultAudioLanguage` - язык аудио

### Часть `contentDetails` (детали контента):
- `duration` - длительность в формате ISO 8601
- `dimension` - 2D или 3D
- `definition` - HD или SD
- `caption` - наличие субтитров
- `licensedContent` - лицензированный контент
- `regionRestriction` - региональные ограничения
- `contentRating` - возрастные рейтинги
- `projection` - 360° или обычное видео
- `hasCustomThumbnail` - кастомная превьюшка

### Часть `statistics` (статистика):
- `viewCount` - количество просмотров
- `likeCount` - количество лайков
- `dislikeCount` - количество дизлайков (приватное)
- `commentCount` - количество комментариев

### Часть `status` (статус):
- `uploadStatus` - статус загрузки
- `privacyStatus` - приватность (public, private, unlisted)
- `license` - лицензия
- `embeddable` - можно ли встраивать
- `madeForKids` - контент для детей
- `containsSyntheticMedia` - содержит ли синтетические медиа

## 2. Операции доступные без OAuth авторизации

### Методы чтения (требуют только API ключ):

#### Videos (видео):
- `videos.list` - получение информации о видео (1 квота)
- Параметры: id, part, chart, maxResults, regionCode

#### Channels (каналы):
- `channels.list` - информация о каналах (1 квота)
- Получение метаданных, статистики, брендинга

#### Playlists (плейлисты):
- `playlists.list` - список плейлистов (1 квота)
- `playlistItems.list` - видео в плейлисте (1 квота)

#### Search (поиск):
- `search.list` - поиск контента (100 квота!)
- Поиск видео, каналов, плейлистов

#### Comments (комментарии):
- `comments.list` - чтение комментариев (1 квота)
- `commentThreads.list` - ветки комментариев (1 квота)

#### Другие:
- `videoCategories.list` - категории видео (1 квота)
- `guideCategories.list` - категории гида (1 квота)
- `activities.list` - активности канала (1 квота)

### Недоступно с API ключом:
- ❌ Загрузка видео
- ❌ Создание/изменение плейлистов
- ❌ Публикация комментариев
- ❌ Подписка на каналы
- ❌ Лайки/дизлайки
- ❌ Обновление информации канала
- ❌ Удаление контента

## 3. Лимиты и квоты API

### Базовые лимиты:
- **10,000 единиц в день** - стандартная квота
- Сброс в полночь по тихоокеанскому времени

### Стоимость операций:
- **Чтение списков**: 1 единица
  - videos.list, channels.list, playlists.list
- **Поиск**: 100 единиц
  - search.list
- **Запись**: 50 единиц
  - insert, update, delete (требуют OAuth)
- **Загрузка видео**: 1600 единиц
  - videos.insert (требует OAuth)

### Важные детали:
- Каждый запрос стоит минимум 1 единицу
- Даже неудачные запросы тратят квоту
- Пагинация стоит квоту за каждую страницу

## 4. Дополнительные endpoints

### Основные ресурсы API:

1. **Activities** - действия на канале
2. **Captions** - субтитры (чтение доступно)
3. **ChannelBanners** - баннеры каналов
4. **ChannelSections** - секции канала
5. **GuideCategories** - категории YouTube гида
6. **i18nLanguages** - поддерживаемые языки
7. **i18nRegions** - поддерживаемые регионы
8. **Members** - участники канала
9. **MembershipsLevels** - уровни членства
10. **Subscriptions** - подписки (чтение публичных)
11. **Thumbnails** - превью
12. **VideoAbuseReportReasons** - причины жалоб
13. **VideoCategories** - категории видео
14. **Watermarks** - водяные знаки

## 5. Примеры запросов videos.list

### Базовый запрос по ID видео:
```
GET https://www.googleapis.com/youtube/v3/videos
?part=snippet,contentDetails,statistics
&id=VIDEO_ID
&key=YOUR_API_KEY
```

### Получение популярных видео:
```
GET https://www.googleapis.com/youtube/v3/videos
?part=snippet,statistics
&chart=mostPopular
&regionCode=RU
&maxResults=10
&key=YOUR_API_KEY
```

### Множественные видео:
```
GET https://www.googleapis.com/youtube/v3/videos
?part=snippet,contentDetails,statistics,status
&id=VIDEO_ID1,VIDEO_ID2,VIDEO_ID3
&key=YOUR_API_KEY
```

### С локализацией:
```
GET https://www.googleapis.com/youtube/v3/videos
?part=snippet,localizations
&id=VIDEO_ID
&hl=ru
&key=YOUR_API_KEY
```

### Все доступные части:
```
GET https://www.googleapis.com/youtube/v3/videos
?part=snippet,contentDetails,statistics,status,player,topicDetails,recordingDetails,localizations
&id=VIDEO_ID
&key=YOUR_API_KEY
```

### Параметры videos.list:
- `part` (обязательный) - какие части данных вернуть
- `chart` - mostPopular для популярных видео
- `id` - ID видео (до 50 через запятую)
- `myRating` - like/dislike (требует OAuth)
- `hl` - язык для локализованных данных
- `maxHeight`/`maxWidth` - для player.embedHtml
- `maxResults` - количество результатов (1-50, по умолчанию 5)
- `onBehalfOfContentOwner` - для контент-партнёров
- `pageToken` - для пагинации
- `regionCode` - код страны для chart
- `videoCategoryId` - фильтр по категории для chart

## Рекомендации по использованию:

1. **Оптимизируйте запросы**: запрашивайте только нужные части данных
2. **Кешируйте результаты**: экономьте квоту
3. **Обрабатывайте ошибки**: особенно quotaExceeded
4. **Используйте пагинацию**: для больших результатов
5. **Мониторьте квоту**: в Google Cloud Console

Этот обзор покрывает все основные возможности YouTube Data API v3 с использованием только API ключа.