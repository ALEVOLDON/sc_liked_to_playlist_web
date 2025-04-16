# -*- coding: utf-8 -*-
import yt_dlp
from tqdm import tqdm
import os
import time
import logging
import sys # Добавим sys на всякий случай для логгера

# --- ИМПОРТЫ КОНФИГУРАЦИИ И УТИЛИТ ---
from .config import (
    DOWNLOADS_DIR, DOWNLOAD_ARCHIVE, MP3_QUALITY, EMBED_THUMBNAIL, WRITE_METADATA,
    CLEANUP_THUMBNAILS_AFTER_DOWNLOAD # Убедимся, что это импортировано
)
from .utils import get_safe_filepath, filter_tracks_only

# Настройка логгера
logger = logging.getLogger(__name__)
# Установим базовый уровень, если логгер еще не настроен
if not logger.hasHandlers():
     # Используем базовую конфигурацию, но можно сделать более сложную
     log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
     logging.basicConfig(level=logging.INFO, format=log_format)
     # Если нужно выводить DEBUG сообщения из этого модуля в консоль/файл,
     # настройку нужно делать в главном скрипте (run_downloader.py/liker_app.py)


# --->>> НАЧАЛО ФУНКЦИИ download_tracks <<<---
def download_tracks(links):
    """
    Скачивает треки из списка ссылок, используя настройки из config.py.
    Возвращает кортеж: (list_of_processed_files, success_count, skip_count, error_count)
    """
    # --- ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ ---
    processed_files = [] # Список для хранения путей к успешно обработанным файлам
    success_count = 0
    skip_download_count = 0
    error_count = 0
    start_time = time.time()
    # --- КОНЕЦ ИНИЦИАЛИЗАЦИИ ---

    # --- Формирование опций yt-dlp на основе конфига ---
    postprocessors = []
    postprocessor_args = {} # Используем пустой словарь по умолчанию
    if MP3_QUALITY:
         postprocessors.append({
             'key': 'FFmpegExtractAudio',
             'preferredcodec': 'mp3',
             'preferredquality': MP3_QUALITY,
         })
         # Добавляем аргументы для FFmpeg только если он используется
         if WRITE_METADATA:
            # Добавляем жанр только если включена запись метаданных
             postprocessor_args['ffmpegextractaudio'] = ['-metadata', 'genre=SoundCloud']

    if EMBED_THUMBNAIL:
         postprocessors.append({'key': 'EmbedThumbnail'})
         # Аргументы для встраивания обложки, если нужны, добавляются сюда же

    # Добавляем запись метаданных как отдельный постпроцессор, если включено
    # и если ffmpegextractaudio не используется (на случай если качаем уже mp3)
    if WRITE_METADATA and not any(pp['key'] == 'FFmpegExtractAudio' for pp in postprocessors):
         postprocessors.append({'key': 'FFmpegMetadata'})
         # Может потребоваться добавить аргументы и для FFmpegMetadata, если нужно
         # postprocessor_args['ffmpegmetadata'] = ['-metadata', 'genre=SoundCloud']
    elif WRITE_METADATA and 'ffmpegextractaudio' not in postprocessor_args:
         # Если используется FFmpegExtractAudio, но жанр не был добавлен выше
         # (на случай если WRITE_METADATA=True, а MP3_QUALITY=None) - маловероятно
          postprocessor_args.setdefault('ffmpegextractaudio', []).extend(['-metadata', 'genre=SoundCloud'])


    ydl_opts = {
        'format': 'bestaudio/best',
        # Используем безопасное имя файла сразу при скачивании
        'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'), # yt-dlp сам обработает title
        'quiet': True, # Подавляем стандартный вывод yt-dlp
        'noplaylist': True,
        'ignoreerrors': True, # Продолжать при ошибках отдельных треков
        'writethumbnail': EMBED_THUMBNAIL, # Скачиваем обложку, только если будем встраивать
        'writeinfojson': False, # Не сохраняем info.json
        'download_archive': DOWNLOAD_ARCHIVE, # Файл для отслеживания скачанного
        'postprocessors': postprocessors,
        'postprocessor_args': postprocessor_args,
        'keepvideo': False, # Не оставлять видео файл после извлечения аудио
        'match_filter': filter_tracks_only, # Используем наш фильтр треков
        'progress_hooks': [], # Можно добавить hook для более детального прогресса
        'ffmpeg_location': None, # Можно указать путь к ffmpeg, если он не в PATH
         # 'verbose': True, # Раскомментировать для детальной отладки yt-dlp
         # Опции ниже могут помочь с некоторыми ошибками
         # 'socket_timeout': 30, # Таймаут соединения
         # 'retries': 5, # Количество попыток скачивания
         # 'fragment_retries': 5, # Количество попыток для фрагментов (DASH/HLS)
    }
    # --- Конец формирования опций ---

    logger.info(f"Начинаем скачивание/обработку {len(links)} ссылок в {DOWNLOADS_DIR}...")
    logger.debug(f"Опции yt-dlp: {ydl_opts}") # Логируем опции для отладки

    os.makedirs(DOWNLOADS_DIR, exist_ok=True) # Убедимся, что папка существует

    # Используем контекстный менеджер для yt-dlp для корректного завершения
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # tqdm для прогресс-бара в консоли (если запускать run_downloader.py)
            # При запуске из Streamlit tqdm может работать некорректно в UI,
            # но он будет писать в лог терминала.
            # Можно обернуть links в tqdm(links), если нужен прогресс в терминале.
            # for link in tqdm(links, unit="ссылка", dynamic_ncols=True, desc="Обработка ссылок"):
            for link in links:
                # Логируем начало обработки каждой ссылки
                logger.debug(f"Обработка ссылки: {link}")
                try:
                    # extract_info выполнит фильтр и скачивание (если download=True и не отфильтровано/не в архиве)
                    # download=True является поведением по умолчанию, если не использовать extract_info(..., download=False)
                    info = ydl.extract_info(link) # download=True по умолчанию

                    # Статус загрузки может быть в info словаре
                    # (но yt-dlp может и не добавить его, если был только pre-processing)
                    download_status = 'unknown'
                    if info is None: # Если info=None, скорее всего ошибка или фильтр сработал на этапе pre-processing
                         # Пытаемся понять, почему info is None
                         # Возможно, стоит проверить архив вручную или использовать хуки
                         logger.warning(f"❓ Не удалось получить info для {link} (возможно, уже в архиве или ошибка до скачивания). Проверяем архив.")
                         # Добавим ручную проверку архива, если info is None
                         if ydl.in_download_archive(info): # info тут может быть None, нужна проверка как это работает
                             download_status = 'already_downloaded'
                         else:
                              download_status = 'error_or_filtered_early'

                    elif '_type' in info and info['_type'] == 'playlist':
                         # Если ссылка оказалась плейлистом (не должна при noplaylist=True, но на всякий случай)
                         logger.warning(f"⏭️ Ссылка {link} оказалась плейлистом, пропускаем.")
                         download_status = 'skipped_playlist'
                         skip_download_count += 1

                    elif info.get('__downloaded') == False: # Проверка флага фильтрации
                          reason = info.get('_filter_reason', 'N/A')
                          logger.info(f"⏭️ Пропущено фильтром: {info.get('title', link)} ({reason})")
                          download_status = 'filtered'
                          skip_download_count += 1

                    elif ydl.in_download_archive(info):
                         logger.info(f"⏭️ Уже скачано (архив): {info.get('title', link)}")
                         download_status = 'already_downloaded'
                         skip_download_count += 1
                         # Пытаемся найти путь к существующему файлу
                         try:
                            # Получаем ожидаемое имя файла (без скачивания)
                            expected_path_base = ydl.prepare_filename(info).rsplit('.', 1)[0]
                            expected_mp3_path = expected_path_base + '.mp3'
                            if os.path.exists(expected_mp3_path):
                                 processed_files.append(expected_mp3_path)
                            else:
                                 logger.warning(f"Файл {expected_mp3_path} помечен как скачанный в архиве, но не найден на диске.")
                         except Exception as e_path:
                            logger.warning(f"Не удалось определить путь для уже скачанного {info.get('title', link)}: {e_path}")

                    elif info.get('filepath'): # Если файл был скачан и обработан
                        original_filepath = info['filepath']
                        # Ожидаемый путь после конвертации в MP3
                        final_mp3_path = os.path.splitext(original_filepath)[0] + '.mp3'
                        # Создаем безопасное имя файла на основе заголовка
                        safe_mp3_path = get_safe_filepath(DOWNLOADS_DIR, info.get('title', 'unknown_track'))

                        try:
                            if os.path.exists(final_mp3_path):
                                # Переименовываем в безопасное имя, если оно отличается
                                if final_mp3_path != safe_mp3_path:
                                    if os.path.exists(safe_mp3_path):
                                        logger.warning(f"Файл с безопасным именем {os.path.basename(safe_mp3_path)} уже существует. Пропускаем переименование для '{os.path.basename(final_mp3_path)}'.")
                                        # Добавляем тот файл, который точно есть
                                        processed_files.append(final_mp3_path)
                                    else:
                                        os.rename(final_mp3_path, safe_mp3_path)
                                        logger.info(f"✅ Скачано и переименовано: {os.path.basename(safe_mp3_path)}")
                                        processed_files.append(safe_mp3_path)
                                else:
                                     logger.info(f"✅ Скачано: {os.path.basename(final_mp3_path)}")
                                     processed_files.append(final_mp3_path)
                                success_count += 1
                                download_status = 'downloaded'
                            else:
                                # Это может случиться, если постпроцессор не создал MP3
                                logger.error(f"❌ Ожидаемый MP3 файл не найден после скачивания: {final_mp3_path} (Оригинал: {original_filepath}) для ссылки {link}")
                                download_status = 'error_postprocessing'
                                error_count += 1
                        except OSError as rename_err:
                            logger.error(f"❌ Ошибка переименования '{os.path.basename(final_mp3_path)}' -> '{os.path.basename(safe_mp3_path)}': {rename_err}")
                            error_count += 1
                            download_status = 'error_rename'
                            # Добавляем оригинальный файл, если он остался
                            if os.path.exists(final_mp3_path): processed_files.append(final_mp3_path)
                    else:
                        # Случай, когда info есть, но не скачано, не в архиве, не отфильтровано
                        logger.warning(f"❓ Не удалось скачать или обработать: {info.get('title', link)} (Статус неизвестен). Info: {info}")
                        download_status = 'error_unknown'
                        error_count += 1

                # --- Обработка исключений для ОДНОЙ ссылки ---
                except yt_dlp.utils.DownloadError as e:
                    # Ловим специфичные ошибки yt-dlp
                    if "is not a valid URL" in str(e): logger.error(f"❌ Некорректный URL: {link}")
                    elif "unable to download video data" in str(e): logger.error(f"❌ Не удалось скачать данные для {link}: {e}")
                    elif "returned non-zero exit status 1" in str(e): logger.error(f"❌ Ошибка постпроцессора (вероятно, ffmpeg) для {link}: {e}")
                    elif "JSON metadata" in str(e): logger.warning(f"❓ Не удалось получить метаданные для {link} (возможно, удален/приватный).")
                    else: logger.error(f"❌ Ошибка скачивания yt-dlp для {link}: {e}")
                    error_count += 1
                except Exception as e_inner:
                    # Ловим любые другие неожиданные ошибки при обработке ссылки
                    logger.error(f"❌ Неожиданная ошибка при обработке {link}: {e_inner}", exc_info=True)
                    error_count += 1
                # --- Конец обработки исключений для ОДНОЙ ссылки ---

    # --- Обработка исключений для ВСЕГО процесса yt-dlp ---
    except Exception as e_outer:
         logger.critical(f"Критическая ошибка при инициализации yt-dlp или в цикле: {e_outer}", exc_info=True)
         # Возвращаем текущие счетчики, даже если не все обработали
         # 'processed_files' был инициализирован в начале функции
         return processed_files, success_count, skip_download_count, error_count
    # --- Конец обработки исключений для ВСЕГО процесса yt-dlp ---


    # Итоги
    total_time = time.time() - start_time
    logger.info("-" * 30+"📊 Статистика скачивания:"+"-"*30)
    logger.info(f"✅ Успешно скачано/обработано новых треков: {success_count}")
    logger.info(f"⏭️ Пропущено (фильтр/архив/плейлист): {skip_download_count}")
    logger.info(f"❌ Ошибок обработки/скачивания: {error_count}")
    logger.info(f"⏱️ Общее время: {time.strftime('%H:%M:%S', time.gmtime(total_time))}")
    logger.info("-" * (60 + len("📊 Статистика скачивания:")))

    # --- ВОЗВРАТ РЕЗУЛЬТАТОВ ---
    return processed_files, success_count, skip_download_count, error_count
