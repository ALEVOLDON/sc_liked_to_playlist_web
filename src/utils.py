# -*- coding: utf-8 -*-
import re
import os
import logging
from .config import PODCAST_KEYWORDS, MAX_TRACK_DURATION_SECONDS

def sanitize_filename(filename):
    """Очищает имя файла от недопустимых символов и лишних пробелов."""
    if not isinstance(filename, str):
        logging.error(f"Ошибка sanitize_filename: ожидалась строка, получено {type(filename)}")
        filename = "invalid_filename" # Возвращаем запасное имя
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    filename = re.sub(r'[\s_]+', ' ', filename)
    return filename.strip()

def get_safe_filepath(base_path, title, extension="mp3"):
    """Создает безопасный путь к файлу."""
    safe_title = sanitize_filename(title)
    return os.path.join(base_path, f"{safe_title}.{extension}")

def filter_tracks_only(info):
    """
    Фильтр для yt-dlp ('match_filter'). Пропускает только треки.
    Возвращает None, если это ТРЕК (нужно скачать), иначе строку с причиной пропуска.
    Использует настройки из src.config
    """
    if not info: return "Нет информации о видео" # Проверка на пустой info

    title = info.get('title', '').lower()
    description = info.get('description', '').lower()
    uploader = info.get('uploader', '').lower()
    duration = info.get('duration')

    # 1. Проверка по ключевым словам
    text_to_check = f"{title} {description} {uploader}"
    for keyword in PODCAST_KEYWORDS:
        if keyword in text_to_check:
            logging.debug(f"Фильтр: Пропуск '{info.get('title', 'N/A')}' из-за слова '{keyword}'")
            return f"Ключевое слово: '{keyword}'" # Короче причина

    # 2. Проверка по длительности
    if duration is not None:
        if duration > MAX_TRACK_DURATION_SECONDS:
            duration_min = duration / 60
            logging.debug(f"Фильтр: Пропуск '{info.get('title', 'N/A')}' из-за длительности ({duration_min:.1f} мин)")
            return f"Длительность > {MAX_TRACK_DURATION_SECONDS / 60:.0f} мин" # Короче причина

    # Если прошло обе проверки - считаем треком
    logging.debug(f"Фильтр: OK '{info.get('title', 'N/A')}' (длительность: {duration} сек)")
    return None