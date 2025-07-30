

# Инструкция по настройке и модификации SocialBot

## Общая информация

SocialBot — это Telegram-бот, написанный на Python с использованием библиотеки `python-telegram-bot`. Бот предоставляет функционал социальной сети, включая публикацию постов, работу с друзьями, группами, маркетплейсом, экономикой, историями, трансляциями и системой достижений.

## Настройка токена бота

Для работы бота необходимо указать токен, полученный от `@BotFather` в Telegram.

### Где изменить токен:

1. Откройте файл с исходным кодом бота.
2. Найдите функцию `main()` в конце файла.
3. Замените строку с токеном:

```python
application = Application.builder().token("СЮДА ТОКЕН БОТА").build()
```

на:

```python
application = Application.builder().token("ВАШ_ТОКЕН").build()
```

где `ВАШ_ТОКЕН` — это токен, полученный от `@BotFather`.

**Пример:**

```python
application = Application.builder().token("1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ").build()
```

**Важно**: Никогда не публикуйте токен бота в открытом доступе, так как это может позволить третьим лицам получить контроль над вашим ботом.

## Модификация функционала

Бот имеет модульную структуру, что упрощает добавление или изменение функционала. Основные компоненты кода:

1. **База данных** (`sqlite3`):
   - Настройка базы данных находится в начале файла, где создаются таблицы (`cursor.executescript`).
   - Для изменения структуры базы данных (добавление новых таблиц, полей или индексов) модифицируйте SQL-запросы в блоке `cursor.executescript`.

2. **Вспомогательные функции**:
   - Функции для работы с пользователями, постами, друзьями, уведомлениями и т.д. расположены после настройки базы данных.
   - Например, для изменения логики добавления друга, найдите функцию `send_friend_request`.

3. **Обработчики команд**:
   - Команды Telegram (например, `/start`, `/msg`, `/sell`) обрабатываются в функциях, начинающихся с `async def` и регистрируются в `main()` в списке `command_handlers`.
   - Для добавления новой команды:
     - Создайте новую функцию с префиксом `async def`, например:

       ```python
       async def new_command(update: Update, context: CallbackContext):
           await update.message.reply_text("Новая команда выполнена!")
       ```

     - Добавьте её в список `command_handlers` в функции `main()`:

       ```python
       command_handlers = [
           # ... существующие обработчики ...
           CommandHandler("new_command", new_command),
       ]
       ```

4. **Обработчики сообщений**:
   - Функция `handle_message` обрабатывает текстовые сообщения и медиа (фото, видео, документы, стикеры).
   - Для изменения логики обработки сообщений (например, добавления новых типов контента):
     - Найдите блок обработки медиа (поиск по `if message.photo`, `if message.video` и т.д.).
     - Добавьте новую логику, например, для обработки аудио:

       ```python
       elif message.audio:
           context.user_data['pending_media'] = {'type': 'audio', 'id': message.audio.file_id}
           await message.reply_text('🎵 Аудио получено. Теперь введите описание поста:')
       ```

     - Обновите функцию `create_post` для поддержки нового типа медиа:

       ```python
       def create_post(user_id, content, group_id=None, media_type=None, media_id=None):
           # ... существующий код ...
           if media_type not in ['photo', 'video', 'document', 'sticker', 'audio']:
               raise ValueError("Неподдерживаемый тип медиа")
           # ... остальной код ...
       ```

5. **Обработчики колбэков**:
   - Функция `handle_callback` обрабатывает нажатия на инлайн-кнопки.
   - Для добавления новой кнопки:
     - Создайте новую клавиатуру или добавьте кнопку в существующую, например, в `main_menu_keyboard`:

       ```python
       def main_menu_keyboard(user_id):
           keyboard = [
               ['👤 Профиль', '📰 Лента', '📑 Закладки'],
               ['📝 Создать пост', '💬 Сообщения', '👥 Группы'],
               ['🛒 Маркет', '📸 Истории', '💰 Экономика'],
               ['🔔 Уведомления', '⚙️ Настройки', 'ℹ️ Помощь'],
               ['❌ Отмена', '🆕 Новая функция']  # Новая кнопка
           ]
           if is_admin(user_id):
               keyboard.insert(0, ['🛠️ Админ-панель'])
           return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
       ```

     - Добавьте обработку в `handle_message`:

       ```python
       elif text == '🆕 Новая функция':
           await message.reply_text("Новая функция в разработке!")
       ```

