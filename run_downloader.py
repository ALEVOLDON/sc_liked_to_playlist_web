# -*- coding: utf-8 -*-
import os
import sys
import argparse
import logging
import pandas as pd
from src.config import (
    BASE_DIR, CSV_FILE, DOWNLOAD_LOG_FILE, LOG_LEVEL, DOWNLOADS_DIR,
    PLAYLIST_JSON_FILE, PLAYLIST_M3U_FILE, PLAYLIST_JSON_SORT_ORDER
    # УДАЛИЛИ CLEANUP_THUMBNAILS_AFTER_DOWNLOAD ОТСЮДА, ТАК КАК ОН НЕ НУЖЕН НАПРЯМУЮ ЗДЕСЬ
)
# --- ИЗМЕНЕНО: ИМПОРТИРУЕМ cleanup_temp_files ---
from src.downloader import download_tracks, cleanup_temp_files
from src.playlist import create_playlist_json, create_m3u_playlist

# --- Настройка логирования (без изменений) ---
# ... (код настройки логирования) ...
logger = logging.getLogger(__name__)
# -----------------------------

# --->>> УДАЛИТЬ ОПРЕДЕЛЕНИЕ ФУНКЦИИ cleanup_temp_files ОТСЮДА <<<---
# def cleanup_temp_files():
#     """Удаляет временные файлы обложек, если настроено."""
#     # ... (ВЕСЬ КОД ЭТОЙ ФУНКЦИИ УДАЛИТЬ) ...
# --->>> КОНЕЦ УДАЛЕНИЯ <<<---


def check_file_structure():
    """Проверяет наличие основных файлов и папок для запуска скачивания."""
    # ... (код без изменений) ...
    return all_ok

def main(skip_download_flag):
    """Основная функция запуска скачивания и генерации плейлистов."""
    logger.info("="*10 + "🚀 Запуск процесса скачивания и обновления плейлистов" + "="*10)

    if not check_file_structure() and not skip_download_flag:
         logger.critical("Проверка структуры не пройдена. Завершение работы.")
         sys.exit(1)

    links_to_download = []
    if not skip_download_flag:
        try:
            logger.info(f"Чтение CSV файла: {CSV_FILE}")
            df = pd.read_csv(CSV_FILE)
            links_to_download = df['Link'].dropna().unique().tolist()
            logger.info(f"🎧 Найдено {len(links_to_download)} уникальных ссылок.")
            if not links_to_download:
                logger.warning("⚠️ CSV файл пуст или не содержит ссылок. Скачивание не начнется.")
        except FileNotFoundError:
            logger.error(f"❌ Файл {CSV_FILE} не найден. Нечего скачивать.")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"❌ Не удалось загрузить или обработать CSV файл {CSV_FILE}: {e}", exc_info=True)
            sys.exit(1)
    else:
        logger.info("⏩ Скачивание пропущено (флаг --skip-download).")

    # --- Скачивание треков ---
    if not skip_download_flag and links_to_download:
        download_tracks(links_to_download)
        # --- ВЫЗОВ ФУНКЦИИ ОЧИСТКИ ОСТАЕТСЯ ---
        # Функция теперь импортирована из src.downloader
        cleanup_temp_files()
        # --- КОНЕЦ ВЫЗОВА ---
    elif not links_to_download and not skip_download_flag:
         logger.info("Ссылок для скачивания нет.")

    # --- Генерация плейлистов (всегда) ---
    # ... (код без изменений) ...

    logger.info("🏁 Процесс завершен.")
    logger.info(f"Лог файл сохранен в: {DOWNLOAD_LOG_FILE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Скачивает треки SoundCloud и генерирует плейлисты.")
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Пропустить фазу скачивания и только обновить плейлисты.'
    )
    args = parser.parse_args()
    main(skip_download_flag=args.skip_download)