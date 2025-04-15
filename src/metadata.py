# -*- coding: utf-8 -*-
import os
import logging
from math import floor
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.easyid3 import EasyID3

# Настройка логгера для этого модуля
logger = logging.getLogger(__name__)

def get_track_metadata(filepath):
    """
    Извлекает метаданные (название, исполнитель, длительность) из MP3 файла.
    Возвращает кортеж (title: str, artist: str, duration: int).
    """
    title = None
    artist = None
    duration = 0
    filename_base = os.path.basename(filepath)
    filename_no_ext = filename_base.rsplit('.', 1)[0]

    try:
        audio = MP3(filepath, ID3=EasyID3)
        duration = floor(audio.info.length) if audio.info.length and audio.info.length > 0 else 0

        # Пытаемся получить теги, обрабатывая возможный KeyError
        try: title = audio['title'][0].strip() if audio.get('title') else None
        except KeyError: pass
        try: artist = audio['artist'][0].strip() if audio.get('artist') else None
        except KeyError: pass

        # --- Улучшенная логика определения исполнителя ---
        if not artist:
            tags_to_try = ['composer', 'albumartist']
            for tag in tags_to_try:
                 try: artist = audio[tag][0].strip() if audio.get(tag) else None
                 except KeyError: pass
                 if artist: break # Нашли - выходим

            # Попробовать извлечь из имени файла, если artist все еще не найден
            if not artist:
                 current_title = title if title else filename_no_ext # Используем название из тега или файла
                 parts = current_title.split(' - ', 1)
                 if len(parts) == 2 and parts[0].strip():
                     artist = parts[0].strip()
                     # Обновляем title только если он был взят из имени файла
                     if not title: title = parts[1].strip()
                     logger.debug(f"Извлекли исполнителя '{artist}' из имени файла для '{filename_base}'.")

        # --- Финальная проверка и установка значений по умолчанию ---
        if not artist:
            artist = "Unknown Artist"
            logger.warning(f"Не найден исполнитель для '{filename_base}', используется '{artist}'.")

        if not title:
            title = filename_no_ext # Название = имя файла без расширения
            logger.warning(f"Не найден тег 'title' для '{filename_base}', используется имя файла.")

        # Убираем лишние пробелы на всякий случай
        title = title.strip()
        artist = artist.strip()

        return title, artist, duration

    except HeaderNotFoundError:
        logger.error(f"Не удалось прочитать MP3 заголовок: {filename_base}")
    except Exception as e:
        logger.error(f"Ошибка чтения метаданных {filename_base}: {e}", exc_info=True)

    # Возвращаем значения по умолчанию в случае серьезной ошибки
    return filename_no_ext, "Unknown Artist", 0