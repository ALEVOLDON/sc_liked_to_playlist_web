# -*- coding: utf-8 -*-
import os
import json
import logging
from .metadata import get_track_metadata
# --- ИЗМЕНЕНО: Импортируем нужные пути и настройки из конфига ---
from .config import INCLUDE_DURATION_IN_JSON, WEB_PLAYER_DIR, DOWNLOADS_DIR

# Настройка логгера
logger = logging.getLogger(__name__)

def create_playlist_json(output_dir, output_file, sort_order='title'):
    """
    Создает JSON-плейлист для веб-плеера из ВСЕХ mp3 файлов в output_dir.
    Использует относительные пути от папки web_player.
    """
    playlist_items = []
    logger.info(f"Создание JSON плейлиста (сортировка: {sort_order})...")

    # Убедимся, что output_dir это ожидаемая папка downloads
    # Эта проверка нестрогая, но может помочь
    if os.path.normpath(output_dir) != os.path.normpath(DOWNLOADS_DIR):
         logger.warning(f"Папка для сканирования MP3 ({output_dir}) не совпадает с DOWNLOADS_DIR ({DOWNLOADS_DIR}) из конфига. Пути могут быть неверными.")

    try:
        # Собираем пути к mp3 файлам
        mp3_filepaths = [
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if f.lower().endswith('.mp3') and not f.endswith('.part')
        ]
        logger.info(f"Найдено {len(mp3_filepaths)} MP3 файлов для обработки в {output_dir}.")
    except FileNotFoundError:
         logger.error(f"Папка для сканирования MP3 не найдена: {output_dir}")
         return False
    except Exception as e:
        logger.error(f"Ошибка при сканировании папки {output_dir}: {e}")
        return False

    # Извлекаем метаданные и формируем пути для всех файлов
    items_data = []
    web_player_full_path = WEB_PLAYER_DIR # Путь к папке плеера из конфига

    for filepath in mp3_filepaths:
        filename = os.path.basename(filepath)
        try:
            title, artist, duration = get_track_metadata(filepath) # Получаем метаданные

            # --- ИСПРАВЛЕНО: Расчет относительного пути к MP3 ---
            try:
                # Вычисляем путь от папки web_player к файлу MP3
                relative_src_path = os.path.relpath(filepath, start=web_player_full_path)
                # Заменяем обратные слеши на прямые для веб-совместимости
                relative_src_path = relative_src_path.replace('\\', '/')
                # Ожидаемый результат: '../downloads/track.mp3'
            except ValueError:
                 # Запасной вариант, если диски разные (маловероятно)
                 relative_src_path = f"../{os.path.basename(output_dir)}/{filename}".replace('\\', '/')
                 logger.warning(f"Не удалось вычислить относительный путь для {filename} через relpath, используется fallback: {relative_src_path}")
            # --- КОНЕЦ ИСПРАВЛЕНИЯ MP3 пути ---

            # --- ИСПРАВЛЕНО: Поиск обложки и расчет пути к ней ---
            relative_cover_path = ""
            thumbnail_base = os.path.splitext(filename)[0]
            # Ищем обложки в папке downloads (output_dir)
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                 thumb_name = thumbnail_base + ext
                 thumb_full_path = os.path.join(output_dir, thumb_name) # Полный путь к файлу обложки
                 if os.path.exists(thumb_full_path):
                      try:
                           # Вычисляем путь от папки web_player к файлу обложки
                           relative_cover_path = os.path.relpath(thumb_full_path, start=web_player_full_path)
                           relative_cover_path = relative_cover_path.replace('\\', '/')
                           # Ожидаемый результат: '../downloads/track.jpg'
                           break # Нашли обложку, выходим из цикла for ext
                      except ValueError:
                           relative_cover_path = f"../{os.path.basename(output_dir)}/{thumb_name}".replace('\\', '/')
                           logger.warning(f"Не удалось вычислить относительный путь для обложки {thumb_name} через relpath, используется fallback: {relative_cover_path}")
                           break # Нашли обложку, выходим из цикла for ext
            # --- КОНЕЦ ИСПРАВЛЕНИЯ пути к обложке ---

            # Формируем информацию о треке с ИСПРАВЛЕННЫМИ путями
            item_info = {
                "title": title,
                "artist": artist,
                "src": relative_src_path, # Используем исправленный путь
                "cover": relative_cover_path, # Используем исправленный путь
            }
            if INCLUDE_DURATION_IN_JSON: # Убедимся, что эта переменная импортирована/определена
                item_info["duration"] = duration

            items_data.append(item_info)

        except Exception as e:
            logger.error(f"Ошибка добавления трека {filename} в JSON: {e}", exc_info=True)
            continue # Пропускаем трек и переходим к следующему

    # Сортировка (без изменений)
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

    # Запись файла (без изменений)
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
    # Эта функция остается без изменений, т.к. M3U обычно используется
    # локальными плеерами, которые могут нормально разрешать пути
    # относительно самого M3U файла. Логика os.path.relpath здесь уже была.

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
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for filename in mp3_files:
                 filepath = os.path.join(output_dir, filename)
                 title, artist, duration = get_track_metadata(filepath)
                 try:
                    m3u_dir = os.path.dirname(output_file)
                    relative_path = os.path.relpath(filepath, start=m3u_dir).replace('\\', '/')
                 except ValueError:
                    # Запасной вариант, если M3U и треки на разных дисках
                    relative_path = os.path.join(os.path.basename(output_dir), filename).replace('\\', '/')

                 f.write(f"#EXTINF:{duration or -1},{artist} - {title}\n") # Используем -1 если duration = 0
                 f.write(f"{relative_path}\n")

        logger.info(f"✅ M3U плейлист сохранен: {os.path.abspath(output_file)} ({len(mp3_files)} треков)")
        return True
    except IOError as e:
        logger.error(f"❌ Не удалось записать M3U плейлист {output_file}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при сохранении M3U: {e}", exc_info=True)
        return False