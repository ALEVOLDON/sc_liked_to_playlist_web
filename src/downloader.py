# -*- coding: utf-8 -*-
import yt_dlp
from tqdm import tqdm
import os
import time
import logging
from .config import (
    DOWNLOADS_DIR, DOWNLOAD_ARCHIVE, MP3_QUALITY, EMBED_THUMBNAIL, WRITE_METADATA
)
from .utils import get_safe_filepath, filter_tracks_only

# Настройка логгера
logger = logging.getLogger(__name__)

def download_tracks(links):
    """
    Скачивает треки из списка ссылок, используя настройки из config.py.
    Возвращает кортеж: (list_of_processed_files, success_count, skip_count, error_count)
    """
    processed_files = []
    success_count = 0
    skip_download_count = 0
    error_count = 0
    start_time = time.time()

    # --- Формирование опций yt-dlp на основе конфига ---
    postprocessors = []
    if MP3_QUALITY:
         postprocessors.append({
             'key': 'FFmpegExtractAudio',
             'preferredcodec': 'mp3',
             'preferredquality': MP3_QUALITY,
         })
    if EMBED_THUMBNAIL:
         postprocessors.append({'key': 'EmbedThumbnail'})
    if WRITE_METADATA:
        postprocessors.append({'key': 'FFmpegMetadata'})
        # Добавляем жанр только если включена запись метаданных
        postprocessor_args = {'ffmpegextractaudio': ['-metadata', 'genre=SoundCloud']}
    else:
        postprocessor_args = {}


    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'ignoreerrors': True, # Продолжать при ошибках отдельных треков
        'writethumbnail': EMBED_THUMBNAIL, # Скачиваем, только если будем встраивать
        'writeinfojson': False, # Не сохраняем info.json
        'download_archive': DOWNLOAD_ARCHIVE,
        'postprocessors': postprocessors,
        'postprocessor_args': postprocessor_args,
        'keepvideo': False,
        'match_filter': filter_tracks_only, # Используем наш фильтр
         # 'verbose': True, # Раскомментировать для отладки yt-dlp
    }
    # --- Конец формирования опций ---

    logger.info(f"Начинаем скачивание/обработку {len(links)} ссылок в {DOWNLOADS_DIR}...")
    logger.debug(f"Опции yt-dlp: {ydl_opts}")

    os.makedirs(DOWNLOADS_DIR, exist_ok=True) # Убедимся, что папка существует

    # Используем контекстный менеджер для yt-dlp
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # tqdm для прогресс-бара
            with tqdm(total=len(links), unit="ссылка", dynamic_ncols=True, desc="Обработка ссылок") as pbar:
                for link in links:
                    pbar.set_description(f"Обработка: {link[:50]}...") # Показываем начало ссылки
                    try:
                        # extract_info выполнит фильтр и скачивание (если нужно)
                        info = ydl.extract_info(link, download=True)
                        download_status = info.get('_download_status', 'downloaded') if info else 'error'

                        # --- Обработка статуса ---
                        if download_status == 'filtered':
                            reason = info.get('_filter_reason', 'N/A')
                            logger.info(f"⏭️ Пропущено фильтром: {info.get('title', link)} ({reason})")
                            skip_download_count += 1
                        elif download_status == 'already_downloaded':
                             logger.info(f"⏭️ Уже скачано (архив): {info.get('title', link)}")
                             skip_download_count += 1
                             # Пытаемся найти путь к существующему файлу
                             try:
                                base_path = ydl.prepare_filename(info).rsplit('.', 1)[0]
                                mp3_path = base_path + '.mp3'
                                if os.path.exists(mp3_path):
                                     processed_files.append(mp3_path)
                                else:
                                     # Если файл удалили вручную, но он в архиве
                                     logger.warning(f"Файл {mp3_path} помечен как скачанный, но не найден.")
                                     # Можно попробовать удалить из архива? Или просто игнорировать.
                             except Exception as e:
                                logger.warning(f"Не удалось определить путь для уже скачанного {info.get('title', link)}: {e}")
                        elif download_status == 'downloaded' and info and info.get('filepath'):
                            original_filepath = info['filepath']
                            final_mp3_path = os.path.splitext(original_filepath)[0] + '.mp3'
                            safe_mp3_path = get_safe_filepath(DOWNLOADS_DIR, info.get('title', 'unknown_track'))
                            try:
                                if os.path.exists(final_mp3_path):
                                    if final_mp3_path != safe_mp3_path:
                                        if os.path.exists(safe_mp3_path):
                                            logger.warning(f"Файл {os.path.basename(safe_mp3_path)} уже существует. Пропускаем переименование '{os.path.basename(final_mp3_path)}'.")
                                            processed_files.append(final_mp3_path)
                                        else:
                                            os.rename(final_mp3_path, safe_mp3_path)
                                            logger.info(f"✅ Скачано и переименовано: {os.path.basename(safe_mp3_path)}")
                                            processed_files.append(safe_mp3_path)
                                            success_count += 1
                                    else:
                                         logger.info(f"✅ Скачано: {os.path.basename(final_mp3_path)}")
                                         processed_files.append(final_mp3_path)
                                         success_count += 1
                                else:
                                    # Это может случиться, если postprocessor не создал MP3
                                    logger.error(f"❌ Ожидаемый MP3 файл не найден после скачивания: {final_mp3_path} (Оригинал: {original_filepath})")
                                    error_count += 1
                            except OSError as rename_err:
                                logger.error(f"❌ Ошибка переименования '{os.path.basename(final_mp3_path)}' -> '{os.path.basename(safe_mp3_path)}': {rename_err}")
                                error_count += 1
                                if os.path.exists(final_mp3_path): processed_files.append(final_mp3_path)
                        elif info is None or download_status == 'error':
                            logger.error(f"❌ Ошибка обработки (info is None или status error): {link}")
                            error_count += 1
                        else:
                             logger.warning(f"❓ Не удалось скачать: {info.get('title', link)} (Статус: {download_status})")
                             error_count += 1
                        # --- Конец обработки статуса ---

                    except yt_dlp.utils.DownloadError as e:
                        if "unable to download json metadata" in str(e).lower(): logger.warning(f"❓ Не удалось получить метаданные для {link} (возможно, трек удален/приватный)")
                        else: logger.error(f"❌ Ошибка скачивания {link}: {e}")
                        error_count += 1
                    except Exception as e:
                        logger.error(f"❌ Неожиданная ошибка при обработке {link}: {e}", exc_info=True)
                        error_count += 1
                    finally:
                        pbar.update(1)
                        pbar.set_postfix_str(f"✅{success_count} ⏭️{skip_download_count} ❌{error_count}")

    except Exception as e:
         logger.critical(f"Критическая ошибка при инициализации yt-dlp или в цикле: {e}", exc_info=True)
         # Возвращаем текущие счетчики, даже если не все обработали
         return processed_files, success_count, skip_download_count, error_count

    # Итоги
    total_time = time.time() - start_time
    logger.info("-" * 30+"📊 Статистика скачивания:"+"-"*30)
    logger.info(f"✅ Успешно скачано новых треков: {success_count}")
    logger.info(f"⏭️ Пропущено (миксы/подкасты/архив): {skip_download_count}")
    logger.info(f"❌ Ошибок обработки/скачивания: {error_count}")
    logger.info(f"⏱️ Общее время: {time.strftime('%H:%M:%S', time.gmtime(total_time))}")
    logger.info("-" * (60 + len("📊 Статистика скачивания:")))

    return processed_files, success_count, skip_download_count, error_count