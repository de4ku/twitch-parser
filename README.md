# Twitch Parser

Парсер русскоязычных Twitch стримеров с малым онлайном (до 150 зрителей). Собирает контакты из описания канала и выгружает в Google Sheets.

## Возможности

- ✅ Парсинг живых русскоязычных стримов
- ✅ Фильтрация по количеству зрителей (до 150)
- ✅ Извлечение контактов (Discord, VK, Telegram, Email)
- ✅ Автоматическая выгрузка в Google Sheets
- ✅ Информация о категории игры, названии стрима, времени начала

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/yourusername/twitch-parser.git
cd twitch-parser
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Настроить Twitch API

1. Перейти на https://dev.twitch.tv/console/apps
2. Нажать "Register Your Application"
3. Заполнить форму:
   - Name: любое название (например, "Twitch Parser")
   - OAuth Redirect URLs: `http://localhost`
   - Category: Application Integration
4. Нажать "Create"
5. Скопировать **Client ID** и **Client Secret**
6. Вставить их в `config.py`:

```python
TWITCH_CLIENT_ID = "ваш_client_id"
TWITCH_CLIENT_SECRET = "ваш_client_secret"
```

### 4. Настроить Google Sheets API

#### 4.1. Создать Service Account

1. Перейти на https://console.cloud.google.com/
2. Создать новый проект (или выбрать существующий)
3. Включить **Google Sheets API**:
   - Перейти в "APIs & Services" → "Enable APIs and Services"
   - Найти "Google Sheets API" и включить
4. Включить **Google Drive API** (обязательно!):
   - Там же найти "Google Drive API" и включить
   - Без этого будет ошибка `APIError: [403]: Google Drive API has not been used`
5. Создать Service Account:
   - "APIs & Services" → "Credentials"
   - "Create Credentials" → "Service Account"
   - Заполнить имя и нажать "Create"
   - Пропустить опциональные шаги
6. Создать ключ:
   - Открыть созданный Service Account
   - Вкладка "Keys" → "Add Key" → "Create new key"
   - Выбрать JSON
   - Скачать файл и переименовать в `credentials.json`
   - Положить в папку с проектом
7. **Скопировать email Service Account** из `credentials.json` (поле `client_email`)
   - Выглядит как `xxx@xxx.iam.gserviceaccount.com`
   - Понадобится на следующем шаге

#### 4.2. Создать Google Sheets таблицу

1. Зайти на https://sheets.google.com
2. Создать новую таблицу: "Создать" → "Google Таблицы"
3. Назвать её **"Twitch Streamers Parser"** (или изменить название в `config.py`)
4. Открыть доступ для Service Account:
   - Нажать "Настройки доступа" (Share) в правом верхнем углу
   - Вставить email Service Account из `credentials.json`
   - Выбрать роль **"Редактор"**
   - Нажать "Готово"

⚠️ **Важно:** Без этого шага будет ошибка `The user's Drive storage quota has been exceeded`, потому что Service Account попытается создать файл на своём Drive (где 0 места).

### 5. Запустить парсер

```bash
python parser.py
```

## Как это работает

1. Парсер подключается к Twitch API и получает список живых русскоязычных стримов
2. Фильтрует стримы по количеству зрителей (до 150)
3. Получает информацию о каждом стримере (описание канала)
4. Извлекает контакты из описания (Discord, VK, Telegram, Email)
5. Выгружает данные в Google Sheets

## Структура данных в Google Sheets

| Username | Display Name | Viewers | Game | Title | Started At | Channel URL | Discord | VK | Telegram | Email | Description |
|----------|--------------|---------|------|-------|------------|-------------|---------|----|-----------| ------|-------------|
| streamer1 | Streamer One | 45 | Dota 2 | Играем в доту | 2024-01-01T12:00:00Z | https://twitch.tv/streamer1 | discord.gg/abc | vk.com/streamer1 | t.me/streamer1 | email@example.com | Описание... |

## Настройка

В файле `config.py` можно изменить:

- `SPREADSHEET_NAME` — название таблицы в Google Sheets
- В `parser.py` в функции `main()` можно изменить `max_viewers` (по умолчанию 150)

## Частота запуска

Рекомендуется запускать парсер не чаще 1 раза в час, чтобы не превысить лимиты Twitch API.

Для автоматического запуска можно использовать cron (Linux/Mac) или Task Scheduler (Windows).

### Пример cron (каждый час):

```bash
0 * * * * cd /path/to/twitch-parser && python parser.py
```

## Лимиты API

- **Twitch API**: 800 запросов в минуту (достаточно для парсинга)
- **Google Sheets API**: 100 запросов в 100 секунд на пользователя (достаточно)

## Troubleshooting

### Ошибка "Invalid OAuth token"
- Проверьте правильность Client ID и Client Secret в `config.py`

### Ошибка `APIError: [403]: Google Drive API has not been used`
- Включите Google Drive API в консоли Google Cloud
- Перейдите по ссылке из ошибки и нажмите "Enable"
- Подождите 1-2 минуты и запустите парсер снова

### Ошибка `The user's Drive storage quota has been exceeded`
- Service Account пытается создать файл на своём Drive (где 0 места)
- **Решение:** Создайте таблицу вручную на своём Google Drive и дайте доступ Service Account (см. раздел 4.2)

### Ошибка "Spreadsheet not found"
- Убедитесь, что таблица называется точно так же, как в `config.py` (по умолчанию "Twitch Streamers Parser")
- Убедитесь, что Service Account имеет доступ к таблице (email из `credentials.json` добавлен в "Настройки доступа")

### Ошибка "credentials.json not found"
- Убедитесь, что файл `credentials.json` находится в папке с проектом

## Лицензия

MIT

## Автор

Создано для парсинга потенциальных клиентов для сервиса накрутки чата Twitch/Kick.
