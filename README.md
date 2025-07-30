# Подробная инструкция: Как изменить токен Telegram-бота и запустить его через командную строку

## 1. Подготовка кода бота
Предположим, у вас есть готовый код бота (`bot.py`). Для работы с токеном используйте один из подходов:

### Вариант 1: Токен хранится в коде (простой способ)
Найдите в коде строку с токеном (обычно выглядит так):
```python
TOKEN = "ВАШ_СТАРЫЙ_ТОКЕН"
```
Замените `ВАШ_СТАРЫЙ_ТОКЕН` на новый токен:
```python
TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

### Вариант 2: Токен через аргументы командной строки (рекомендуется)
Добавьте обработку аргументов в код:
```python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="Telegram Bot Token", required=True)
    args = parser.parse_args()
    
    TOKEN = args.token
    # Ваш основной код бота

if __name__ == "__main__":
    main()
```

## 2. Получение нового токена бота
1. Откройте Telegram, найдите `@BotFather`
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Укажите имя бота (например: `MyDemoBot`)
   - Укажите username бота (должен заканчиваться на `bot`, например: `MyDemoTestBot`)
4. Скопируйте выданный токен (формат: `123456:ABC-DEF1234ghIkl...`)

## 3. Запуск бота через командную строку

### Для Windows:
1. Откройте командную строку (`Win + R` → `cmd` → Enter)
2. Перейдите в папку с ботом:
```cmd
cd C:\путь\к\папке\с\ботом
```
3. Запустите бот:
   - Если токен в коде:
   ```cmd
   python bot.py
   ```
   - Если токен передается аргументом:
   ```cmd
   python bot.py --token=ВАШ_НОВЫЙ_ТОКЕН
   ```

### Для Linux/macOS:
1. Откройте терминал
2. Перейдите в папку с ботом:
```bash
cd /путь/к/папке/с/ботом
```
3. Запустите бот:
   - Если токен в коде:
   ```bash
   python3 bot.py
   ```
   - Если токен передается аргументом:
   ```bash
   python3 bot.py --token=ВАШ_НОВЫЙ_ТОКЕН
   ```

---

## 🔍 Частые проблемы и решения

| Проблема                  | Решение                                                                 |
|---------------------------|-------------------------------------------------------------------------|
| `ModuleNotFoundError`     | Установите зависимости: `pip install python-telegram-bot`               |
| `Invalid token`           | Проверьте опечатки в токене, формат должен быть `число:строка`          |
| Бот не отвечает           | Проверьте запущенный скрипт и интернет-соединение                      |
| Остановка бота            | Нажмите `Ctrl + C` в терминале                                         |

---

## 🧩 Пример готового кода (`bot.py`)
```python
from telegram.ext import Updater, CommandHandler
import argparse

def start(update, context):
    update.message.reply_text("Привет! Я работаю с новым токеном!")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="Токен бота")
    args = parser.parse_args()
    
    updater = Updater(args.token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    
    updater.start_polling()
    print("✅ Бот запущен!")
    updater.idle()

if __name__ == "__main__":
    main()
```

## 💡 Советы
- **Безопасность**: Никогда не публикуйте токен в открытых репозиториях. Добавьте в `.gitignore`:
  ```
  *.env
  *.secret
  ```
- **Переменные окружения** (альтернативный способ):
  ```bash
  # Linux/macOS
  export BOT_TOKEN="ВАШ_ТОКЕН"
  
  # Windows
  set BOT_TOKEN="ВАШ_ТОКЕН"
  ```
  Использование в коде:
  ```python
  import os
  TOKEN = os.getenv("BOT_TOKEN")
  ```

> Теперь вы можете легко менять токен и запускать бота! Для вопросов используйте команду `/help` в боте или пишите в комментарии 😊
