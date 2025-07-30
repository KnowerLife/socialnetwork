import datetime
import sqlite3
import re
import logging
import random
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройка базы данных
conn = sqlite3.connect('111.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.executescript('''
-- Основные таблицы
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    nickname TEXT UNIQUE,
    reg_date TEXT,
    last_seen TEXT,
    is_private BOOLEAN DEFAULT 0,
    bio TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS friends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    friend_id INTEGER,
    status TEXT CHECK(status IN ('pending', 'accepted', 'rejected')) DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (friend_id) REFERENCES users(user_id),
    UNIQUE(user_id, friend_id)
);

CREATE TABLE IF NOT EXISTS posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT,
    post_date TEXT,
    group_id INTEGER,
    media_type TEXT,  -- 'photo', 'video', 'document', 'sticker'
    media_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);

CREATE TABLE IF NOT EXISTS hashtags (
    hashtag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS post_hashtags (
    post_id INTEGER,
    hashtag_id INTEGER,
    PRIMARY KEY (post_id, hashtag_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id),
    FOREIGN KEY (hashtag_id) REFERENCES hashtags(hashtag_id)
);

CREATE TABLE IF NOT EXISTS likes (
    like_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    user_id INTEGER,
    like_date TEXT,
    reaction TEXT DEFAULT 'like',
    FOREIGN KEY (post_id) REFERENCES posts(post_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(post_id, user_id)
);

CREATE TABLE IF NOT EXISTS comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    user_id INTEGER,
    content TEXT,
    comment_date TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(post_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    content TEXT,
    related_id INTEGER,
    notification_date TEXT,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    content TEXT,
    timestamp TEXT,
    is_read BOOLEAN DEFAULT 0,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (receiver_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    creator_id INTEGER,
    description TEXT,
    is_public BOOLEAN DEFAULT 1,
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER,
    user_id INTEGER,
    role TEXT CHECK(role IN ('admin', 'moderator', 'member')) DEFAULT 'member',
    joined_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS blocks (
    blocker_id INTEGER,
    blocked_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (blocker_id, blocked_id),
    FOREIGN KEY (blocker_id) REFERENCES users(user_id),
    FOREIGN KEY (blocked_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS currencies (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    last_claim TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER,
    target_id INTEGER,
    target_type TEXT CHECK(target_type IN ('post', 'user', 'item', 'ad')),
    reason TEXT,
    report_date TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (reporter_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    post_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id),
    UNIQUE(user_id, post_id)
);

CREATE TABLE IF NOT EXISTS marketplace (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER,
    title TEXT,
    description TEXT,
    price INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    status TEXT CHECK(status IN ('active', 'sold', 'cancelled')) DEFAULT 'active',
    media_id TEXT,
    media_type TEXT,
    FOREIGN KEY (seller_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS ads (
    ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER,
    content TEXT,
    price INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'active', 'expired')) DEFAULT 'pending',
    media_id TEXT,
    media_type TEXT,
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    role TEXT CHECK(role IN ('admin', 'moderator', 'superadmin')) DEFAULT 'admin',
    appointed_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Новые таблицы для историй
CREATE TABLE IF NOT EXISTS stories (
    story_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    media_id TEXT,
    media_type TEXT CHECK(media_type IN ('photo', 'video', 'text')),
    content TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT DEFAULT (datetime('now', '+24 hours')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Новые таблицы для трансляций
CREATE TABLE IF NOT EXISTS live_streams (
    stream_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    group_id INTEGER,
    title TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    status TEXT CHECK(status IN ('active', 'ended')) DEFAULT 'active',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);

-- Новые таблицы для достижений
CREATE TABLE IF NOT EXISTS achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    description TEXT,
    earned_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Новые таблицы для настроек уведомлений
CREATE TABLE IF NOT EXISTS notification_settings (
    user_id INTEGER PRIMARY KEY,
    notify_likes BOOLEAN DEFAULT 1,
    notify_comments BOOLEAN DEFAULT 1,
    notify_mentions BOOLEAN DEFAULT 1,
    notify_friend_requests BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id);
CREATE INDEX IF NOT EXISTS idx_friends_friend ON friends(friend_id);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_seller ON marketplace(seller_id);
CREATE INDEX IF NOT EXISTS idx_ads_creator ON ads(creator_id);
''')
conn.commit()

# Вспомогательные функции
def is_member(user_id, group_id):
    cursor.execute('SELECT * FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
    return cursor.fetchone() is not None

def is_blocked(blocker_id, blocked_id):
    cursor.execute('SELECT * FROM blocks WHERE blocker_id = ? AND blocked_id = ?', (blocker_id, blocked_id))
    return cursor.fetchone() is not None

def can_access_post(user_id, post_id):
    cursor.execute('SELECT p.user_id, p.group_id FROM posts p WHERE post_id = ?', (post_id,))
    post = cursor.fetchone()
    if not post:
        return False
    
    author_id, group_id = post
    if is_blocked(author_id, user_id) or is_blocked(user_id, author_id):
        return False
    
    if group_id:
        return is_member(user_id, group_id)
    return True

def extract_hashtags(text):
    return set(re.findall(r"#(\w+)", text.lower()))

def extract_mentions(text):
    return set(re.findall(r"@(\w+)", text.lower()))

def validate_text_length(text, max_length, field_name):
    if len(text) > max_length:
        raise ValueError(f"❌ {field_name} слишком длинный (макс. {max_length} символов)")
    return text

def is_admin(user_id):
    cursor.execute('SELECT role FROM admins WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

# Функции для работы с пользователями
def register_user(user_id, nickname, is_private=False, bio=''):
    try:
        nickname = validate_text_length(nickname.strip(), 30, "Никнейм")
        cursor.execute('''
        INSERT INTO users (user_id, nickname, reg_date, last_seen, is_private, bio)
        VALUES (?, ?, datetime('now'), datetime('now'), ?, ?)
        ''', (user_id, nickname, int(is_private), bio))
        cursor.execute('INSERT OR IGNORE INTO currencies (user_id) VALUES (?)', (user_id,))
        cursor.execute('INSERT OR IGNORE INTO notification_settings (user_id) VALUES (?)', (user_id,))
        conn.commit()
        return True
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка регистрации: {e}")
        return False

def update_user_profile(user_id, **kwargs):
    try:
        if 'nickname' in kwargs:
            nickname = validate_text_length(kwargs['nickname'].strip(), 30, "Никнейм")
            cursor.execute('UPDATE users SET nickname = ? WHERE user_id = ?', (nickname, user_id))
        if 'bio' in kwargs:
            bio = validate_text_length(kwargs['bio'], 200, "Описание")
            cursor.execute('UPDATE users SET bio = ? WHERE user_id = ?', (bio, user_id))
        if 'is_private' in kwargs:
            cursor.execute('UPDATE users SET is_private = ? WHERE user_id = ?', (int(kwargs['is_private']), user_id))
        cursor.execute('UPDATE users SET last_seen = datetime("now") WHERE user_id = ?', (user_id,))
        conn.commit()
        return True
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка обновления профиля: {e}")
        return False

def get_user_by_id(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "user_id": row[0],
        "nickname": row[1],
        "reg_date": row[2],
        "last_seen": row[3],
        "is_private": bool(row[4]),
        "bio": row[5] if len(row) > 5 else ""
    }

def get_user_by_nickname(nickname):
    cursor.execute('SELECT * FROM users WHERE nickname = ?', (nickname,))
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "user_id": row[0],
        "nickname": row[1],
        "reg_date": row[2],
        "last_seen": row[3],
        "is_private": bool(row[4]),
        "bio": row[5] if len(row) > 5 else ""
    }

def is_registered(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

# Функции для друзей и блокировок
def send_friend_request(user_id, friend_nickname):
    friend = get_user_by_nickname(friend_nickname)
    if not friend or friend['user_id'] == user_id:
        return False
    
    friend_id = friend['user_id']
    is_private = friend['is_private']
    
    cursor.execute('''
    SELECT status FROM friends 
    WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
    ''', (user_id, friend_id, friend_id, user_id))
    existing = cursor.fetchone()
    if existing:
        return False
    
    if not is_private:
        try:
            cursor.execute('INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, "accepted")', (user_id, friend_id))
            cursor.execute('INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, "accepted")', (friend_id, user_id))
            conn.commit()
            sender = get_user_by_id(user_id)
            send_notification(friend_id, 'friend_accepted', f'Вы теперь дружите с {sender["nickname"]}!', user_id)
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления друга: {e}")
            return False
    
    try:
        cursor.execute('INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, "pending")', (user_id, friend_id))
        conn.commit()
        sender = get_user_by_id(user_id)
        send_notification(friend_id, 'friend_request', f'Запрос на дружбу от {sender["nickname"]}', user_id)
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка отправки запроса: {e}")
        return False

def respond_friend_request(user_id, friend_id, accept=True):
    status = 'accepted' if accept else 'rejected'
    cursor.execute('''
    UPDATE friends SET status = ?
    WHERE user_id = ? AND friend_id = ? AND status = 'pending'
    ''', (status, friend_id, user_id))
    
    if cursor.rowcount == 0:
        return False
    
    if accept:
        cursor.execute('INSERT OR IGNORE INTO friends (user_id, friend_id, status) VALUES (?, ?, "accepted")', (user_id, friend_id))
    conn.commit()
    
    responder = get_user_by_id(user_id)
    content = f'Ваш запрос дружбы {"принят" if accept else "отклонен"} пользователем {responder["nickname"]}'
    send_notification(friend_id, 'friend_response', content, user_id)
    return True

def block_user(blocker_id, blocked_nickname):
    blocked = get_user_by_nickname(blocked_nickname)
    if not blocked or blocked['user_id'] == blocker_id:
        return False
    
    blocked_id = blocked['user_id']
    if is_blocked(blocker_id, blocked_id):
        return False
    
    cursor.execute('''
    DELETE FROM friends 
    WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
    ''', (blocker_id, blocked_id, blocked_id, blocker_id))
    
    cursor.execute('INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)', (blocker_id, blocked_id))
    conn.commit()
    return True

def unblock_user(blocker_id, blocked_nickname):
    blocked = get_user_by_nickname(blocked_nickname)
    if not blocked:
        return False

    blocked_id = blocked['user_id']
    if not is_blocked(blocker_id, blocked_id):
        return False

    cursor.execute('DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?', (blocker_id, blocked_id))
    conn.commit()
    return cursor.rowcount > 0

# Функции для постов и ленты
def create_post(user_id, content, group_id=None, media_type=None, media_id=None):
    try:
        content = validate_text_length(content, 1000, "Текст поста")
        cursor.execute('''
        INSERT INTO posts (user_id, content, post_date, group_id, media_type, media_id)
        VALUES (?, ?, datetime('now'), ?, ?, ?)
        ''', (user_id, content, group_id, media_type, media_id))
        post_id = cursor.lastrowid
        
        hashtags = extract_hashtags(content)
        for tag in hashtags:
            cursor.execute('INSERT OR IGNORE INTO hashtags (name) VALUES (?)', (tag,))
            cursor.execute('SELECT hashtag_id FROM hashtags WHERE name = ?', (tag,))
            hashtag_id = cursor.fetchone()[0]
            cursor.execute('INSERT OR IGNORE INTO post_hashtags (post_id, hashtag_id) VALUES (?, ?)', (post_id, hashtag_id))
        
        # Проверка достижений
        cursor.execute('SELECT COUNT(*) FROM posts WHERE user_id = ?', (user_id,))
        post_count = cursor.fetchone()[0]
        if post_count % 10 == 0:  # Награда каждые 10 постов
            award_achievement(user_id, 'active_poster', f'Опубликовал {post_count} постов')
        
        conn.commit()
        return post_id
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка создания поста: {e}")
        conn.rollback()
        return None

def get_feed_posts(user_id, limit=10, offset=0):
    cursor.execute('''
    SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type
    FROM posts p
    JOIN users u ON p.user_id = u.user_id
    WHERE (
        p.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'accepted')
        OR p.group_id IN (SELECT group_id FROM group_members WHERE user_id = ?)
    )
    AND NOT EXISTS (SELECT 1 FROM blocks 
                   WHERE (blocker_id = ? AND blocked_id = p.user_id)
                   OR (blocker_id = p.user_id AND blocked_id = ?))
    ORDER BY p.post_date DESC
    LIMIT ? OFFSET ?
    ''', (user_id, user_id, user_id, user_id, limit, offset))
    return cursor.fetchall()

def get_smart_feed(user_id, limit=10, offset=0):
    cursor.execute('''
    SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type,
           COUNT(l.like_id) as like_count, COUNT(c.comment_id) as comment_count
    FROM posts p
    JOIN users u ON p.user_id = u.user_id
    LEFT JOIN likes l ON p.post_id = l.post_id
    LEFT JOIN comments c ON p.post_id = c.post_id
    WHERE (
        p.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'accepted')
        OR p.group_id IN (SELECT group_id FROM group_members WHERE user_id = ?)
        OR p.post_id IN (SELECT ph.post_id FROM post_hashtags ph 
                        JOIN hashtags h ON ph.hashtag_id = h.hashtag_id
                        WHERE h.name IN (SELECT h2.name FROM post_hashtags ph2 
                                        JOIN hashtags h2 ON ph2.hashtag_id = h2.hashtag_id
                                        JOIN posts p2 ON ph2.post_id = p2.post_id
                                        WHERE p2.user_id = ?))
    )
    AND NOT EXISTS (SELECT 1 FROM blocks 
                   WHERE (blocker_id = ? AND blocked_id = p.user_id)
                   OR (blocker_id = p.user_id AND blocked_id = ?))
    GROUP BY p.post_id
    ORDER BY (like_count * 2 + comment_count * 3 + 
              CASE WHEN p.post_date > datetime('now', '-1 day') THEN 10 ELSE 0 END) DESC
    LIMIT ? OFFSET ?
    ''', (user_id, user_id, user_id, user_id, user_id, limit, offset))
    return cursor.fetchall()

def get_popular_posts(user_id, limit=5, offset=0):
    cursor.execute('''
    SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type,
           COUNT(l.like_id) as like_count,
           COUNT(c.comment_id) as comment_count
    FROM posts p
    JOIN users u ON p.user_id = u.user_id
    LEFT JOIN likes l ON p.post_id = l.post_id
    LEFT JOIN comments c ON p.post_id = c.post_id
    WHERE (
        p.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'accepted')
        OR p.group_id IN (SELECT group_id FROM group_members WHERE user_id = ?)
    )
    AND NOT EXISTS (SELECT 1 FROM blocks 
                   WHERE (blocker_id = ? AND blocked_id = p.user_id)
                   OR (blocker_id = p.user_id AND blocked_id = ?))
    GROUP BY p.post_id
    ORDER BY (like_count + comment_count) DESC, p.post_date DESC
    LIMIT ? OFFSET ?
    ''', (user_id, user_id, user_id, user_id, limit, offset))
    return cursor.fetchall()

def get_trending_hashtags(limit=10):
    cursor.execute('''
    SELECT h.name, COUNT(ph.post_id) as post_count
    FROM hashtags h
    JOIN post_hashtags ph ON h.hashtag_id = ph.hashtag_id
    JOIN posts p ON ph.post_id = p.post_id
    WHERE p.post_date > datetime('now', '-1 day')
    GROUP BY h.hashtag_id
    ORDER BY post_count DESC
    LIMIT ?
    ''', (limit,))
    return cursor.fetchall()

def like_post(user_id, post_id, reaction='like'):
    if not can_access_post(user_id, post_id):
        return False
    
    try:
        cursor.execute('''
        INSERT INTO likes (post_id, user_id, like_date, reaction) 
        VALUES (?, ?, datetime("now"), ?)
        ON CONFLICT(post_id, user_id) DO UPDATE SET reaction = ?
        ''', (post_id, user_id, reaction, reaction))
        
        post_author = cursor.execute('SELECT user_id FROM posts WHERE post_id = ?', (post_id,)).fetchone()[0]
        liker = get_user_by_id(user_id)
        
        # Проверяем настройки уведомлений
        cursor.execute('SELECT notify_likes FROM notification_settings WHERE user_id = ?', (post_author,))
        setting = cursor.fetchone()
        if setting and setting[0]:
            send_notification(post_author, 'like', f'@{liker["nickname"]} поставил реакцию {reaction} на ваш пост', post_id)
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка реакции на пост: {e}")
        return False

def comment_post(user_id, post_id, content):
    if not can_access_post(user_id, post_id):
        return False
    
    try:
        content = validate_text_length(content, 500, "Комментарий")
        cursor.execute('''
        INSERT INTO comments (post_id, user_id, content, comment_date)
        VALUES (?, ?, ?, datetime("now"))
        ''', (post_id, user_id, content))
        
        post_author = cursor.execute('SELECT user_id FROM posts WHERE post_id = ?', (post_id,)).fetchone()[0]
        commenter = get_user_by_id(user_id)
        
        # Проверяем настройки уведомлений
        cursor.execute('SELECT notify_comments FROM notification_settings WHERE user_id = ?', (post_author,))
        setting = cursor.fetchone()
        if setting and setting[0]:
            send_notification(post_author, 'comment', f'Новый комментарий от {commenter["nickname"]}: {content[:50]}...', post_id)
        
        # Отправляем уведомления об упоминаниях
        mentions = extract_mentions(content)
        for mention in mentions:
            target = get_user_by_nickname(mention)
            if target:
                target_id = target['user_id']
                cursor.execute('SELECT notify_mentions FROM notification_settings WHERE user_id = ?', (target_id,))
                mention_setting = cursor.fetchone()
                if mention_setting and mention_setting[0]:
                    send_notification(target_id, 'mention', 
                                    f'@{commenter["nickname"]} упомянул вас в комментарии', post_id)
        
        conn.commit()
        return True
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка комментария: {e}")
        return False

def repost(user_id, post_id):
    original = cursor.execute('SELECT * FROM posts WHERE post_id = ?', (post_id,)).fetchone()
    if not original or not can_access_post(user_id, post_id):
        return None
    
    _, orig_user_id, content, post_date, group_id, media_type, media_id = original
    new_post_id = create_post(user_id, f"🔁 Репост: {content}", group_id, media_type, media_id)
    return new_post_id

# Функции для закладок
def add_bookmark(user_id, post_id):
    if not can_access_post(user_id, post_id):
        return False
    try:
        cursor.execute('INSERT INTO bookmarks (user_id, post_id) VALUES (?, ?)', (user_id, post_id))
        conn.commit()
        return True
    except sqlite3.Error:
        return False

def remove_bookmark(user_id, post_id):
    cursor.execute('DELETE FROM bookmarks WHERE user_id = ? AND post_id = ?', (user_id, post_id))
    conn.commit()
    return cursor.rowcount > 0

def get_bookmarks(user_id, limit=10, offset=0):
    cursor.execute('''
    SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type
    FROM bookmarks b
    JOIN posts p ON b.post_id = p.post_id
    JOIN users u ON p.user_id = u.user_id
    WHERE b.user_id = ?
    ORDER BY b.created_at DESC
    LIMIT ? OFFSET ?
    ''', (user_id, limit, offset))
    return cursor.fetchall()

# Функции для маркета
def create_market_item(seller_id, title, description, price, media_id=None, media_type=None):
    try:
        title = validate_text_length(title, 100, "Название товара")
        description = validate_text_length(description, 500, "Описание товара")
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        cursor.execute('''
        INSERT INTO marketplace (seller_id, title, description, price, media_id, media_type)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (seller_id, title, description, price, media_id, media_type))
        conn.commit()
        return cursor.lastrowid
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка создания товара: {e}")
        return None

def get_market_items(limit=10, offset=0):
    cursor.execute('''
    SELECT m.item_id, m.title, m.description, m.price, m.created_at, u.nickname, m.media_id, m.media_type
    FROM marketplace m
    JOIN users u ON m.seller_id = u.user_id
    WHERE m.status = 'active'
    ORDER BY m.created_at DESC
    LIMIT ? OFFSET ?
    ''', (limit, offset))
    return cursor.fetchall()

def buy_item(buyer_id, item_id):
    cursor.execute('SELECT seller_id, price FROM marketplace WHERE item_id = ? AND status = "active"', (item_id,))
    item = cursor.fetchone()
    if not item:
        return "❌ Товар не найден или уже продан"
    seller_id, price = item
    balance = get_currency(buyer_id)
    if balance < price:
        return "❌ Недостаточно монет"
    try:
        cursor.execute('UPDATE currencies SET balance = balance - ? WHERE user_id = ?', (price, buyer_id))
        cursor.execute('UPDATE currencies SET balance = balance + ? WHERE user_id = ?', (price, seller_id))
        cursor.execute('UPDATE marketplace SET status = "sold" WHERE item_id = ?', (item_id,))
        conn.commit()
        buyer = get_user_by_id(buyer_id)
        send_notification(seller_id, 'item_sold', f'Ваш товар "{item_id}" купил @{buyer["nickname"]}!', item_id)
        return "✅ Покупка успешна!"
    except sqlite3.Error as e:
        logger.error(f"Ошибка покупки: {e}")
        conn.rollback()
        return "❌ Ошибка покупки"

# Функции для рекламы
def create_ad(creator_id, content, price, media_id=None, media_type=None):
    try:
        content = validate_text_length(content, 500, "Текст рекламы")
        if price < 0:
            raise ValueError("Цена не может быть отрицательной")
        cursor.execute('''
        INSERT INTO ads (creator_id, content, price, media_id, media_type)
        VALUES (?, ?, ?, ?, ?)
        ''', (creator_id, content, price, media_id, media_type))
        conn.commit()
        return cursor.lastrowid
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка создания рекламы: {e}")
        return None

def get_ads(limit=5, offset=0):
    cursor.execute('''
    SELECT a.ad_id, a.content, a.created_at, u.nickname, a.media_id, a.media_type
    FROM ads a
    JOIN users u ON a.creator_id = u.user_id
    WHERE a.status = 'active'
    ORDER BY a.created_at DESC
    LIMIT ? OFFSET ?
    ''', (limit, offset))
    return cursor.fetchall()

# Функции для администрирования
def appoint_admin(user_id, appointed_by, role='admin'):
    try:
        cursor.execute('INSERT INTO admins (user_id, role, appointed_at) VALUES (?, ?, datetime("now"))', 
                      (user_id, role))
        conn.commit()
        return True
    except sqlite3.Error:
        return False

def remove_admin(user_id):
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    return cursor.rowcount > 0

def ban_user(admin_id, target_nickname, reason):
    if not is_admin(admin_id):
        return "❌ Вы не администратор"
    target = get_user_by_nickname(target_nickname)
    if not target:
        return "❌ Пользователь не найден"
    target_id = target['user_id']
    try:
        cursor.execute('INSERT INTO blocks (blocker_id, blocked_id) VALUES (?, ?)', (0, target_id))  # 0 - системный блок
        cursor.execute('UPDATE users SET is_private = 1 WHERE user_id = ?', (target_id,))
        conn.commit()
        send_notification(target_id, 'ban', f'Вы были забанены. Причина: {reason}', admin_id)
        return f"✅ Пользователь @{target_nickname} забанен"
    except sqlite3.Error:
        return "❌ Ошибка бана"

def review_ad(admin_id, ad_id, approve=True):
    if not is_admin(admin_id):
        return "❌ Вы не администратор"
    status = 'active' if approve else 'rejected'
    cursor.execute('UPDATE ads SET status = ? WHERE ad_id = ?', (status, ad_id))
    conn.commit()
    if cursor.rowcount > 0:
        ad = cursor.execute('SELECT creator_id, content FROM ads WHERE ad_id = ?', (ad_id,)).fetchone()
        if ad:
            creator_id, content = ad
            send_notification(creator_id, 'ad_review', 
                            f'Ваша реклама {"одобрена" if approve else "отклонена"}', ad_id)
        return f"✅ Реклама ID {ad_id} {'одобрена' if approve else 'отклонена'}"
    return "❌ Реклама не найдена"

def delete_post(admin_id, post_id):
    if not is_admin(admin_id):
        return "❌ Вы не администратор"
    cursor.execute('DELETE FROM posts WHERE post_id = ?', (post_id,))
    conn.commit()
    return "✅ Пост удален" if cursor.rowcount > 0 else "❌ Пост не найден"

# Функции для уведомлений
def send_notification(user_id, type, content, related_id=None):
    try:
        content = validate_text_length(content, 200, "Уведомление")
        cursor.execute('''
        INSERT INTO notifications (user_id, type, content, related_id, notification_date)
        VALUES (?, ?, ?, ?, datetime("now"))
        ''', (user_id, type, content, related_id))
        conn.commit()
        return True
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка уведомления: {e}")
        return False

def mark_notification_read(notification_id):
    cursor.execute('UPDATE notifications SET is_read = 1 WHERE notification_id = ?', (notification_id,))
    conn.commit()

# Функции для сообщений
def send_private_message(sender_id, receiver_nickname, message):
    receiver = get_user_by_nickname(receiver_nickname)
    if not receiver:
        return False
    
    receiver_id = receiver['user_id']
    if is_blocked(receiver_id, sender_id) or is_blocked(sender_id, receiver_id):
        return False
    
    try:
        message = validate_text_length(message, 1000, "Сообщение")
        cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, content, timestamp)
        VALUES (?, ?, ?, datetime("now"))
        ''', (sender_id, receiver_id, message))
        sender = get_user_by_id(sender_id)
        send_notification(receiver_id, 'message', f'Новое сообщение от {sender["nickname"]}', sender_id)
        conn.commit()
        return True
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка сообщения: {e}")
        return False

# Функции для групп
def create_group(user_id, name, description, is_public=True):
    try:
        name = validate_text_length(name, 50, "Название группы")
        description = validate_text_length(description, 200, "Описание группы")
        cursor.execute('''
        INSERT INTO groups (name, creator_id, description, is_public)
        VALUES (?, ?, ?, ?)
        ''', (name, user_id, description, int(is_public)))
        group_id = cursor.lastrowid
        cursor.execute('INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, "admin")', (group_id, user_id))
        conn.commit()
        return group_id
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка создания группы: {e}")
        return None

def join_group(user_id, group_id):
    cursor.execute('SELECT is_public FROM groups WHERE group_id = ?', (group_id,))
    group = cursor.fetchone()
    if not group:
        return False
    
    is_public = bool(group[0])
    if not is_public:
        return False
    
    cursor.execute('INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

# Функции для экономики
def get_currency(user_id):
    cursor.execute('SELECT balance FROM currencies WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def add_currency(user_id, amount):
    cursor.execute('UPDATE currencies SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def daily_bonus(user_id):
    try:
        today = datetime.date.today().isoformat()
        cursor.execute('SELECT last_claim FROM currencies WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        last_claim = result[0] if result else None
        
        if last_claim is None or last_claim != today:
            add_currency(user_id, 10)
            cursor.execute('UPDATE currencies SET last_claim = ? WHERE user_id = ?', (today, user_id))
            conn.commit()
            return True
        return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка бонуса: {e}")
        return False

def transfer_currency(sender_id, receiver_nickname, amount):
    try:
        amount = int(amount)
        if amount <= 0:
            return "❌ Сумма должна быть положительной"
        
        sender_balance = get_currency(sender_id)
        if sender_balance < amount:
            return "❌ Недостаточно средств"
        
        receiver = get_user_by_nickname(receiver_nickname)
        if not receiver:
            return "❌ Пользователь не найден"
        
        receiver_id = receiver['user_id']
        if sender_id == receiver_id:
            return "❌ Нельзя переводить самому себе"
        
        if is_blocked(receiver_id, sender_id) or is_blocked(sender_id, receiver_id):
            return "❌ Пользователь заблокирован"
        
        cursor.execute('UPDATE currencies SET balance = balance - ? WHERE user_id = ?', (amount, sender_id))
        cursor.execute('UPDATE currencies SET balance = balance + ? WHERE user_id = ?', (amount, receiver_id))
        conn.commit()
        
        sender = get_user_by_id(sender_id)
        send_notification(receiver_id, 'transfer', f'Вы получили {amount} монет от {sender["nickname"]}', sender_id)
        return f"✅ Успешно переведено {amount} монет пользователю @{receiver_nickname}"
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка перевода: {e}")
        return "❌ Ошибка перевода"

# Функции для поиска
def search_users(keyword):
    cursor.execute('SELECT user_id, nickname FROM users WHERE nickname LIKE ? ORDER BY nickname LIMIT 20', (f'%{keyword}%',))
    return cursor.fetchall()

def search_groups(keyword):
    cursor.execute('SELECT group_id, name, description FROM groups WHERE name LIKE ? AND is_public = 1 ORDER BY name LIMIT 10', (f'%{keyword}%',))
    return cursor.fetchall()

def search_posts_by_hashtag(hashtag):
    cursor.execute('''
    SELECT p.post_id, p.content, u.nickname
    FROM posts p
    JOIN users u ON p.user_id = u.user_id
    JOIN post_hashtags ph ON p.post_id = ph.post_id
    JOIN hashtags h ON ph.hashtag_id = h.hashtag_id
    WHERE h.name = ?
    ORDER BY p.post_date DESC
    LIMIT 20
    ''', (hashtag.lower(),))
    return cursor.fetchall()

def search_content(keyword, user_id, limit=20):
    cursor.execute('''
    SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type
    FROM posts p
    JOIN users u ON p.user_id = u.user_id
    WHERE p.content LIKE ?
    AND (p.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'accepted')
         OR p.group_id IN (SELECT group_id FROM group_members WHERE user_id = ?)
         OR p.user_id = ?)
    AND NOT EXISTS (SELECT 1 FROM blocks 
                   WHERE (blocker_id = ? AND blocked_id = p.user_id)
                   OR (blocker_id = p.user_id AND blocked_id = ?))
    ORDER BY p.post_date DESC
    LIMIT ?
    ''', (f'%{keyword}%', user_id, user_id, user_id, user_id, user_id, limit))
    return cursor.fetchall()

# Функции для жалоб
def create_report(reporter_id, target_id, target_type, reason):
    try:
        reason = validate_text_length(reason, 200, "Причина жалобы")
        cursor.execute('''
        INSERT INTO reports (reporter_id, target_id, target_type, reason)
        VALUES (?, ?, ?, ?)
        ''', (reporter_id, target_id, target_type, reason))
        conn.commit()
        return True
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка жалобы: {e}")
        return False

# Новые функции для историй
def create_story(user_id, content=None, media_id=None, media_type=None):
    try:
        if content:
            content = validate_text_length(content, 200, "Текст истории")
        cursor.execute('''
        INSERT INTO stories (user_id, content, media_id, media_type)
        VALUES (?, ?, ?, ?)
        ''', (user_id, content, media_id, media_type))
        conn.commit()
        return cursor.lastrowid
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка создания истории: {e}")
        return None

def get_stories(user_id, limit=10):
    cursor.execute('''
    SELECT s.story_id, s.content, s.created_at, u.nickname, s.media_id, s.media_type
    FROM stories s
    JOIN users u ON s.user_id = u.user_id
    WHERE (s.user_id IN (SELECT friend_id FROM friends WHERE user_id = ? AND status = 'accepted')
           OR s.user_id = ?)
    AND s.expires_at > datetime('now')
    AND NOT EXISTS (SELECT 1 FROM blocks 
                   WHERE (blocker_id = ? AND blocked_id = s.user_id)
                   OR (blocker_id = s.user_id AND blocked_id = ?))
    ORDER BY s.created_at DESC
    LIMIT ?
    ''', (user_id, user_id, user_id, user_id, limit))
    return cursor.fetchall()

# Новые функции для трансляций
def start_live_stream(user_id, group_id, title):
    if not is_member(user_id, group_id):
        return None
    try:
        title = validate_text_length(title, 100, "Название трансляции")
        cursor.execute('''
        INSERT INTO live_streams (user_id, group_id, title)
        VALUES (?, ?, ?)
        ''', (user_id, group_id, title))
        stream_id = cursor.lastrowid
        cursor.execute('''
        INSERT INTO notifications (user_id, type, content, related_id, notification_date)
        SELECT gm.user_id, 'live_stream', ?, ?, datetime('now')
        FROM group_members gm WHERE gm.group_id = ?
        ''', (f'@{get_user_by_id(user_id)["nickname"]} начал трансляцию: {title}', stream_id, group_id))
        conn.commit()
        return stream_id
    except (ValueError, sqlite3.Error) as e:
        logger.error(f"Ошибка создания трансляции: {e}")
        return None

def end_live_stream(stream_id):
    cursor.execute('UPDATE live_streams SET status = "ended" WHERE stream_id = ?', (stream_id,))
    conn.commit()
    return cursor.rowcount > 0

# Новые функции для достижений
def award_achievement(user_id, type, description):
    try:
        cursor.execute('INSERT INTO achievements (user_id, type, description) VALUES (?, ?, ?)', 
                      (user_id, type, description))
        conn.commit()
        send_notification(user_id, 'achievement', f'🏆 Новое достижение: {description}', None)
        return True
    except sqlite3.Error:
        return False

def check_achievements(user_id):
    # Проверка достижений при различных действиях
    cursor.execute('SELECT COUNT(*) FROM posts WHERE user_id = ?', (user_id,))
    post_count = cursor.fetchone()[0]
    if post_count >= 10:
        award_achievement(user_id, 'active_poster', 'Опубликовал 10 постов')
    
    cursor.execute('SELECT COUNT(*) FROM friends WHERE user_id = ? AND status = "accepted"', (user_id,))
    friend_count = cursor.fetchone()[0]
    if friend_count >= 5:
        award_achievement(user_id, 'social_butterfly', 'Завел 5 друзей')
    
    cursor.execute('SELECT COUNT(*) FROM groups WHERE creator_id = ?', (user_id,))
    group_count = cursor.fetchone()[0]
    if group_count >= 3:
        award_achievement(user_id, 'group_leader', 'Создал 3 группы')

# Клавиатуры
def main_menu_keyboard(user_id):
    keyboard = [
        ['👤 Профиль', '📰 Лента', '📑 Закладки'],
        ['📝 Создать пост', '💬 Сообщения', '👥 Группы'],
        ['🛒 Маркет', '📸 Истории', '💰 Экономика'],
        ['🔔 Уведомления', '⚙️ Настройки', 'ℹ️ Помощь'],
        ['❌ Отмена']
    ]
    if is_admin(user_id):
        keyboard.insert(0, ['🛠️ Админ-панель'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def profile_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить никнейм", callback_data='change_nickname'),
         InlineKeyboardButton("📝 Изменить описание", callback_data='change_bio')],
        [InlineKeyboardButton("🔒 Изменить приватность", callback_data='toggle_privacy')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats'),
         InlineKeyboardButton("🏆 Достижения", callback_data='achievements')],
        [InlineKeyboardButton("📝 Мои посты", callback_data='my_posts')],  # Новая кнопка
        [InlineKeyboardButton("🚫 Заблокированные", callback_data='blocked_list')],
        [InlineKeyboardButton("👥 Друзья", callback_data='friends_list')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='main_menu')]
    ])

def feed_menu_keyboard(offset):
    keyboard = [
        [InlineKeyboardButton("📝 Создать пост", callback_data='create_post')],  # Новая кнопка
        [
            InlineKeyboardButton("👤 Посты друзей", callback_data='feed_friends'),
            InlineKeyboardButton("👥 Посты групп", callback_data='feed_groups')
        ],
        [InlineKeyboardButton("🔥 Популярные посты", callback_data='feed_popular')],
        [InlineKeyboardButton("🚀 Умная лента", callback_data='feed_smart')],
        [InlineKeyboardButton("📂 Фильтр", callback_data='filter_feed')],
        []
    ]
    
    if offset > 0:
        keyboard[5].append(InlineKeyboardButton("⬅️ Назад", callback_data=f'feed_prev_{offset-5}'))
    else:
        keyboard[5].append(InlineKeyboardButton(" ", callback_data='noop'))
    
    keyboard[5].append(InlineKeyboardButton("➡️ Далее", callback_data=f'feed_next_{offset+5}'))
    
    return InlineKeyboardMarkup(keyboard)

def filter_feed_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Все", callback_data='feed_all')],
        [InlineKeyboardButton("📸 Фото", callback_data='feed_photos')],
        [InlineKeyboardButton("🎥 Видео", callback_data='feed_videos')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ])

def messages_menu_keyboard():
    return ReplyKeyboardMarkup([
        ['📥 Входящие сообщения', '📤 Отправленные сообщения'],
        ['✉️ Новое сообщение', '👥 Контакты'],
        ['🏠 Главное меню']
    ], resize_keyboard=True, one_time_keyboard=True)

def groups_menu_keyboard():
    return ReplyKeyboardMarkup([
        ['👥 Мои группы', '📝 Создать группу'],
        ['🎥 Начать трансляцию', '🔍 Найти группу'],
        ['🏠 Главное меню']
    ], resize_keyboard=True, one_time_keyboard=True)

def economy_menu_keyboard():
    return ReplyKeyboardMarkup([
        ['💰 Мой баланс', '🎁 Получить бонус'],
        ['➡️ Перевод монет', '🏠 Главное меню']
    ], resize_keyboard=True, one_time_keyboard=True)

def search_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["👤 Поиск пользователей", "#️⃣ Поиск по хештегам"],
        ["👥 Поиск групп", "📜 Поиск по контенту"],
        ["🏠 Главное меню"]
    ], resize_keyboard=True, one_time_keyboard=True)

def market_menu_keyboard():
    return ReplyKeyboardMarkup([
        ['🛒 Просмотреть маркет', '📦 Мои товары'],
        ['💰 Продать товар', '🏠 Главное меню']
    ], resize_keyboard=True, one_time_keyboard=True)

def ad_menu_keyboard():
    return ReplyKeyboardMarkup([
        ['📢 Создать рекламу', '📊 Мои рекламы'],
        ['🏠 Главное меню']
    ], resize_keyboard=True, one_time_keyboard=True)

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("🚫 Бан пользователя", callback_data='admin_ban')],
        [InlineKeyboardButton("📢 Модерация рекламы", callback_data='admin_ads')],
        [InlineKeyboardButton("🗑️ Модерация контента", callback_data='admin_content')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ])

def notification_keyboard(notification_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Прочитано", callback_data=f'read_{notification_id}'),
            InlineKeyboardButton("❌ Удалить", callback_data=f'delete_{notification_id}')
        ]
    ])

def post_keyboard(post_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍", callback_data=f'reaction_{post_id}_like'),
            InlineKeyboardButton("❤️", callback_data=f'reaction_{post_id}_heart'),
            InlineKeyboardButton("😂", callback_data=f'reaction_{post_id}_laugh'),
            InlineKeyboardButton("😢", callback_data=f'reaction_{post_id}_sad'),
            InlineKeyboardButton("🔥", callback_data=f'reaction_{post_id}_fire')
        ],
        [
            InlineKeyboardButton("💬 Комментировать", callback_data=f'comment_{post_id}'),
            InlineKeyboardButton("🔄 Репост", callback_data=f'repost_{post_id}'),
            InlineKeyboardButton("📑 В закладки", callback_data=f'bookmark_{post_id}')
        ],
        [InlineKeyboardButton("📤 Поделиться", callback_data=f'share_{post_id}'),
         InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_post_{post_id}')]
    ])

async def show_my_posts(message, context: CallbackContext):
    user_id = message.from_user.id
    offset = context.user_data.get('my_posts_offset', 0)
    
    # Получаем посты с информацией о медиа
    cursor.execute('''
    SELECT p.post_id, p.content, p.post_date, p.media_id, p.media_type
    FROM posts p
    WHERE p.user_id = ?
    ORDER BY p.post_date DESC
    LIMIT 5 OFFSET ?
    ''', (user_id, offset))
    posts = cursor.fetchall()
    
    if not posts:
        await message.reply_text("📭 У вас пока нет постов.")
        return
        
    for post in posts:
        post_id, content, post_date, media_id, media_type = post
        date_str = post_date.split()[0] if post_date else "N/A"
        response = f"📝 <b>Ваш пост</b> от {date_str}:\n{content}\nID: {post_id}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f'delete_my_post_{post_id}')],
            [InlineKeyboardButton("📑 В закладки", callback_data=f'bookmark_{post_id}')]
        ])
        
        try:
            if media_type and media_id:
                if media_type == 'photo':
                    await message.reply_photo(photo=media_id, caption=response, 
                                            reply_markup=keyboard, parse_mode='HTML')
                elif media_type == 'video':
                    await message.reply_video(video=media_id, caption=response, 
                                            reply_markup=keyboard, parse_mode='HTML')
                elif media_type == 'document':
                    await message.reply_document(document=media_id, caption=response, 
                                               reply_markup=keyboard, parse_mode='HTML')
                elif media_type == 'sticker':
                    await message.reply_sticker(sticker=media_id)
                    await message.reply_text(response, reply_markup=keyboard, parse_mode='HTML')
            else:
                await message.reply_text(response, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка отображения поста: {e}")
            await message.reply_text(f"📝 Пост от {date_str}:\n{content}", 
                                   reply_markup=keyboard, parse_mode='HTML')
    
    # Навигация
    keyboard = []
    if offset > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'my_posts_prev_{offset-5}'))
    if len(posts) == 5:
        keyboard.append(InlineKeyboardButton("➡️ Далее", callback_data=f'my_posts_next_{offset+5}'))
    
    if keyboard:
        reply_markup = InlineKeyboardMarkup([keyboard])
        await message.reply_text("📝 Ваши посты:", reply_markup=reply_markup)
    
    context.user_data['my_posts_offset'] = offset

# Обработчики команд
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_registered(user_id):
        await update.message.reply_text(
            '👋 Добро пожаловать в SocialBot!\n\n'
            'Выберите уникальный никнейм для регистрации:',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        response = (
            "🏠 Добро пожаловать в главное меню!\n\n"
            "Основные возможности:\n"
            "• 📝 Создать пост - публикация новостей\n"
            "• 📰 Лента - просмотр обновлений\n"
            "• 📸 Истории - 24-часовые публикации\n"
            "• 🛒 Маркет - покупка и продажа товаров\n"
            "• 👥 Группы - сообщества по интересам\n\n"
            "Выберите раздел для начала работы:"
        )
        await update.message.reply_text(response, reply_markup=main_menu_keyboard(user_id))

async def register(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_registered(user_id):
        await update.message.reply_text('ℹ️ Вы уже зарегистрированы.', reply_markup=main_menu_keyboard(user_id))
        return
    
    nickname = update.message.text.strip()
    if not nickname:
        await update.message.reply_text('⚠️ Никнейм не может быть пустым.')
        return
    
    if get_user_by_nickname(nickname):
        await update.message.reply_text('⚠️ Этот никнейм уже занят.')
    else:
        if register_user(user_id, nickname):
            add_currency(user_id, 50)
            await update.message.reply_text(
                f'✅ Вы зарегистрированы как @{nickname}! Получите стартовый бонус: 50 монет.',
                reply_markup=main_menu_keyboard(user_id)
            )
        else:
            await update.message.reply_text('❌ Ошибка регистрации. Попробуйте другой никнейм.')

# Функции отображения
async def show_profile(message, context: CallbackContext):
    user_id = message.from_user.id
    user = get_user_by_id(user_id)
    if not user:
        await message.reply_text("Профиль не найден")
        return
    
    nickname = user.get('nickname', 'N/A')
    reg_date = user.get('reg_date', '').split()[0] if user.get('reg_date') else "N/A"
    last_seen = user.get('last_seen', '').split()[0] if user.get('last_seen') else "N/A"
    is_private = "🔒 Приватный" if user.get('is_private') else "🔓 Публичный"
    bio = user.get('bio', '') or "Описание отсутствует"
    balance = get_currency(user_id)
    
    cursor.execute('SELECT COUNT(*) FROM achievements WHERE user_id = ?', (user_id,))
    ach_count = cursor.fetchone()[0]
    
    response = (
        f"👤 Профиль @{nickname}\n\n"
        f"📅 Регистрация: {reg_date}\n"
        f"🕒 Последний вход: {last_seen}\n"
        f"👁️‍🗨️ Видимость: {is_private}\n"
        f"💬 О себе: {bio}\n"
        f"💰 Баланс: {balance} монет\n"
        f"🏆 Достижений: {ach_count}\n"
    )
    
    await message.reply_text(response, reply_markup=profile_menu_keyboard())

async def show_feed(message, context: CallbackContext):
    user_id = message.from_user.id
    offset = context.user_data.get('feed_offset', 0)
    filter_type = context.user_data.get('feed_filter', 'all')
    media_filter = context.user_data.get('feed_media_filter', None)
    
    try:
        # Получение постов с учетом фильтра
        if filter_type == 'popular':
            posts = get_popular_posts(user_id, limit=5, offset=offset)
        elif filter_type == 'friends':
            cursor.execute('''
            SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type
            FROM posts p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id IN (
                SELECT friend_id 
                FROM friends 
                WHERE user_id = ? AND status = 'accepted'
            )
            AND NOT EXISTS (
                SELECT 1 
                FROM blocks 
                WHERE (blocker_id = ? AND blocked_id = p.user_id)
                OR (blocker_id = p.user_id AND blocked_id = ?)
            )
            ORDER BY p.post_date DESC
            LIMIT 5 OFFSET ?
            ''', (user_id, user_id, user_id, offset))
            posts = cursor.fetchall()
        elif filter_type == 'groups':
            cursor.execute('''
            SELECT p.post_id, p.content, p.post_date, u.nickname, p.media_id, p.media_type
            FROM posts p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.group_id IN (
                SELECT group_id 
                FROM group_members 
                WHERE user_id = ?
            )
            AND NOT EXISTS (
                SELECT 1 
                FROM blocks 
                WHERE (blocker_id = ? AND blocked_id = p.user_id)
                OR (blocker_id = p.user_id AND blocked_id = ?)
            )
            ORDER BY p.post_date DESC
            LIMIT 5 OFFSET ?
            ''', (user_id, user_id, user_id, offset))
            posts = cursor.fetchall()
        elif filter_type == 'smart':
            posts = get_smart_feed(user_id, limit=5, offset=offset)
        else:
            posts = get_feed_posts(user_id, limit=5, offset=offset)
        
        # Применение медиа-фильтра
        if media_filter:
            if media_filter == 'photos':
                posts = [p for p in posts if p[5] == 'photo']
            elif media_filter == 'videos':
                posts = [p for p in posts if p[5] == 'video']
        
        # Получение рекламы (каждые 5 постов)
        ads = []
        if offset % 5 == 0 and filter_type != 'smart':
            ads = get_ads(limit=1, offset=offset//5)
        
        # Обработка пустой ленты
        if not posts and not ads:
            response = (
                "📭 Ваша лента пуста.\n\n"
                "Подпишитесь на других пользователей или группы, чтобы видеть их посты здесь.\n"
                "Или создайте свой первый пост, нажав кнопку ниже!"
            )
            await message.reply_text(
                response, 
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Создать первый пост", callback_data='create_post')]
                ])
            )
            return
        
        # Отображение постов и рекламы
        for i, post in enumerate(posts):
            post_id, content, post_date, nickname, media_id, media_type = post
            date_str = post_date.split()[0] if post_date else "N/A"
            response = f"👤 <b>@{nickname}</b> ({date_str})\n{content}\nID: {post_id}\n"
            
            try:
                # Отправка медиаконтента
                if media_type and media_id:
                    if media_type == 'photo':
                        await message.reply_photo(
                            photo=media_id, 
                            caption=response, 
                            reply_markup=post_keyboard(post_id),
                            parse_mode='HTML'
                        )
                    elif media_type == 'video':
                        await message.reply_video(
                            video=media_id, 
                            caption=response, 
                            reply_markup=post_keyboard(post_id),
                            parse_mode='HTML'
                        )
                    elif media_type == 'document':
                        await message.reply_document(
                            document=media_id, 
                            caption=response, 
                            reply_markup=post_keyboard(post_id),
                            parse_mode='HTML'
                        )
                    elif media_type == 'sticker':
                        await message.reply_sticker(sticker=media_id)
                        await message.reply_text(
                            response, 
                            reply_markup=post_keyboard(post_id),
                            parse_mode='HTML'
                        )
                else:
                    await message.reply_text(
                        response, 
                        reply_markup=post_keyboard(post_id),
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Ошибка отображения поста: {e}")
                await message.reply_text(
                    f"👤 @{nickname} ({date_str})\n{content}", 
                    reply_markup=post_keyboard(post_id)
                )
            
            # Вставка рекламы после 2-го поста
            if ads and i == 2:
                ad = ads[0]
                ad_id, ad_content, ad_date, ad_nickname, ad_media_id, ad_media_type = ad
                ad_response = f"📢 <b>Реклама от @{ad_nickname}</b>\n{ad_content}\nID: {ad_id}\n"
                
                try:
                    if ad_media_type and ad_media_id:
                        if ad_media_type == 'photo':
                            await message.reply_photo(
                                photo=ad_media_id, 
                                caption=ad_response, 
                                parse_mode='HTML'
                            )
                        elif ad_media_type == 'video':
                            await message.reply_video(
                                video=ad_media_id, 
                                caption=ad_response, 
                                parse_mode='HTML'
                            )
                        elif ad_media_type == 'document':
                            await message.reply_document(
                                document=ad_media_id, 
                                caption=ad_response, 
                                parse_mode='HTML'
                            )
                    else:
                        await message.reply_text(ad_response, parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Ошибка отображения рекламы: {e}")
        
        # Фиксация смещения и вывод меню
        context.user_data['feed_offset'] = offset
        await message.reply_text(
            f"📰 Лента ({filter_type}):", 
            reply_markup=feed_menu_keyboard(offset)
        )
        
    except Exception as e:
        logger.error(f"Ошибка показа ленты: {e}")
        await message.reply_text("❌ Ошибка загрузки ленты. Попробуйте позже.")

async def show_trends(message, context: CallbackContext):
    trends = get_trending_hashtags(10)
    if not trends:
        await message.reply_text("Популярные хештеги не найдены.")
        return
    
    response = "🔥 Топ популярных хештегов за последние 24 часа:\n\n"
    for i, trend in enumerate(trends):
        hashtag, count = trend
        response += f"{i+1}. #{hashtag} - {count} постов\n"
    
    await message.reply_text(response)

async def show_messages(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT m.message_id, u.nickname, m.content, m.timestamp
    FROM messages m
    JOIN users u ON m.sender_id = u.user_id
    WHERE m.receiver_id = ?
    ORDER BY m.timestamp DESC
    LIMIT 5
    ''', (user_id,))
    messages = cursor.fetchall()
    
    if not messages:
        await message.reply_text("У вас нет сообщений.", reply_markup=messages_menu_keyboard())
        return
    
    response = "💬 Последние входящие сообщения:\n\n"
    for msg in messages:
        msg_id, nickname, content, timestamp = msg
        preview = content[:50] + "..." if len(content) > 50 else content
        response += f"👤 От @{nickname} ({timestamp.split()[0]}):\n{preview}\n[ID: {msg_id}]\n\n"
    
    await message.reply_text(response, reply_markup=messages_menu_keyboard())

async def show_sent_messages(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT m.message_id, u.nickname, m.content, m.timestamp
    FROM messages m
    JOIN users u ON m.receiver_id = u.user_id
    WHERE m.sender_id = ?
    ORDER BY m.timestamp DESC
    LIMIT 5
    ''', (user_id,))
    messages = cursor.fetchall()
    
    if not messages:
        await message.reply_text("У вас нет отправленных сообщений.", reply_markup=messages_menu_keyboard())
        return
    
    response = "📤 Отправленные сообщения:\n\n"
    for msg in messages:
        msg_id, nickname, content, timestamp = msg
        preview = content[:50] + "..." if len(content) > 50 else content
        response += f"👤 К @{nickname} ({timestamp.split()[0]}):\n{preview}\n[ID: {msg_id}]\n\n"
    
    await message.reply_text(response, reply_markup=messages_menu_keyboard())

async def show_contacts(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT u.nickname 
    FROM friends f
    JOIN users u ON f.friend_id = u.user_id
    WHERE f.user_id = ? AND f.status = 'accepted'
    ''', (user_id,))
    friends = cursor.fetchall()
    
    if not friends:
        await message.reply_text("У вас нет друзей для отправки сообщений.", reply_markup=messages_menu_keyboard())
        return
    
    response = "👥 Ваши контакты:\n\n"
    for friend in friends:
        response += f"• @{friend[0]}\n"
    
    await message.reply_text(response, reply_markup=messages_menu_keyboard())

async def show_groups(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT g.group_id, g.name, g.description 
    FROM groups g
    JOIN group_members gm ON g.group_id = gm.group_id
    WHERE gm.user_id = ?
    ''', (user_id,))
    groups = cursor.fetchall()
    
    if not groups:
        await message.reply_text("Вы не состоите ни в одной группе.", reply_markup=groups_menu_keyboard())
        return
    
    response = "👥 Ваши группы:\n\n"
    for group in groups:
        group_id, name, description = group
        response += f"🔷 {name} (ID: {group_id})\nОписание: {description}\n\n"
    
    await message.reply_text(response, reply_markup=groups_menu_keyboard())

async def show_search(message, context: CallbackContext):
    await message.reply_text(
        "🔍 Выберите тип поиска:",
        reply_markup=search_menu_keyboard()
    )

async def show_economy(message, context: CallbackContext):
    user_id = message.from_user.id
    balance = get_currency(user_id)
    await message.reply_text(f"💰 Ваш баланс: {balance} монет", reply_markup=economy_menu_keyboard())

async def show_notifications(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT notification_id, content, notification_date 
    FROM notifications 
    WHERE user_id = ? AND is_read = 0
    ORDER BY notification_date DESC
    LIMIT 10
    ''', (user_id,))
    notifs = cursor.fetchall()
    
    if not notifs:
        await message.reply_text("У вас нет непрочитанных уведомлений.", reply_markup=main_menu_keyboard(user_id))
        return
    
    for notif in notifs:
        n_id, content, date = notif
        keyboard = notification_keyboard(n_id)
        date_str = date.split()[0] if date else ""
        await message.reply_text(
            f"📌 {content}\nДата: {date_str}",
            reply_markup=keyboard
        )

async def show_settings(message, context: CallbackContext):
    await message.reply_text(
        "⚙️ Настройки профиля:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Изменить никнейм", callback_data='change_nickname'),
             InlineKeyboardButton("📝 Изменить описание", callback_data='change_bio')],
            [InlineKeyboardButton("🔒 Приватность профиля", callback_data='toggle_privacy')],
            [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data='notification_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='profile_back')]
        ])
    )

