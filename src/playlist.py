# -*- coding: utf-8 -*-
import os
import json
import logging
from .metadata import get_track_metadata
from .config import INCLUDE_DURATION_IN_JSON

# Настройка логгера
logger = logging.getLogger(__name__)

def create_playlist_json(output_dir, output_file, sort_order='title'):
    """
    Создает JSON-плейлист для веб-плеера из ВСЕХ mp3 файлов в output_dir.
    """
    playlist_items = []
    logger.info(f"Создание JSON плейлиста (сортировка: {sort_order})...")

    try:
        # Сначала собираем пути
        mp3_filepaths = [
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if f.lower().endswith('.mp3') and not f.endswith('.part')
        ]
        logger.info(f"Найдено {len(mp3_filepaths)} MP3 файлов для обработки в {output_dir}.")
    except FileNotFoundError:
         logger.error(f"Папка для сканирования не найдена: {output_dir}")
         return False
    except Exception as e:
        logger.error(f"Ошибка при сканировании папки {output_dir}: {e}")
        return False


    # Извлекаем метаданные для всех файлов
    items_data = []
    for filepath in mp3_filepaths:
        filename = os.path.basename(filepath)
        try:
            title, artist, duration = get_track_metadata(filepath)
            # Путь для плеера должен быть относительным к папке web_player
            # Пример: "downloads/Track Name.mp3"
            relative_src_path = os.path.join(os.path.basename(output_dir), filename).replace('\\', '/')

            relative_cover_path = ""
            thumbnail_base = os.path.splitext(filename)[0]
            # Ищем обложки с тем же именем в папке downloads
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                 thumb_name = thumbnail_base + ext
                 if os.path.exists(os.path.join(output_dir, thumb_name)):
                      relative_cover_path = os.path.join(os.path.basename(output_dir), thumb_name).replace('\\', '/')
                      break # Нашли первую попавшуюся

            item_info = {
                "title": title,
                "artist": artist,
                "src": relative_src_path,
                "cover": relative_cover_path
            }
            if INCLUDE_DURATION_IN_JSON:
                item_info["duration"] = duration

            items_data.append(item_info)

        except Exception as e:
            logger.error(f"Ошибка добавления трека {filename} в JSON: {e}", exc_info=True)
            continue

    # Сортировка
    try:
        sort_key = None
        if sort_order == 'artist':
            sort_key = lambda x: (x['artist'] or "").lower() # Устойчивость к None
            logger.info("Плейлист будет отсортирован по исполнителю.")
        elif sort_order == 'title':
            sort_key = lambda x: (x['title'] or "").lower()
            logger.info("Плейлист будет отсортирован по названию.")
        else: # 'none' или неизвестное значение
             logger.info("Плейлист останется в порядке файловой системы.")

        if sort_key:
             playlist_items = sorted(items_data, key=sort_key)
        else:
             playlist_items = items_data # Без сортировки

    except Exception as e:
        logger.error(f"Ошибка сортировки плейлиста: {e}. Используется порядок ФС.")
        playlist_items = items_data

    playlist_data = {"tracks": playlist_items}

    # Запись файла
    try:
        # Убедимся, что папка для файла существует (на случай web_player/playlist.json)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(playlist_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ JSON плейлист сохранен: {os.path.abspath(output_file)} ({len(playlist_items)} треков)")
        return len(playlist_items) > 0
    except IOError as e:
        logger.error(f"❌ Не удалось записать JSON плейлист {output_file}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при сохранении JSON: {e}", exc_info=True)
        return False


def create_m3u_playlist(output_dir, output_file):
    """Создает M3U плейлист из ВСЕХ mp3 файлов в output_dir с относительными путями."""
    logger.info("Создание M3U плейлиста...")

    try:
        mp3_files = sorted([
            f for f in os.listdir(output_dir)
            if f.lower().endswith('.mp3') and not f.endswith('.part')
        ])
    except FileNotFoundError:
         logger.error(f"Папка для сканирования не найдена: {output_dir}")
         return False
    except Exception as e:
        logger.error(f"Ошибка при сканировании папки {output_dir}: {e}")
        return False

    logger.info(f"Найдено {len(mp3_files)} MP3 файлов для включения в M3U.")
    if not mp3_files:
        logger.warning("⚠️ MP3 файлы не найдены, M3U плейлист не будет создан.")
        return False

    # Запись файла
    try:
        # Убедимся, что папка для файла существует (на случай data/playlist.m3u)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for filename in mp3_files:
                 filepath = os.path.join(output_dir, filename)
                 title, artist, duration = get_track_metadata(filepath)
                 # Относительный путь от папки, где будет лежать M3U
                 # Если M3U в data/, а треки в downloads/, путь будет ../downloads/file.mp3
                 # Рассчитаем относительный путь
                 try:
                    m3u_dir = os.path.dirname(output_file)
                    relative_path = os.path.relpath(filepath, start=m3u_dir).replace('\\', '/')
                 except ValueError: # Если диски разные (маловероятно)
                    relative_path = os.path.join(os.path.basename(output_dir), filename).replace('\\', '/') # Запасной вариант

                 f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                 f.write(f"{relative_path}\n")

        logger.info(f"✅ M3U плейлист сохранен: {os.path.abspath(output_file)} ({len(mp3_files)} треков)")
        return True
    except IOError as e:
        logger.error(f"❌ Не удалось записать M3U плейлист {output_file}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при сохранении M3U: {e}", exc_info=True)
        return False