# --->>> КОНЕЦ ФУНКЦИИ download_tracks <<<---


# --->>> НАЧАЛО ФУНКЦИИ cleanup_temp_files <<<---
def cleanup_temp_files():
    """Удаляет временные файлы обложек, если настроено."""
    thumb_count = 0
    # Используем конфиг, импортированный в начале файла
    if not CLEANUP_THUMBNAILS_AFTER_DOWNLOAD:
        logger.info("ℹ️ Очистка файлов обложек отключена (CLEANUP_THUMBNAILS_AFTER_DOWNLOAD=False).")
        return

    logger.info("🧹 Очистка временных файлов обложек...")
    try:
        # Используем конфиг, импортированный в начале файла
        if not os.path.isdir(DOWNLOADS_DIR):
             logger.warning(f"Папка {DOWNLOADS_DIR} не найдена, очистка не требуется.")
             return

        for filename in os.listdir(DOWNLOADS_DIR):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            try:
                # Удаляем только файлы обложек, связанные с существующими MP3
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                     mp3_equivalent = os.path.splitext(filepath)[0] + '.mp3'
                     if os.path.exists(mp3_equivalent):
                          os.remove(filepath)
                          thumb_count += 1
                          logger.debug(f"Удалена обложка: {filename}")
                     else:
                          logger.debug(f"Обложка {filename} оставлена (нет MP3).")
            except OSError as e:
                logger.error(f"Ошибка при удалении файла {filename}: {e}")
            except Exception as e_inner:
                 logger.error(f"Неожиданная ошибка при обработке файла {filename} для очистки: {e_inner}")

    except FileNotFoundError:
         logger.error(f"Ошибка: Папка {DOWNLOADS_DIR} не найдена во время очистки.")
    except Exception as e_outer:
        logger.error(f"Неожиданная ошибка при очистке: {e_outer}", exc_info=True)

    if thumb_count > 0:
        logger.info(f"✨ Удалено {thumb_count} файлов обложек.")
    else:
         logger.info("✨ Файлы обложек для удаления не найдены или очистка не требовалась.")
# --->>> КОНЕЦ ФУНКЦИИ cleanup_temp_files <<<---