6. **Клавиатуры**:
   - Клавиатуры (ReplyKeyboardMarkup и InlineKeyboardMarkup) определены в функциях, таких как `main_menu_keyboard`, `profile_menu_keyboard` и т.д.
   - Для изменения меню добавьте или удалите кнопки в соответствующих функциях.

7. **Экономика и достижения**:
   - Функции `add_currency`, `daily_bonus`, `transfer_currency` управляют виртуальной валютой.
   - Для изменения логики начисления монет или условий достижений:
     - Измените функцию `award_achievement` или `check_achievements`.
     - Например, для нового достижения за 100 постов:

       ```python
       def check_achievements(user_id):
           # ... существующий код ...
           if post_count >= 100:
               award_achievement(user_id, 'pro_poster', 'Опубликовал 100 постов')
       ```

8. **Уведомления**:
   - Уведомления обрабатываются функцией `send_notification`.
   - Для добавления нового типа уведомлений:
     - Добавьте новый тип в функцию `send_notification` и обработайте его в `show_notifications`.

9. **Логирование**:
   - Логирование настроено с помощью модуля `logging`. Для изменения уровня логов или формата:
     - Найдите блок `logging.basicConfig` и измените параметры, например:

       ```python
       logging.basicConfig(
           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
           level=logging.DEBUG  # Изменено с INFO на DEBUG для более подробных логов
       )
       ```

## Примеры модификаций

### 1. Изменение лимита постов в ленте
Для изменения количества постов, отображаемых в ленте:
- Найдите функцию `get_feed_posts` или `get_smart_feed`.
- Измените параметр `limit`:

```python
def get_feed_posts(user_id, limit=20, offset=0):  # Изменено с limit=10 на limit=20
    # ... остальной код ...
```

### 2. Добавление новой команды `/profile`
Для добавления команды просмотра профиля:
- Создайте функцию:

```python
async def profile_cmd(update: Update, context: CallbackContext):
    await show_profile(update.message, context)
```

- Добавьте в `main()`:

```python
command_handlers = [
    # ... существующие обработчики ...
    CommandHandler("profile", profile_cmd),
]
```

### 3. Изменение структуры базы данных
Для добавления нового поля в таблицу `users`:
- В блоке `cursor.executescript` добавьте новое поле в таблицу `users`:

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    nickname TEXT UNIQUE,
    reg_date TEXT,
    last_seen TEXT,
    is_private BOOLEAN DEFAULT 0,
    bio TEXT DEFAULT '',
    new_field TEXT DEFAULT ''  -- Новое поле
);
```

- Обновите функции работы с пользователями (`register_user`, `update_user_profile`, `get_user_by_id`), чтобы обрабатывать новое поле.

## Тестирование изменений
1. Убедитесь, что у вас установлены все зависимости:
   ```bash
   pip install python-telegram-bot sqlite3
   ```
2. Запустите бота локально:
   ```bash
   python bot.py
   ```
3. Проверьте новый функционал через Telegram, взаимодействуя с ботом.
4. Следите за логами в консоли для отладки ошибок.

## Размещение изменений на Git
1. Создайте ветку для изменений:
   ```bash
   git checkout -b feature/new-functionality
   ```
2. Внесите изменения в код.
3. Зафиксируйте изменения:
   ```bash
   git add .
   git commit -m "Добавлен новый функционал: описание"
   ```
4. Отправьте изменения в репозиторий:
   ```bash
   git push origin feature/new-functionality
   ```
5. Создайте Pull Request на GitHub для ревью кода.

## Рекомендации
- Всегда делайте резервную копию базы данных (`111.db`) перед внесением изменений в структуру.
- Проверяйте SQL-запросы на синтаксические ошибки с помощью SQLite-клиента.
- Тестируйте новый функционал на тестовом боте с отдельным токеном, чтобы избежать влияния на продакшен.