async def show_notification_settings(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('SELECT * FROM notification_settings WHERE user_id = ?', (user_id,))
    settings = cursor.fetchone()
    if not settings:
        # Создаем настройки по умолчанию
        cursor.execute('INSERT INTO notification_settings (user_id) VALUES (?)', (user_id,))
        conn.commit()
        settings = (user_id, 1, 1, 1, 1)
    
    response = (
        f"🔔 Настройки уведомлений:\n"
        f"Лайки: {'✅' if settings[1] else '❌'}\n"
        f"Комментарии: {'✅' if settings[2] else '❌'}\n"
        f"Упоминания: {'✅' if settings[3] else '❌'}\n"
        f"Запросы дружбы: {'✅' if settings[4] else '❌'}\n"
    )
    
    await message.reply_text(response, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Лайки", callback_data='toggle_notify_likes')],
        [InlineKeyboardButton("🔄 Комментарии", callback_data='toggle_notify_comments')],
        [InlineKeyboardButton("🔄 Упоминания", callback_data='toggle_notify_mentions')],
        [InlineKeyboardButton("🔄 Запросы дружбы", callback_data='toggle_notify_friend_requests')],
        [InlineKeyboardButton("🔙 Назад", callback_data='profile_back')]
    ]))

async def show_friends(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT u.user_id, u.nickname 
    FROM friends f
    JOIN users u ON f.friend_id = u.user_id
    WHERE f.user_id = ? AND f.status = 'accepted'
    ''', (user_id,))
    friends = cursor.fetchall()
    
    cursor.execute('''
    SELECT u.user_id, u.nickname 
    FROM friends f
    JOIN users u ON f.user_id = u.user_id
    WHERE f.friend_id = ? AND f.status = 'pending'
    ''', (user_id,))
    requests = cursor.fetchall()
    
    response = "👥 Ваши друзья:\n"
    for friend in friends:
        response += f"• @{friend[1]}\n"
    
    response += "\n📨 Входящие запросы:\n"
    keyboard = []
    for req in requests:
        response += f"• @{req[1]}\n"
        keyboard.append([
            InlineKeyboardButton(f"✅ Принять {req[1]}", callback_data=f'accept_friend_{req[0]}'),
            InlineKeyboardButton(f"❌ Отклонить {req[1]}", callback_data=f'reject_friend_{req[0]}')
        ])
    
    await message.reply_text(
        response, 
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )

async def show_stats(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('SELECT COUNT(*) FROM posts WHERE user_id = ?', (user_id,))
    post_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM likes WHERE post_id IN (SELECT post_id FROM posts WHERE user_id = ?)', (user_id,))
    likes_received = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comments WHERE post_id IN (SELECT post_id FROM posts WHERE user_id = ?)', (user_id,))
    comments_received = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM friends WHERE user_id = ? AND status="accepted"', (user_id,))
    friend_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM groups WHERE creator_id = ?', (user_id,))
    group_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM achievements WHERE user_id = ?', (user_id,))
    ach_count = cursor.fetchone()[0]
    
    balance = get_currency(user_id)
    
    # Анализ активности за неделю
    cursor.execute('''
    SELECT strftime('%Y-%m-%d', post_date) AS day, COUNT(*) 
    FROM posts 
    WHERE user_id = ? AND post_date > datetime('now', '-7 days')
    GROUP BY day
    ORDER BY day DESC
    ''', (user_id,))
    weekly_activity = cursor.fetchall()
    
    response = (
        f"📊 Ваша статистика:\n\n"
        f"📝 Постов: {post_count}\n"
        f"❤️ Лайков получено: {likes_received}\n"
        f"💬 Комментариев получено: {comments_received}\n"
        f"👥 Друзей: {friend_count}\n"
        f"👥 Групп создано: {group_count}\n"
        f"🏆 Достижений: {ach_count}\n"
        f"💰 Монет: {balance}\n\n"
        f"📈 Активность за неделю:\n"
    )
    
    for day, count in weekly_activity:
        response += f"{day}: {count} постов\n"
    
    await message.reply_text(response)

async def show_achievements(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('SELECT type, description, earned_at FROM achievements WHERE user_id = ?', (user_id,))
    achievements = cursor.fetchall()
    
    if not achievements:
        await message.reply_text("🏆 У вас пока нет достижений.")
        return
    
    response = "🏆 Ваши достижения:\n\n"
    for ach in achievements:
        response += f"• {ach[1]} ({ach[2].split()[0]})\n"
    
    await message.reply_text(response)

async def show_blocked(message, context: CallbackContext):
    user_id = message.from_user.id
    cursor.execute('''
    SELECT u.nickname 
    FROM blocks b
    JOIN users u ON b.blocked_id = u.user_id
    WHERE blocker_id = ?
    ''', (user_id,))
    blocked_users = cursor.fetchall()
    
    if not blocked_users:
        await message.reply_text("🚫 У вас нет заблокированных пользователей")
        return
    
    response = "🚫 Заблокированные пользователи:\n"
    for user in blocked_users:
        response += f"• @{user[0]}\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data='profile_back')]
    ])
    await message.reply_text(response, reply_markup=keyboard)

async def show_bookmarks(message, context: CallbackContext):
    user_id = message.from_user.id
    offset = context.user_data.get('bookmark_offset', 0)
    bookmarks = get_bookmarks(user_id, limit=5, offset=offset)
    if not bookmarks:
        await message.reply_text("📑 У вас нет сохраненных постов.", reply_markup=main_menu_keyboard(user_id))
        return
    for post in bookmarks:
        post_id, content, post_date, nickname, media_id, media_type = post
        response = f"👤 @{nickname} ({post_date.split()[0]})\n{content}\nID поста: {post_id}\n"
        post_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍 Лайк", callback_data=f'like_{post_id}'),
                InlineKeyboardButton("💬 Комментировать", callback_data=f'comment_{post_id}'),
                InlineKeyboardButton("🔄 Репост", callback_data=f'repost_{post_id}'),
                InlineKeyboardButton("🗑️ Удалить из закладок", callback_data=f'remove_bookmark_{post_id}')
            ],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_post_{post_id}')]
        ])
        if media_type and media_id:
            if media_type == 'photo':
                await message.reply_photo(photo=media_id, caption=response, reply_markup=post_keyboard)
            elif media_type == 'video':
                await message.reply_video(video=media_id, caption=response, reply_markup=post_keyboard)
            elif media_type == 'document':
                await message.reply_document(document=media_id, caption=response, reply_markup=post_keyboard)
            elif media_type == 'sticker':
                await message.reply_sticker(sticker=media_id)
                await message.reply_text(response, reply_markup=post_keyboard)
        else:
            await message.reply_text(response, reply_markup=post_keyboard)
    context.user_data['bookmark_offset'] = offset
    
    # Навигация для закладок
    keyboard = []
    if offset > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'bookmark_prev_{offset-5}'))
    keyboard.append(InlineKeyboardButton("➡️ Далее", callback_data=f'bookmark_next_{offset+5}'))
    
    reply_markup = InlineKeyboardMarkup([keyboard])
    await message.reply_text("📑 Ваши закладки:", reply_markup=reply_markup)

async def show_marketplace(message, context: CallbackContext):
    user_id = message.from_user.id
    offset = context.user_data.get('market_offset', 0)
    items = get_market_items(limit=5, offset=offset)
    if not items:
        response = (
            "🛒 Маркет пуст.\n\n"
            "Будьте первым, кто разместит товар!\n"
            "Чтобы продать товар:\n"
            "1. Отправьте фото товара\n"
            "2. Используйте команду /sell <название> <цена> <описание>\n"
            "3. Пример: /sell Крутые часы 150 Часы со стразами, новое состояние"
        )
        await message.reply_text(response, reply_markup=market_menu_keyboard())
        return
    for item in items:
        item_id, title, description, price, created_at, nickname, media_id, media_type = item
        response = f"🛍️ {title} от @{nickname}\nЦена: {price} монет\nОписание: {description}\nID: {item_id}\nДата: {created_at.split()[0]}\n"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Купить", callback_data=f'buy_item_{item_id}')],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f'report_item_{item_id}')]
        ])
        if media_type and media_id:
            if media_type == 'photo':
                await message.reply_photo(photo=media_id, caption=response, reply_markup=keyboard)
            elif media_type == 'video':
                await message.reply_video(video=media_id, caption=response, reply_markup=keyboard)
            elif media_type == 'document':
                await message.reply_document(document=media_id, caption=response, reply_markup=keyboard)
        else:
            await message.reply_text(response, reply_markup=keyboard)
    context.user_data['market_offset'] = offset
    
    # Навигация для маркета
    keyboard = []
    if offset > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'market_prev_{offset-5}'))
    keyboard.append(InlineKeyboardButton("➡️ Далее", callback_data=f'market_next_{offset+5}'))
    
    reply_markup = InlineKeyboardMarkup([keyboard])
    await message.reply_text("🛒 Маркет:", reply_markup=reply_markup)

async def show_admin_panel(message, context: CallbackContext):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply_text("❌ Доступ запрещен")
        return
    await message.reply_text(
        "🛠️ Панель администратора:",
        reply_markup=admin_menu_keyboard()
    )

async def show_stories(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    stories = get_stories(user_id)
    if not stories:
        await update.message.reply_text("📸 Нет доступных историй.", reply_markup=main_menu_keyboard(user_id))
        return
    for story in stories:
        story_id, content, created_at, nickname, media_id, media_type = story
        response = f"📸 История от @{nickname} ({created_at.split()[0]})\n{content or ''}\nID: {story_id}"
        if media_type and media_id:
            if media_type == 'photo':
                await update.message.reply_photo(photo=media_id, caption=response)
            elif media_type == 'video':
                await update.message.reply_video(video=media_id, caption=response)
        else:
            await update.message.reply_text(response)

# Обработчики сообщений
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message
    text = message.text if message.text else ""
    
    # Обработка регистрации
    if not is_registered(user_id):
        await register(update, context)
        return
    
    # Обработка редактирования профиля
    if 'editing' in context.user_data:
        field = context.user_data['editing']
        del context.user_data['editing']
        
        if field == 'nickname':
            if not text.strip():
                await message.reply_text("❌ Никнейм не может быть пустым.")
                return
            if get_user_by_nickname(text.strip()):
                await message.reply_text("❌ Этот никнейм уже занят.")
                return
            if update_user_profile(user_id, nickname=text.strip()):
                await message.reply_text("✅ Никнейм успешно изменен!")
            else:
                await message.reply_text("❌ Ошибка при изменении никнейма.")
        
        elif field == 'bio':
            if update_user_profile(user_id, bio=text):
                await message.reply_text("✅ Описание профиля успешно обновлено!")
            else:
                await message.reply_text("❌ Ошибка при обновлении описания.")
        return
    
    # Обработка комментариев
    if 'commenting_post' in context.user_data:
        post_id = context.user_data['commenting_post']
        del context.user_data['commenting_post']
        if comment_post(user_id, post_id, text):
            await message.reply_text("💬 Комментарий добавлен!")
        else:
            await message.reply_text("❌ Не удалось добавить комментарий")
        return
    
    # Обработка жалоб
    if 'reporting_post' in context.user_data:
        post_id = context.user_data['reporting_post']
        del context.user_data['reporting_post']
        if create_report(user_id, post_id, 'post', text):
            await message.reply_text("⚠️ Жалоба на пост отправлена.", reply_markup=main_menu_keyboard(user_id))
        else:
            await message.reply_text("❌ Не удалось отправить жалобу.")
        return
    
    if 'reporting_item' in context.user_data:
        item_id = context.user_data['reporting_item']
        del context.user_data['reporting_item']
        if create_report(user_id, item_id, 'item', text):
            await message.reply_text("⚠️ Жалоба на товар отправлена.", reply_markup=main_menu_keyboard(user_id))
        else:
            await message.reply_text("❌ Не удалось отправить жалобу.")
        return
    
    if 'reporting_ad' in context.user_data:
        ad_id = context.user_data['reporting_ad']
        del context.user_data['reporting_ad']
        if create_report(user_id, ad_id, 'ad', text):
            await message.reply_text("⚠️ Жалоба на рекламу отправлена.", reply_markup=main_menu_keyboard(user_id))
        else:
            await message.reply_text("❌ Не удалось отправить жалобу.")
        return
    
    # Обработка медиаконтента для постов
    if message.photo and not context.user_data.get('pending_market_media') and not context.user_data.get('pending_ad_media'):
        media_id = message.photo[-1].file_id
        context.user_data['pending_media'] = {'type': 'photo', 'id': media_id}
        await message.reply_text('📸 Фото получено. Теперь введите описание поста:')
        return
    elif message.video and not context.user_data.get('pending_market_media') and not context.user_data.get('pending_ad_media'):
        context.user_data['pending_media'] = {'type': 'video', 'id': message.video.file_id}
        await message.reply_text('🎥 Видео получено. Теперь введите описание поста:')
        return
    elif message.document and not context.user_data.get('pending_market_media') and not context.user_data.get('pending_ad_media'):
        context.user_data['pending_media'] = {'type': 'document', 'id': message.document.file_id}
        await message.reply_text('📄 Документ получен. Теперь введите описание поста:')
        return
    elif message.sticker and not context.user_data.get('pending_market_media') and not context.user_data.get('pending_ad_media'):
        context.user_data['pending_media'] = {'type': 'sticker', 'id': message.sticker.file_id}
        await message.reply_text('🧩 Стикер получен. Теперь введите описание поста:')
        return
    
    # Обработка медиаконтента для историй
    if (message.photo or message.video) and not any([
        context.user_data.get('pending_media'),
        context.user_data.get('pending_market_media'),
        context.user_data.get('pending_ad_media')
    ]):
        media_type = 'photo' if message.photo else 'video'
        media_id = message.photo[-1].file_id if media_type == 'photo' else message.video.file_id
        
        story_id = create_story(user_id, media_id=media_id, media_type=media_type)
        if story_id:
            await message.reply_text(f"📸 История опубликована! ID: {story_id}")
        else:
            await message.reply_text("❌ Ошибка публикации истории")
        return
    
    # Обработка медиаконтента для маркета
    if message.photo and not context.user_data.get('pending_media') and not context.user_data.get('pending_ad_media'):
        media_id = message.photo[-1].file_id
        context.user_data['pending_market_media'] = {'type': 'photo', 'id': media_id}
        await message.reply_text('📸 Фото для товара получено. Введите: /sell <название> <цена> <описание>')
        return
    elif message.video and not context.user_data.get('pending_media') and not context.user_data.get('pending_ad_media'):
        context.user_data['pending_market_media'] = {'type': 'video', 'id': message.video.file_id}
        await message.reply_text('🎥 Видео для товара получено. Введите: /sell <название> <цена> <описание>')
        return
    elif message.document and not context.user_data.get('pending_media') and not context.user_data.get('pending_ad_media'):
        context.user_data['pending_market_media'] = {'type': 'document', 'id': message.document.file_id}
        await message.reply_text('📄 Документ для товара получен. Введите: /sell <название> <цена> <описание>')
        return
    
    # Обработка медиаконтента для рекламы
    if message.photo and not context.user_data.get('pending_media') and not context.user_data.get('pending_market_media'):
        media_id = message.photo[-1].file_id
        context.user_data['pending_ad_media'] = {'type': 'photo', 'id': media_id}
        await message.reply_text('📸 Фото для рекламы получено. Введите: /create_ad <цена> <текст>')
        return
    elif message.video and not context.user_data.get('pending_media') and not context.user_data.get('pending_market_media'):
        context.user_data['pending_ad_media'] = {'type': 'video', 'id': message.video.file_id}
        await message.reply_text('🎥 Видео для рекламы получено. Введите: /create_ad <цена> <текст>')
        return
    elif message.document and not context.user_data.get('pending_media') and not context.user_data.get('pending_market_media'):
        context.user_data['pending_ad_media'] = {'type': 'document', 'id': message.document.file_id}
        await message.reply_text('📄 Документ для рекламы получен. Введите: /create_ad <цена> <текст>')
        return
    
    # Обработка текстовых команд главного меню
    if text == '👤 Профиль':
        await show_profile(message, context)
    elif text == '📰 Лента':
        context.user_data['feed_offset'] = 0
        context.user_data['feed_filter'] = 'all'
        await show_feed(message, context)
    elif text == 'ℹ️ Помощь':  # Обработка новой кнопки
        await show_help(message, context)
    elif text == '🔥 Тренды':
        await show_trends(message, context)
    elif text == '📑 Закладки':
        await show_bookmarks(message, context)
    elif text == '💬 Сообщения':
        await show_messages(message, context)
    elif text == '👥 Группы':
        await show_groups(message, context)
    elif text == '🛒 Маркет':
        await show_marketplace(message, context)
    elif text == '🔔 Уведомления':
        await show_notifications(message, context)
    elif text == '💰 Экономика':
        await show_economy(message, context)
    elif text == '📸 Истории':
        await show_stories(update, context)
    elif text == '🔍 Поиск':
        await show_search(message, context)
    elif text == '⚙️ Настройки':
        await show_settings(message, context)
    elif text == '🛠️ Админ-панель':
        await show_admin_panel(message, context)
    elif text == '🏠 Главное меню':
        await message.reply_text('🏠 Главное меню:', reply_markup=main_menu_keyboard(user_id))
    elif text == '❌ Отмена':
        if 'pending_media' in context.user_data:
            del context.user_data['pending_media']
        if 'pending_market_media' in context.user_data:
            del context.user_data['pending_market_media']
        if 'pending_ad_media' in context.user_data:
            del context.user_data['pending_ad_media']
        await message.reply_text('❌ Действие отменено', reply_markup=main_menu_keyboard(user_id))
    
    # Обработка подменю сообщений
    elif text == '📥 Входящие сообщения':
        await show_messages(message, context)
    elif text == '📤 Отправленные сообщения':
        await show_sent_messages(message, context)
    elif text == '✉️ Новое сообщение':
        await message.reply_text("Введите никнейм получателя и сообщение: /msg <никнейм> <текст>", 
                                reply_markup=messages_menu_keyboard())
    elif text == '👥 Контакты':
        await show_contacts(message, context)
    
    # Обработка подменю групп
    elif text == '👥 Мои группы':
        await show_groups(message, context)
    elif text == '📝 Создать группу':
        await message.reply_text("Введите: /create_group <название> <описание>", 
                                reply_markup=groups_menu_keyboard())
    elif text == '🎥 Начать трансляцию':
        await message.reply_text("🎥 Запуск трансляции:\n\n"
                               "Использование: /start_live <ID_группы> <Название>\n\n"
                               "Как получить ID группы:\n"
                               "1. Перейдите в раздел '👥 Группы'\n"
                               "2. Выберите '👥 Мои группы'\n"
                               "3. ID группы указан в скобках\n\n"
                               "Пример: /start_live 123 Моя первая трансляция")
    elif text == '🔍 Найти группу':
        await message.reply_text("Введите: /search_groups <ключевое слово>", 
                                reply_markup=groups_menu_keyboard())
    
    # Обработка подменю экономики
    elif text == '💰 Мой баланс':
        await show_economy(message, context)
    elif text == '🎁 Получить бонус':
        if daily_bonus(user_id):
            await message.reply_text('🎉 Вы получили 10 монет!', reply_markup=economy_menu_keyboard())
        else:
            await message.reply_text('⚠️ Вы уже получали бонус сегодня. Приходите завтра!', 
                                   reply_markup=economy_menu_keyboard())
    elif text == '➡️ Перевод монет':
        await message.reply_text("Введите: /transfer <никнейм> <сумма>", 
                                reply_markup=economy_menu_keyboard())
    
    # Обработка подменю поиска
    elif text == '👤 Поиск пользователей':
        await message.reply_text("🔍 Введите имя пользователя для поиска:")
        context.user_data['searching_users'] = True
    elif text == '#️⃣ Поиск по хештегам' or text == '📝 Поиск постов':
        await message.reply_text("🔍 Введите хештег для поиска (без #):")
        context.user_data['searching_hashtag'] = True
    elif text == '👥 Поиск групп':
        await message.reply_text("🔍 Введите название группы для поиска:")
        context.user_data['searching_groups'] = True
    elif text == '📜 Поиск по контенту':
        await message.reply_text("🔍 Введите ключевое слово для поиска:")
        context.user_data['searching_content'] = True
    
    # Обработка подменю маркета
    elif text == '🛒 Просмотреть маркет':
        await show_marketplace(message, context)
    elif text == '📦 Мои товары':
        await show_my_marketplace(message, context)
    elif text == '💰 Продать товар':
        await message.reply_text("Отправьте фото/видео товара и введите: /sell <название> <цена> <описание>", 
                               reply_markup=market_menu_keyboard())
    
    # Обработка создания поста
    elif text == '📝 Создать пост':
        await message.reply_text(
            "📝 Создание нового поста:\n\n"
            "• Просто напишите текст поста\n"
            "• Или отправьте фото/видео с описанием\n"
            "• Используйте #хештеги для лучшего охвата\n\n"
            "Отправьте содержимое поста сейчас:"
        )
    
    # Обработка историй
    elif text == '📸 Истории':
        await message.reply_text(
            "📸 Создание историй:\n\n"
            "• Отправьте фото или видео\n"
            "• Истории исчезнут через 24 часа\n"
            "• Ваши друзья увидят их в этом разделе\n\n"
            "Отправьте фото или видео сейчас, чтобы создать историю:"
        )
        await show_stories(update, context)
    
    # Обработка рекламы
    elif text == '📢 Создать рекламу':
        await message.reply_text(
            "📢 Создание рекламы:\n\n"
            "1. Отправьте медиа (фото/видео) для рекламы (необязательно)\n"
            "2. Используйте команду: /create_ad <бюджет> <текст>\n"
            "3. Пример: /create_ad 50 Присоединяйтесь к нашей группе!\n"
            "4. Реклама будет проверена модератором\n\n"
            "Вы можете отправить медиа сейчас или сразу использовать команду"
        )
    
    # Обработка поисковых запросов
    elif context.user_data.get('searching_users'):
        del context.user_data['searching_users']
        results = search_users(text)
        if not results:
            await message.reply_text("Пользователи не найдены.")
            return
        response = "🔍 Результаты поиска пользователей:\n\n"
        for user_id, nickname in results:
            response += f"• @{nickname} (ID: {user_id})\n"
        await message.reply_text(response)
    elif context.user_data.get('searching_hashtag'):
        del context.user_data['searching_hashtag']
        results = search_posts_by_hashtag(text)
        if not results:
            await message.reply_text("Посты с таким хештегом не найдены.")
            return
        response = f"🔍 Посты с хештегом #{text}:\n\n"
        for post_id, content, nickname in results:
            preview = content[:100] + "..." if len(content) > 100 else content
            response += f"👤 @{nickname}\n{preview}\nID поста: {post_id}\n\n"
        await message.reply_text(response)
    elif context.user_data.get('searching_groups'):
        del context.user_data['searching_groups']
        results = search_groups(text)
        if not results:
            await message.reply_text("Группы не найдены.")
            return
        response = "🔍 Результаты поиска групп:\n\n"
        for group_id, name, description in results:
            response += f"🔷 {name} (ID: {group_id})\nОписание: {description}\n\n"
        await message.reply_text(response)
    elif context.user_data.get('searching_content'):
        del context.user_data['searching_content']
        results = search_content(text, user_id)
        if not results:
            await message.reply_text("🔍 Ничего не найдено.")
            return
        response = "🔍 Результаты поиска:\n\n"
        for post in results:
            post_id, content, post_date, nickname, media_id, media_type = post
            preview = content[:100] + "..." if len(content) > 100 else content
            response += f"👤 @{nickname} ({post_date.split()[0]})\n{preview}\nID поста: {post_id}\n\n"
        await message.reply_text(response)
    
    # Обработка постов с медиа
    elif 'pending_media' in context.user_data:
        media = context.user_data['pending_media']
        post_id = create_post(user_id, text, media_type=media['type'], media_id=media['id'])
        del context.user_data['pending_media']
        if post_id:
            await message.reply_text('✅ Пост с медиа опубликован!')
        else:
            await message.reply_text('❌ Ошибка публикации поста')
    
    # Обработка обычных текстовых постов
    else:
        post_id = create_post(user_id, text)
        if post_id:
            await message.reply_text('✅ Текстовый пост опубликован!')
        else:
            await message.reply_text('❌ Ошибка публикации поста')

async def show_help(message, context: CallbackContext):
    help_text = (
        "🌟 <b>Полное руководство по SocialBot</b> 🌟\n\n"
        "📝 <b>Создание контента:</b>\n"
        "- Посты: текст, фото/видео с описанием\n"
        "- Истории: медиа, исчезающие через 24 часа\n"
        "- Трансляции: /start_live [ID группы] [Название]\n\n"  # Исправлено здесь
        "📰 <b>Лента новостей:</b>\n"
        "- Посты друзей, групп и популярный контент\n"
        "- Умная лента с рекомендациями\n"
        "- Фильтры по типу контента\n\n"
        "👥 <b>Социальные функции:</b>\n"
        "- Друзья: запросы, принятие/отклонение\n"
        "- Группы: создание, поиск, участие\n"
        "- Сообщения: личные чаты с друзьями\n\n"
        "🛒 <b>Маркетплейс:</b>\n"
        "- Покупка/продажа товаров\n"
        "- Ваши товары: управление объявлениями\n"
        "- Реклама: создание промо-постов\n\n"
        "💰 <b>Экономика:</b>\n"
        "- Баланс: виртуальные монеты\n"
        "- Бонусы: ежедневные награды\n"
        "- Переводы: отправка монет друзьям\n\n"
        "🏆 <b>Достижения:</b>\n"
        "- Награды за активность\n"
        "- Статистика ваших действий\n\n"
        "⚙️ <b>Настройки:</b>\n"
        "- Профиль: никнейм, описание\n"
        "- Приватность: публичный/закрытый аккаунт\n"
        "- Уведомления: управление оповещениями\n\n"
        "🛠️ <b>Администраторам:</b>\n"
        "- Модерация контента\n"
        "- Управление рекламой\n"
        "- Бан пользователей\n\n"
        "📌 Для начала работы выберите раздел в меню или используйте команды:\n"
        "/create_post - Создать пост\n"
        "/msg - Отправить сообщение\n"
        "/sell - Продать товар\n"
        "/transfer - Перевести монеты"
    )
    
    await message.reply_text(
        help_text, 
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(message.from_user.id)
    )

async def help_command(update: Update, context: CallbackContext):
    await show_help(update.message, context)

# Обработчики колбэков
async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == 'main_menu':
        await query.message.reply_text('🏠 Главное меню:', reply_markup=main_menu_keyboard(user_id))
    elif data == 'create_post':
        await query.message.reply_text(
            "📝 Создание нового поста:\n\n"
            "1. Вы можете просто отправить текст\n"
            "2. Или отправить медиа (фото/видео/документ) с подписью\n"
            "3. Используйте хештеги #пример для категоризации\n\n"
            "Отправьте содержимое поста сейчас:"
        )
    elif data == 'my_posts':
        await show_my_posts(query.message, context)
    elif data.startswith('my_posts_prev_'):
        offset = int(data.split('_')[3])
        context.user_data['my_posts_offset'] = offset
        await show_my_posts(query.message, context)
    elif data.startswith('my_posts_next_'):
        offset = int(data.split('_')[3])
        context.user_data['my_posts_offset'] = offset
        await show_my_posts(query.message, context)
    elif data.startswith('delete_my_post_'):
        post_id = int(data.split('_')[3])
        cursor.execute('DELETE FROM posts WHERE post_id = ? AND user_id = ?', (post_id, user_id))
        conn.commit()  # Не забываем сохранять изменения!
        if cursor.rowcount > 0:
            await query.answer("🗑️ Пост удален")
            await show_my_posts(query.message, context)
        else:
            await query.answer("❌ Не удалось удалить пост")
    elif data == 'feed_friends':
        context.user_data['feed_filter'] = 'friends'
        context.user_data['feed_offset'] = 0
        await show_feed(query.message, context)
    elif data == 'feed_groups':
        context.user_data['feed_filter'] = 'groups'
        context.user_data['feed_offset'] = 0
        await show_feed(query.message, context)
    elif data == 'feed_popular':
        context.user_data['feed_filter'] = 'popular'
        context.user_data['feed_offset'] = 0
        await show_feed(query.message, context)
    elif data == 'feed_smart':
        context.user_data['feed_filter'] = 'smart'
        context.user_data['feed_offset'] = 0
        await show_feed(query.message, context)
    elif data == 'filter_feed':
        await query.message.reply_text(
            "📂 Выберите тип контента для ленты:",
            reply_markup=filter_feed_keyboard()
        )
    elif data == 'feed_all':
        context.user_data['feed_media_filter'] = None
        await show_feed(query.message, context)
    elif data == 'feed_photos':
        context.user_data['feed_media_filter'] = 'photos'
        await show_feed(query.message, context)
    elif data == 'feed_videos':
        context.user_data['feed_media_filter'] = 'videos'
        await show_feed(query.message, context)
    elif data.startswith('feed_prev_'):
        offset = int(data.split('_')[2])
        context.user_data['feed_offset'] = offset
        await show_feed(query.message, context)
    elif data.startswith('feed_next_'):
        offset = int(data.split('_')[2])
        context.user_data['feed_offset'] = offset
        await show_feed(query.message, context)
    elif data.startswith('bookmark_prev_'):
        offset = int(data.split('_')[2])
        context.user_data['bookmark_offset'] = offset
        await show_bookmarks(query.message, context)
    elif data.startswith('bookmark_next_'):
        offset = int(data.split('_')[2])
        context.user_data['bookmark_offset'] = offset
        await show_bookmarks(query.message, context)
    elif data.startswith('market_prev_'):
        offset = int(data.split('_')[2])
        context.user_data['market_offset'] = offset
        await show_marketplace(query.message, context)
    elif data.startswith('market_next_'):
        offset = int(data.split('_')[2])
        context.user_data['market_offset'] = offset
        await show_marketplace(query.message, context)
    elif data.startswith('reaction_'):
        parts = data.split('_')
        post_id = int(parts[1])
        reaction = parts[2]
        if like_post(user_id, post_id, reaction):
            await query.answer(f"Реакция {reaction} добавлена!")
        else:
            await query.answer("❌ Не удалось добавить реакцию")
    elif data.startswith('comment_'):
        post_id = int(data.split('_')[1])
        context.user_data['commenting_post'] = post_id
        await query.message.reply_text("💬 Введите текст комментария:")
    elif data.startswith('repost_'):
        post_id = int(data.split('_')[1])
        new_post_id = repost(user_id, post_id)
        if new_post_id:
            await query.answer(f"✅ Пост репостнут! ID: {new_post_id}")
        else:
            await query.answer("❌ Ошибка репоста")
    elif data.startswith('bookmark_'):
        post_id = int(data.split('_')[1])
        if add_bookmark(user_id, post_id):
            await query.answer("📑 Пост добавлен в закладки!")
        else:
            await query.answer("❌ Не удалось добавить в закладки")
    elif data.startswith('remove_bookmark_'):
        post_id = int(data.split('_')[2])
        if remove_bookmark(user_id, post_id):
            await query.answer("🗑️ Пост удален из закладок")
        else:
            await query.answer("❌ Ошибка удаления из закладок")
    elif data.startswith('report_post_'):
        post_id = int(data.split('_')[2])
        context.user_data['reporting_post'] = post_id
        await query.message.reply_text("⚠️ Укажите причину жалобы на пост:")
    elif data.startswith('read_'):
        notification_id = data.split('_')[1]
        mark_notification_read(notification_id)
        await query.message.delete()
    elif data.startswith('delete_'):
        notification_id = data.split('_')[1]
        cursor.execute('DELETE FROM notifications WHERE notification_id = ?', (notification_id,))
        conn.commit()
        await query.message.delete()
    elif data == 'blocked_list':
        await show_blocked(query.message, context)
    elif data == 'stats':
        await show_stats(query.message, context)
    elif data == 'achievements':
        await show_achievements(query.message, context)
    elif data == 'friends_list':
        await show_friends(query.message, context)
    elif data.startswith('accept_friend_'):
        friend_id = int(data.split('_')[2])
        if respond_friend_request(user_id, friend_id, True):
            await query.edit_message_text("✅ Запрос дружбы принят")
        else:
            await query.edit_message_text("❌ Ошибка принятия запроса")
    elif data.startswith('reject_friend_'):
        friend_id = int(data.split('_')[2])
        if respond_friend_request(user_id, friend_id, False):
            await query.edit_message_text("✅ Запрос дружбы отклонен")
        else:
            await query.edit_message_text("❌ Ошибка отклонения запроса")
    elif data == 'change_nickname':
        context.user_data['editing'] = 'nickname'
        await query.message.reply_text("✏️ Введите новый никнейм:")
    elif data == 'change_bio':
        context.user_data['editing'] = 'bio'
        await query.message.reply_text("📝 Введите новое описание профиля:")
    elif data == 'notification_settings':
        await show_notification_settings(query.message, context)
    elif data.startswith('toggle_notify_'):
        setting = data.split('_')[2]
        cursor.execute(f'SELECT {setting} FROM notification_settings WHERE user_id = ?', (user_id,))
        current = cursor.fetchone()[0] or 1
        new_value = 1 - current
        cursor.execute(f'UPDATE notification_settings SET {setting} = ? WHERE user_id = ?', (new_value, user_id))
        conn.commit()
        await query.answer(f"{'✅ Включено' if new_value else '❌ Отключено'}")
        await show_notification_settings(query.message, context)
    elif data == 'toggle_privacy':
        user = get_user_by_id(user_id)
        if not user:
            await query.message.reply_text("❌ Профиль не найден")
            return
        new_privacy = not user.get('is_private', False)
        update_user_profile(user_id, is_private=new_privacy)
        status = "🔒 приватный" if new_privacy else "🔓 публичный"
        await query.message.reply_text(f"✅ Профиль теперь {status}")
    elif data == 'profile_back':
        await show_profile(query.message, context)
    elif data.startswith('buy_item_'):
        item_id = int(data.split('_')[2])
        result = buy_item(user_id, item_id)
        await query.answer(result)
    elif data.startswith('report_item_'):
        item_id = int(data.split('_')[2])
        context.user_data['reporting_item'] = item_id
        await query.message.reply_text("⚠️ Укажите причину жалобы на товар:")
    elif data.startswith('report_ad_'):
        ad_id = int(data.split('_')[2])
        context.user_data['reporting_ad'] = ad_id
        await query.message.reply_text("⚠️ Укажите причину жалобы на рекламу:")
    elif data == 'admin_panel':
        await show_admin_panel(query.message, context)
    elif data == 'admin_stats':
        await query.message.reply_text("📊 Статистика в разработке")
    elif data == 'admin_ban':
        await query.message.reply_text("Введите: /ban <никнейм> <причина>")
    elif data == 'admin_ads':
        await query.message.reply_text("Список рекламы для модерации в разработке")
    elif data == 'admin_content':
        await query.message.reply_text("Список контента для модерации в разработке")

# Новые функции для "Мои товары"
async def show_my_marketplace(message, context: CallbackContext):
    user_id = message.from_user.id
    offset = context.user_data.get('my_market_offset', 0)
    items = get_my_market_items(user_id, limit=5, offset=offset)
    
    if not items:
        response = (
            "📦 У вас нет товаров на продажу.\n\n"
            "Чтобы добавить товар:\n"
            "1. Отправьте фото товара\n"
            "2. Используйте команду /sell <название> <цена> <описание>\n"
            "3. Пример: /sell Крутые часы 150 Часы со стразами, новое состояние"
        )
        await message.reply_text(response, reply_markup=market_menu_keyboard())
        return
        
    for item in items:
        item_id, title, description, price, created_at, nickname, media_id, media_type = item
        response = f"📦 Ваш товар: {title}\nЦена: {price} монет\nОписание: {description}\nID: {item_id}\nДата: {created_at.split()[0]}\n"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Редактировать", callback_data=f'edit_item_{item_id}')],
            [InlineKeyboardButton("❌ Удалить", callback_data=f'delete_item_{item_id}')]
        ])
        if media_type and media_id:
            if media_type == 'photo':
                await message.reply_photo(photo=media_id, caption=response, reply_markup=keyboard)
            elif media_type == 'video':
                await message.reply_video(video=media_id, caption=response, reply_markup=keyboard)
            elif media_type == 'document':
                await message.reply_document(document=media_id, caption=response, reply_markup=keyboard)
        else:
            await message.reply_text(response, reply_markup=keyboard)
    
    # Навигация
    keyboard = []
    if offset > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f'my_market_prev_{offset-5}'))
    keyboard.append(InlineKeyboardButton("➡️ Далее", callback_data=f'my_market_next_{offset+5}'))
    
    reply_markup = InlineKeyboardMarkup([keyboard])
    context.user_data['my_market_offset'] = offset
    await message.reply_text("📦 Ваши товары:", reply_markup=reply_markup)

def get_my_market_items(user_id, limit=5, offset=0):
    cursor.execute('''
    SELECT m.item_id, m.title, m.description, m.price, m.created_at, u.nickname, m.media_id, m.media_type
    FROM marketplace m
    JOIN users u ON m.seller_id = u.user_id
    WHERE m.seller_id = ? AND m.status = 'active'
    ORDER BY m.created_at DESC
    LIMIT ? OFFSET ?
    ''', (user_id, limit, offset))
    return cursor.fetchall()

# Командные обработчики
async def block_user_cmd(update: Update, context: CallbackContext):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Использование: /block <никнейм> <причина>")
        return
    nickname = context.args[0]
    reason = ' '.join(context.args[1:])
    result = ban_user(update.effective_user.id, nickname, reason)
    await update.message.reply_text(result)

async def unblock_user_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Использование: /unblock <никнейм>")
        return
    nickname = ' '.join(context.args)
    if unblock_user(update.effective_user.id, nickname):
        await update.message.reply_text(f"✅ Пользователь @{nickname} разблокирован")
    else:
        await update.message.reply_text("❌ Не удалось разблокировать пользователя. Возможно, он не был заблокирован.")

async def send_message_cmd(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text('Использование: /msg <никнейм> <текст сообщения>')
        return
    receiver_nick = context.args[0]
    message = ' '.join(context.args[1:])
    if send_private_message(update.effective_user.id, receiver_nick, message):
        await update.message.reply_text(f'✉️ Сообщение отправлено @{receiver_nick}')
    else:
        await update.message.reply_text('⚠️ Не удалось отправить сообщение. Проверьте никнейм или настройки приватности.')

async def daily_bonus_cmd(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if daily_bonus(user_id):
        await update.message.reply_text('🎉 Вы получили 10 монет!')
    else:
        await update.message.reply_text('⚠️ Вы уже получали бонус сегодня. Приходите завтра!')

async def search_users_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Использование: /search_users <ключевое слово>")
        return
    keyword = ' '.join(context.args)
    results = search_users(keyword)
    if not results:
        await update.message.reply_text("Пользователи не найдены.")
        return
    response = "🔍 Результаты поиска пользователей:\n\n"
    for user_id, nickname in results:
        response += f"• @{nickname} (ID: {user_id})\n"
    await update.message.reply_text(response)

async def search_groups_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Использование: /search_groups <ключевое слово>")
        return
    keyword = ' '.join(context.args)
    results = search_groups(keyword)
    if not results:
        await update.message.reply_text("Группы не найдены.")
        return
    response = "🔍 Результаты поиска групп:\n\n"
    for group_id, name, description in results:
        response += f"🔷 {name} (ID: {group_id})\nОписание: {description}\n\n"
    await update.message.reply_text(response)

async def search_posts_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Использование: /search_posts <хештег>")
        return
    hashtag = context.args[0].lstrip('#')
    results = search_posts_by_hashtag(hashtag)
    if not results:
        await update.message.reply_text("Посты с таким хештегом не найдены.")
        return
    response = f"🔍 Посты с хештегом #{hashtag}:\n\n"
    for post_id, content, nickname in results:
        preview = content[:100] + "..." if len(content) > 100 else content
        response += f"👤 @{nickname}\n{preview}\nID поста: {post_id}\n\n"
    await update.message.reply_text(response)

async def create_group_cmd(update: Update, context: CallbackContext):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Использование: /create_group <название> <описание>")
        return
    group_name = context.args[0]
    description = ' '.join(context.args[1:])
    group_id = create_group(update.effective_user.id, group_name, description)
    if group_id:
        await update.message.reply_text(f"✅ Группа '{group_name}' создана! ID группы: {group_id}")
    else:
        await update.message.reply_text("⚠️ Не удалось создать группу.")

async def start_live_cmd(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text(
            "🎥 Запуск трансляции:\n\n"
            "Использование: /start_live <ID_группы> <Название>\n\n"
            "Как получить ID группы:\n"
            "1. Перейдите в раздел '👥 Группы'\n"
            "2. Выберите '👥 Мои группы'\n"
            "3. ID группы указан в скобках\n\n"
            "Пример: /start_live 123 Моя первая трансляция"
        )
        return
    try:
        group_id = int(context.args[0])
        title = ' '.join(context.args[1:])
        user_id = update.effective_user.id
        stream_id = start_live_stream(user_id, group_id, title)
        if stream_id:
            await update.message.reply_text(
                f"🎥 Трансляция начата! ID: {stream_id}\n"
                f"Для запуска используйте видеозвонок в группе."
            )
        else:
            await update.message.reply_text("❌ Не удалось начать трансляцию")
    except ValueError:
        await update.message.reply_text("⚠️ ID группы должен быть числом")

async def transfer_cmd(update: Update, context: CallbackContext):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Использование: /transfer <никнейм> <сумма>")
        return
    receiver_nick = context.args[0]
    amount = context.args[1]
    result = transfer_currency(update.effective_user.id, receiver_nick, amount)
    await update.message.reply_text(result)

async def sell_cmd(update: Update, context: CallbackContext):
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /sell <название> <цена> <описание>")
        return
    title = context.args[0]
    try:
        price = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Цена должна быть числом")
        return
    description = ' '.join(context.args[2:])
    user_id = update.effective_user.id
    media = context.user_data.get('pending_market_media', None)
    item_id = create_market_item(user_id, title, description, price, 
                                media['id'] if media else None, 
                                media['type'] if media else None)
    if media:
        del context.user_data['pending_market_media']
    if item_id:
        await update.message.reply_text(f"✅ Товар '{title}' выставлен на продажу! ID: {item_id}")
    else:
        await update.message.reply_text("❌ Ошибка при создании товара")

async def create_ad_cmd(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /create_ad <цена> <текст>")
        return
    try:
        price = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Цена должна быть числом")
        return
    content = ' '.join(context.args[1:])
    user_id = update.effective_user.id
    media = context.user_data.get('pending_ad_media', None)
    ad_id = create_ad(user_id, content, price, 
                      media['id'] if media else None, 
                      media['type'] if media else None)
    if media:
        del context.user_data['pending_ad_media']
    if ad_id:
        await update.message.reply_text(f"✅ Реклама отправлена на модерацию! ID: {ad_id}")
    else:
        await update.message.reply_text("❌ Ошибка при создании рекламы")

async def review_ad_cmd(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /review_ad <ad_id> <approve/reject>")
        return
    try:
        ad_id = int(context.args[0])
        action = context.args[1].lower()
        if action not in ('approve', 'reject'):
            await update.message.reply_text("⚠️ Укажите действие: approve или reject")
            return
        result = review_ad(update.effective_user.id, ad_id, action == 'approve')
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("⚠️ ID рекламы должен быть числом")

async def delete_post_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Использование: /delete_post <post_id>")
        return
    try:
        post_id = int(context.args[0])
        result = delete_post(update.effective_user.id, post_id)
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("⚠️ ID поста должен быть числом")

async def search_content_cmd(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Использование: /search_content <ключевое слово>")
        return
    keyword = ' '.join(context.args)
    user_id = update.effective_user.id
    results = search_content(keyword, user_id)
    if not results:
        await update.message.reply_text("🔍 Ничего не найдено.")
        return
    response = "🔍 Результаты поиска:\n\n"
    for post in results:
        post_id, content, post_date, nickname, media_id, media_type = post
        preview = content[:100] + "..." if len(content) > 100 else content
        response += f"👤 @{nickname} ({post_date.split()[0]})\n{preview}\nID поста: {post_id}\n\n"
    await update.message.reply_text(response)

# Основная функция
def main():
    application = Application.builder().token("СЮДА ТОКЕН БОТА").build()
    
    # Обработчики команд
    command_handlers = [
        CommandHandler("start", start),
        CommandHandler("block", block_user_cmd),
        CommandHandler("unblock", unblock_user_cmd),
        CommandHandler("msg", send_message_cmd),
        CommandHandler("daily_bonus", daily_bonus_cmd),
        CommandHandler("search_users", search_users_cmd),
        CommandHandler("search_groups", search_groups_cmd),
        CommandHandler("search_posts", search_posts_cmd),
        CommandHandler("create_group", create_group_cmd),
        CommandHandler("start_live", start_live_cmd),
        CommandHandler("transfer", transfer_cmd),
        CommandHandler("sell", sell_cmd),
        CommandHandler("create_ad", create_ad_cmd),
        CommandHandler("review_ad", review_ad_cmd),
        CommandHandler("delete_post", delete_post_cmd),
        CommandHandler("stories", show_stories),
        CommandHandler("search_content", search_content_cmd),
        CommandHandler("help", help_command),
    ]
    
    for handler in command_handlers:
        application.add_handler(handler)
    
    # Обработчики сообщений и колбэков
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    application.run_polling()

if __name__ == '__main__':
    main()