# -*- coding: utf-8 -*-
import os
import sys
import logging
import shutil
import time
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.easyid3 import EasyID3
from src.config import (
    BASE_DIR, DOWNLOADS_DIR, BACKUP_DIR_BASE, CLEANUP_LOG_FILE, LOG_LEVEL,
    CLEANUP_MIN_DURATION_SECONDS, CLEANUP_KEYWORDS
)

# --- Настройка логирования ---
log_level_map = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR}
log_level = log_level_map.get(LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CLEANUP_LOG_FILE, encoding='utf-8', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.getLogger().handlers[1].setLevel(logging.INFO) # Консоль только INFO и выше
logger = logging.getLogger(__name__)
# -----------------------------

def is_podcast_or_mix_for_cleanup(filepath):
    """
    Проверяет, является ли файл подкастом/миксом для удаления.
    Использует настройки из config.py (CLEANUP_MIN_DURATION_SECONDS, CLEANUP_KEYWORDS).
    """
    filename_lower = os.path.basename(filepath).lower()

    # 1. Проверка по ключевым словам в имени файла
    for keyword in CLEANUP_KEYWORDS:
         if keyword in filename_lower:
             logger.debug(f"Очистка: '{os.path.basename(filepath)}' - ключевое слово в имени файла ('{keyword}').")
             return True

    # 2. Проверка ID3-тегов и длительности
    try:
        audio = MP3(filepath, ID3=EasyID3)
        duration = audio.info.length if audio.info.length else 0

        # Проверка длительности
        if duration > CLEANUP_MIN_DURATION_SECONDS:
            logger.debug(f"Очистка: '{os.path.basename(filepath)}' - длительность ({duration / 60:.1f} мин).")
            return True

        # Проверка ключевых слов в тегах
        title = (audio['title'][0].lower() if audio.get('title') else "")
        artist = (audio['artist'][0].lower() if audio.get('artist') else "")

        text_to_check = f"{title} {artist}"
        for keyword in CLEANUP_KEYWORDS:
            if keyword in text_to_check:
                 logger.debug(f"Очистка: '{os.path.basename(filepath)}' - ключевое слово в тегах ('{keyword}').")
                 return True

    except HeaderNotFoundError:
        logger.warning(f"Не удалось прочитать MP3 заголовок для файла: {os.path.basename(filepath)} - файл не будет удален.")
    except Exception as e:
        logger.error(f"Ошибка чтения метаданных для {os.path.basename(filepath)}: {e} - файл не будет удален.")

    # Если ни одна проверка не сработала
    logger.debug(f"Очистка: '{os.path.basename(filepath)}' - НЕ определён как микс/подкаст.")
    return False

def main():
    """Основная функция для очистки папки downloads."""
    logger.info("="*10 + "🚀 Запуск скрипта очистки миксов/подкастов" + "="*10)

    if not os.path.isdir(DOWNLOADS_DIR):
        logger.error(f"❌ Папка {DOWNLOADS_DIR} не найдена. Нечего очищать.")
        sys.exit(1)

    # --- Создание резервной копии ---
    backup_dir_with_timestamp = f"{BACKUP_DIR_BASE}_{time.strftime('%Y%m%d_%H%M%S')}"
    try:
        logger.info(f"📦 Создание резервной копии '{DOWNLOADS_DIR}' в '{backup_dir_with_timestamp}'...")
        shutil.copytree(DOWNLOADS_DIR, backup_dir_with_timestamp)
        logger.info(f"✅ Резервная копия успешно создана.")
    except FileExistsError:
        # Это не должно произойти из-за временной метки, но на всякий случай
        logger.error(f"❌ Папка для резервной копии {backup_dir_with_timestamp} уже существует!")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Не удалось создать резервную копию: {e}", exc_info=True)
        sys.exit(1)
    # --- Конец создания бэкапа ---

    # --- Перебор и удаление файлов ---
    removed_files = []
    kept_files_count = 0
    error_files = []

    logger.info(f"🧹 Поиск и удаление миксов/подкастов из {DOWNLOADS_DIR}...")
    all_files = os.listdir(DOWNLOADS_DIR)

    for filename in all_files:
        # Проверяем только MP3 файлы
        if filename.lower().endswith('.mp3') and not filename.endswith('.part'):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            try:
                if is_podcast_or_mix_for_cleanup(filepath):
                    os.remove(filepath)
                    logger.info(f"🗑️ Удален файл: {filename}")
                    removed_files.append(filename)
                else:
                    kept_files_count += 1
            except OSError as e:
                logger.error(f"❌ Не удалось удалить файл {filename}: {e}")
                error_files.append(filename)
                kept_files_count += 1 # Не удалили - считаем оставшимся
            except Exception as e:
                 logger.error(f"❌ Неожиданная ошибка при обработке {filename}: {e}", exc_info=True)
                 error_files.append(filename)
                 kept_files_count += 1
        elif not filename.lower().endswith('.mp3'):
            # Другие файлы (обложки и т.д.) просто игнорируем и считаем оставшимися
             logger.debug(f"Пропуск не-MP3 файла: {filename}")
             kept_files_count += 1


    # --- Вывод статистики ---
    logger.info("-" * 30 + "📊 Статистика очистки:" + "-"*30)
    logger.info(f"✅ Оставлено файлов (включая не-MP3): {kept_files_count}")
    logger.info(f"🗑️ Удалено MP3 файлов (миксы/подкасты): {len(removed_files)}")
    if error_files:
        logger.warning(f"❌ Ошибок при удалении/обработке: {len(error_files)}")
        logger.warning("Файлы с ошибками:")
        for err_file in error_files: logger.warning(f"  - {err_file}")

    if removed_files:
        logger.info("\n--- Список удаленных MP3 файлов ---")
        for file in removed_files: logger.info(f"  - {file}")
        logger.info("--- Конец списка ---")

    logger.info(f"\n💾 Резервная копия ОРИГИНАЛЬНОЙ папки сохранена в: {os.path.abspath(backup_dir_with_timestamp)}")
    logger.warning("⚠️ ВАЖНО: После очистки необходимо обновить плейлисты!")
    logger.warning("Запустите: python run_downloader.py --skip-download")
    logger.info(f"Лог файл сохранен в: {CLEANUP_LOG_FILE}")
    logger.info("🏁 Скрипт очистки завершил работу.")

if __name__ == "__main__":
    main()