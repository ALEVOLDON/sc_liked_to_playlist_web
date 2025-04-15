# -*- coding: utf-8 -*-
import os

# --- Базовые Пути ---
# Определяем базовую директорию как родительскую папку для 'src'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Пути к Данным и Логам ---
DATA_DIR = os.path.join(BASE_DIR, 'data')
CSV_FILE = os.path.join(DATA_DIR, 'liked_tracks.csv')
DOWNLOAD_ARCHIVE = os.path.join(DATA_DIR, 'downloaded.txt')
DOWNLOAD_LOG_FILE = os.path.join(DATA_DIR, 'download_log.txt')
CLEANUP_LOG_FILE = os.path.join(DATA_DIR, 'cleanup_log.txt')

# --- Пути для Медиа и Плейлистов ---
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
# Имя папки бэкапа будет создаваться с временной меткой в run_cleanup.py
BACKUP_DIR_BASE = os.path.join(BASE_DIR, 'downloads_backup')
WEB_PLAYER_DIR = os.path.join(BASE_DIR, 'web_player')
PLAYLIST_JSON_FILE = os.path.join(WEB_PLAYER_DIR, 'playlist.json') # JSON кладем к плееру
PLAYLIST_M3U_FILE = os.path.join(DATA_DIR, 'liked_playlist.m3u') # M3U можно в data

# --- Настройки Скачивания (yt-dlp) ---
MP3_QUALITY = '192' # Качество MP3 ('128', '192', '320', 'V0' ~ VBR)
EMBED_THUMBNAIL = True # Встраивать ли обложку в MP3
WRITE_METADATA = True # Записывать ли метаданные (исполнитель, название)
CLEANUP_THUMBNAILS_AFTER_DOWNLOAD = False # Удалять ли .jpg/.webp после скачивания
# SKIP_DOWNLOADS = False # Управляется через аргументы командной строки в run_downloader.py

# --- Настройки Фильтрации Треков ---
# Максимальная длительность в секундах для "трека"
MAX_TRACK_DURATION_SECONDS = 15 * 60 # 15 минут
# Ключевые слова для пропуска (миксы, подкасты и т.д.)
PODCAST_KEYWORDS = [
    'podcast', 'mix', 'radio', 'live', 'set', 'essential mix', 'episode', 'show',
    'ra.', 'resident advisor', 'boiler room', 'b2b', 'back to back', 'dj set',
    'dj mix', 'mixcloud', 'soundcloud radio', 'guest mix', 'live set',
    'recorded at', 'session', 'liveset', 'dj-set', 'podcast episode', 'tracklist',
    'full mix', 'compilation' # Добавлено
]

# --- Настройки Генерации Плейлиста ---
INCLUDE_DURATION_IN_JSON = True # Добавлять ли длительность в playlist.json
# Сортировка JSON: 'title' (по названию), 'artist' (по исполнителю), 'none' (порядок файловой системы)
PLAYLIST_JSON_SORT_ORDER = 'title'

# --- Настройки Логирования ---
LOG_LEVEL = 'INFO' # Уровень логирования ('DEBUG', 'INFO', 'WARNING', 'ERROR')

# --- Настройки Очистки (для run_cleanup.py) ---
CLEANUP_MIN_DURATION_SECONDS = 15 * 60 # Минимальная длина для удаления при очистке
CLEANUP_KEYWORDS = PODCAST_KEYWORDS # Используем те же ключевые слова