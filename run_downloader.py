# -*- coding: utf-8 -*-
import os
import sys
import argparse
import logging
import pandas as pd
from src.config import (
    BASE_DIR, CSV_FILE, DOWNLOAD_LOG_FILE, LOG_LEVEL, DOWNLOADS_DIR,
    PLAYLIST_JSON_FILE, PLAYLIST_M3U_FILE, PLAYLIST_JSON_SORT_ORDER,
    CLEANUP_THUMBNAILS_AFTER_DOWNLOAD
)
from src.downloader import download_tracks
from src.playlist import create_playlist_json, create_m3u_playlist

# --- Настройка логирования ---
log_level_map = {
    'DEBUG': logging.DEBUG, 'INFO': logging.INFO,
    'WARNING': logging.WARNING, 'ERROR': logging.ERROR
}
# Устанавливаем уровень из конфига, по умолчанию INFO
log_level = log_level_map.get(LOG_LEVEL.upper(), logging.INFO)

# Настраиваем базовую конфигурацию логирования
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Перезаписываем лог-файл при каждом запуске
        logging.FileHandler(DOWNLOAD_LOG_FILE, encoding='utf-8', mode='w'),
        # Выводим логи уровня INFO и выше в консоль
        logging.StreamHandler(sys.stdout)
    ]
)
# Устанавливаем уровень INFO для StreamHandler, чтобы не засорять консоль DEBUG сообщениями
logging.getLogger().handlers[1].setLevel(logging.INFO)

# Логгер этого скрипта
logger = logging.getLogger(__name__) # Имя логгера = имя модуля
# -----------------------------

def cleanup_temp_files():
    """Удаляет временные файлы обложек, если настроено."""
    # info.json файлы больше не создаются и не удаляются
    thumb_count = 0
    if not CLEANUP_THUMBNAILS_AFTER_DOWNLOAD:
        logger.info("ℹ️ Очистка файлов обложек отключена (CLEANUP_THUMBNAILS_AFTER_DOWNLOAD=False).")
        return

    logger.info("🧹 Очистка временных файлов обложек...")
    try:
        if not os.path.isdir(DOWNLOADS_DIR):
             logger.warning(f"Папка {DOWNLOADS_DIR} не найдена, очистка не требуется.")
             return

        for filename in os.listdir(DOWNLOADS_DIR):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            try:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                     # Проверяем наличие соответствующего MP3
                     mp3_equivalent = os.path.splitext(filepath)[0] + '.mp3'
                     if os.path.exists(mp3_equivalent):
                          os.remove(filepath)
                          thumb_count += 1
                          logger.debug(f"Удалена обложка: {filename}")
                     else:
                          logger.debug(f"Обложка {filename} оставлена (нет MP3).")
            except OSError as e:
                logger.error(f"Ошибка при удалении файла {filename}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при очистке: {e}", exc_info=True)

    logger.info(f"✨ Удалено {thumb_count} файлов обложек.")


def check_file_structure():
    """Проверяет наличие основных файлов и папок для запуска скачивания."""
    logger.info("Проверка структуры для скачивания...")
    all_ok = True
    # Проверяем наличие папки для данных (где CSV и архив)
    if not os.path.isdir(os.path.dirname(CSV_FILE)):
         logger.critical(f"❌ Папка для данных не найдена: {os.path.dirname(CSV_FILE)}")
         all_ok = False
    # Проверяем CSV файл (только если не пропускаем скачивание)
    if not args.skip_download and not os.path.exists(CSV_FILE):
         logger.critical(f"❌ Файл с лайками не найден: {CSV_FILE}. Запустите сначала сбор лайков.")
         all_ok = False
    # Папка для скачивания будет создана, если ее нет
    # Папка для плеера (куда пишем JSON) будет создана
    if all_ok:
         logger.info("✅ Необходимые файлы/папки для запуска присутствуют.")
    return all_ok

def main(skip_download_flag):
    """Основная функция запуска скачивания и генерации плейлистов."""
    logger.info("="*10 + "🚀 Запуск процесса скачивания и обновления плейлистов" + "="*10)

    if not check_file_structure() and not skip_download_flag:
         logger.critical("Проверка структуры не пройдена. Завершение работы.")
         sys.exit(1) # Выход с кодом ошибки

    links_to_download = []
    if not skip_download_flag:
        # --- Загрузка CSV ---
        try:
            logger.info(f"Чтение CSV файла: {CSV_FILE}")
            df = pd.read_csv(CSV_FILE)
            links_to_download = df['Link'].dropna().unique().tolist()
            logger.info(f"🎧 Найдено {len(links_to_download)} уникальных ссылок.")
            if not links_to_download:
                logger.warning("⚠️ CSV файл пуст или не содержит ссылок. Скачивание не начнется.")
        except FileNotFoundError:
            logger.error(f"❌ Файл {CSV_FILE} не найден. Нечего скачивать.")
            # Выход, так как без CSV скачивать нечего (если не skip_download)
            sys.exit(1)
        except Exception as e:
            logger.critical(f"❌ Не удалось загрузить или обработать CSV файл {CSV_FILE}: {e}", exc_info=True)
            sys.exit(1)
        # --- Конец загрузки CSV ---
    else:
        logger.info("⏩ Скачивание пропущено (флаг --skip-download).")

    # --- Скачивание треков ---
    if not skip_download_flag and links_to_download:
        download_tracks(links_to_download)
        # После скачивания можно вызвать очистку обложек, если включено
        cleanup_temp_files()
    elif not links_to_download and not skip_download_flag:
         logger.info("Ссылок для скачивания нет.")
    # --- Конец скачивания ---

    # --- Генерация плейлистов (всегда) ---
    logger.info("Генерация/обновление плейлистов...")
    # Убедимся, что папка downloads существует перед генерацией
    if not os.path.isdir(DOWNLOADS_DIR):
         logger.warning(f"Папка {DOWNLOADS_DIR} не найдена. Плейлисты не могут быть созданы.")
    else:
        json_created = create_playlist_json(
            output_dir=DOWNLOADS_DIR,
            output_file=PLAYLIST_JSON_FILE,
            sort_order=PLAYLIST_JSON_SORT_ORDER
        )
        m3u_created = create_m3u_playlist(
            output_dir=DOWNLOADS_DIR,
            output_file=PLAYLIST_M3U_FILE
        )
        if not json_created and not m3u_created:
             logger.warning("Не удалось создать плейлисты (возможно, папка 'downloads' пуста?).")
    # --- Конец генерации плейлистов ---

    logger.info("🏁 Процесс завершен.")
    logger.info(f"Лог файл сохранен в: {DOWNLOAD_LOG_FILE}")

if __name__ == "__main__":
    # --- Обработка аргументов командной строки ---
    parser = argparse.ArgumentParser(description="Скачивает треки SoundCloud и генерирует плейлисты.")
    parser.add_argument(
        '--skip-download',
        action='store_true', # Если флаг указан, будет True
        help='Пропустить фазу скачивания и только обновить плейлисты.'
    )
    args = parser.parse_args()
    # --- Конец обработки аргументов ---

    main(skip_download_flag=args.skip_download)