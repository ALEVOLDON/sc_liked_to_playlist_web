# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import sys
import logging
import traceback # Импортируем traceback для вывода ошибок

# --- Добавляем КОРЕНЬ ПРОЕКТА в sys.path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root) # Добавляем КОРЕНЬ проекта
# ---------------------------------------------------

# --- Импорты из src ---
# Основные импорты для приложения Streamlit
try:
    from src.config import CSV_FILE, DATA_DIR
    from src.scraper import setup_driver, scroll_and_collect
    # logger = logging.getLogger(__name__)
except ImportError as e:
     st.error(f"Критическая ошибка: Не удалось импортировать модули из 'src': {e}")
     st.error(f"Убедитесь, что структура папок верна, файл '{os.path.join(project_root, 'src', '__init__.py')}' существует, и запускаете скрипт из корневой папки проекта.")
     st.stop()

# --- Импорты для скачивания (будут выполнены позже, при необходимости) ---
# Мы импортируем их внутри блока try/except при запуске скачивания,
# чтобы не вызывать ошибку, если пользователь просто открыл приложение
# без намерения скачивать немедленно.
# from src.downloader import download_tracks, cleanup_temp_files
# from src.playlist import create_playlist_json, create_m3u_playlist
# from src.config import DOWNLOADS_DIR, PLAYLIST_JSON_FILE, PLAYLIST_M3U_FILE, PLAYLIST_JSON_SORT_ORDER
# ----------------------

# === Настройки по умолчанию ===
DEFAULT_SCROLL_WAIT_TIME = 2.0 # Секунды
DEFAULT_MAX_CONSECUTIVE_SAME_HEIGHT = 3 # Количество проверок высоты
DEFAULT_MAX_TRACKS = 100 # По умолчанию без лимита

# === Интерфейс Streamlit ===
st.set_page_config(page_title="SoundCloud Like Collector", layout="wide")
st.title("🎵 SoundCloud Like Collector")

# Определяем относительный путь к CSV заранее для отображения
try:
    csv_rel_path = os.path.relpath(CSV_FILE, project_root)
except NameError:
    csv_rel_path = os.path.join('data', 'liked_tracks.csv') # Запасной вариант

st.caption(f"Собирает лайки, обновляет `{csv_rel_path}` и запускает скачивание.") # Изменено

# Колонки для ввода и настроек
col1, col2 = st.columns([2, 1])

with col1:
    username = st.text_input(
        "Имя пользователя SoundCloud:", "",
        help="То, что идет после soundcloud.com/"
    )
    start_button = st.button("🚀 Собрать, обновить и скачать") # Изменена надпись

with col2:
    st.subheader("⚙️ Настройки сбора")
    scroll_wait = st.number_input(
        "Пауза после скролла (секунды):",
        min_value=0.5, max_value=10.0, value=DEFAULT_SCROLL_WAIT_TIME, step=0.1,
        help="Время ожидания загрузки новых треков. Увеличьте при медленном интернете."
        )
    max_wait_count = st.number_input(
        "Кол-во проверок конца страницы:",
        min_value=1, max_value=10, value=DEFAULT_MAX_CONSECUTIVE_SAME_HEIGHT, step=1,
        help="Сколько раз высота должна совпасть, чтобы остановить скроллинг (если лимит треков не задан)."
        )
    max_tracks_limit = st.number_input(
        "Макс. треков для сбора (0 = без лимита):",
        min_value=0, value=DEFAULT_MAX_TRACKS, step=10,
        help="Остановить сбор, когда будет найдено указанное кол-во треков. 0 - собирать все до конца страницы."
        )

st.markdown("---")

# Инфо о CSV (показываем перед запуском)
existing_tracks_on_load = 0
csv_exists_on_load = False
try:
    csv_full_path = CSV_FILE
    if os.path.exists(csv_full_path):
        csv_exists_on_load = True
        try:
            df_existing_on_load = pd.read_csv(csv_full_path)
            existing_tracks_on_load = len(df_existing_on_load)
            st.info(f"ℹ️ Найден существующий файл `{csv_rel_path}` ({existing_tracks_on_load} треков).")
        except Exception as e:
            st.warning(f"⚠️ Не удалось прочитать существующий `{csv_rel_path}` перед запуском: {e}")
    else:
        st.info(f"ℹ️ Файл `{csv_rel_path}` не найден. Он будет создан.")
except NameError:
    st.warning("⚠️ Не удалось определить путь к CSV файлу (ошибка импорта?).")


# --- Логика обратной связи для Streamlit ---
if 'status_message' not in st.session_state: st.session_state.status_message = ""
if 'progress_value' not in st.session_state: st.session_state.progress_value = 0
if 'progress_text' not in st.session_state: st.session_state.progress_text = ""
if 'caption_message' not in st.session_state: st.session_state.caption_message = ""

status_placeholder = st.empty()
progress_bar_placeholder = st.empty()
progress_text_placeholder = st.empty()
caption_placeholder = st.empty()

# Обновляем callback для прогресса с учетом лимита
def update_streamlit_ui(type, message):
     global max_tracks_limit # Получаем доступ к значению лимита из UI
     if type == "status":
          st.session_state.status_message = message
     elif type == "progress":
          current_total = message
          target = max_tracks_limit if max_tracks_limit > 0 else 1000
          st.session_state.progress_value = min(current_total / target, 1.0) if target > 0 else 0
          progress_info = f" ({current_total}/{max_tracks_limit})" if max_tracks_limit > 0 else ""
          st.session_state.progress_text = f"Собрано {current_total} треков{progress_info}..."
     elif type == "caption":
          st.session_state.caption_message = message
     elif type == "info":
          status_placeholder.info(message)
     elif type == "warning":
          status_placeholder.warning(message)
     elif type == "error":
          status_placeholder.error(message)
     elif type == "success":
         status_placeholder.success(message)

     # Обновляем плейсхолдеры из session_state
     if st.session_state.status_message: status_placeholder.info(st.session_state.status_message)
     if st.session_state.progress_text:
          progress_bar_placeholder.progress(st.session_state.progress_value)
          progress_text_placeholder.text(st.session_state.progress_text)
     if st.session_state.caption_message: caption_placeholder.caption(st.session_state.caption_message)


# === Запуск сбора, ОБНОВЛЕНИЯ и СКАЧИВАНИЯ ===
if start_button:
    # Очищаем предыдущие статусы
    st.session_state.status_message = ""
    st.session_state.progress_value = 0
    st.session_state.progress_text = ""
    st.session_state.caption_message = ""
    status_placeholder.empty()
    progress_bar_placeholder.empty()
    progress_text_placeholder.empty()
    caption_placeholder.empty()

    # Очищаем и старые сообщения об успехе/статистике
    st.success("") # Скроет предыдущее сообщение об успехе
    st.info("") # Скроет предыдущее сообщение info
    st.warning("") # Скроет предыдущее предупреждение

    if not username.strip():
        st.warning("⚠️ Пожалуйста, введите имя пользователя SoundCloud.")
    else:
        profile_url = f"https://soundcloud.com/{username.strip()}/likes"
        st.markdown(f"🔗 Собираем лайки: [{profile_url}]({profile_url})")
        limit_text = f"до лимита в {max_tracks_limit} треков" if max_tracks_limit > 0 else "до конца страницы"
        st.markdown(f"(Пауза: {scroll_wait} сек, Проверок конца: {max_wait_count}, Лимит: {limit_text})")

        driver = None
        try:
            # --- Этап 1: Сбор лайков ---
            st.subheader("Этап 1: Сбор лайков")
            if 'setup_driver' not in globals() or 'scroll_and_collect' not in globals():
                 st.error("Критическая ошибка: Не удалось импортировать функции из src.")
                 st.stop()

            with st.spinner("Инициализация драйвера Chrome..."):
                driver = setup_driver()

            collected_list = scroll_and_collect(
                driver, profile_url, scroll_wait, max_wait_count,
                update_streamlit_ui, max_tracks=max_tracks_limit
            )

            status_placeholder.empty()
            progress_bar_placeholder.empty()
            progress_text_placeholder.empty()
            caption_placeholder.empty()

            if collected_list is None:
                 st.error("Сбор лайков не удался из-за ошибки загрузки страницы.")
                 st.stop() # Останавливаем выполнение, если сбор не удался

            total_scraped_this_run = len(collected_list)
            completion_reason = f"(достигнут лимит: {max_tracks_limit})" if (max_tracks_limit > 0 and total_scraped_this_run >= max_tracks_limit) else "(достигнут конец страницы)"
            st.success(f"✅ Этап 1 завершен! Собрано уникальных треков: {total_scraped_this_run} {completion_reason}")

            # --- Этап 2: Обновление CSV ---
            st.subheader("Этап 2: Обновление файла CSV")
            if not collected_list and not csv_exists_on_load:
                 st.warning("Не найдено ни одного лайка на странице и не было старого файла CSV. Скачивание не начнется.")
                 st.stop() # Останавливаем, если нечего скачивать

            df_final = None # Инициализируем df_final
            try:
                with st.spinner("Обновление CSV файла..."):
                    df_new = pd.DataFrame(collected_list, columns=["Title", "Link"]) if collected_list else pd.DataFrame(columns=["Title", "Link"])

                    df_existing = None
                    existing_links_count = 0
                    newly_added_count = 0
                    final_links_count = 0
                    csv_read_error = False

                    try:
                        if 'CSV_FILE' in globals() and os.path.exists(CSV_FILE):
                             df_existing = pd.read_csv(CSV_FILE)
                             existing_links_count = len(df_existing)
                        # Нет нужды выводить info о чтении здесь, сделаем это в итоговой статистике
                    except Exception as e:
                        st.warning(f"⚠️ Не удалось прочитать существующий CSV файл: {e}. Он будет перезаписан.")
                        df_existing = None
                        csv_read_error = True

                    if df_existing is not None:
                        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    else:
                        df_combined = df_new

                    df_final = df_combined.drop_duplicates(subset=['Link'], keep='last')
                    final_links_count = len(df_final)

                    if df_existing is not None and not csv_read_error:
                        newly_added_count = final_links_count - existing_links_count
                    else:
                         newly_added_count = final_links_count

                    # Сохраняем итоговый CSV
                    if 'DATA_DIR' not in globals() or 'CSV_FILE' not in globals():
                         st.error("Критическая ошибка: Не удалось импортировать пути из src.config.")
                         st.stop()
                    os.makedirs(DATA_DIR, exist_ok=True)
                    df_final.to_csv(CSV_FILE, index=False, encoding='utf-8')

                st.info(f"💾 Данные обновлены в `{csv_rel_path}`.")
                if df_existing is not None and not csv_read_error:
                    st.success(f"📊 Статистика CSV: Было: {existing_links_count}, Добавлено новых: {newly_added_count}, Всего в файле: {final_links_count}")
                elif csv_read_error:
                    st.warning(f"📊 Статистика CSV (файл перезаписан): Всего в файле: {final_links_count}")
                else: # Если файла не было
                    st.success(f"📊 Статистика CSV (файл создан): Всего в файле: {final_links_count}")

                # Кнопка скачивания итогового CSV (на всякий случай)
                csv_data = df_final.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Скачать итоговый CSV", data=csv_data,
                    file_name=f"{username.strip()}_liked_tracks_final.csv", mime="text/csv"
                )

            except Exception as e:
                st.error(f"Не удалось обработать или сохранить итоговый CSV: {e}")
                st.code(traceback.format_exc())
                st.stop() # Останавливаем, если CSV не удалось обновить

            # --- Этап 3: Автоматическое скачивание и создание плейлистов ---
            st.markdown("---")
            st.subheader("Этап 3: Скачивание и создание плейлистов")

            # Получаем список ссылок из финального DataFrame
            if df_final is None or df_final.empty:
                 st.warning("Нет данных в итоговом CSV для скачивания.")
                 st.stop()

            links_to_download = df_final['Link'].dropna().unique().tolist()

            if not links_to_download:
                  st.warning("Нет ссылок для скачивания в итоговом CSV.")
            else:
                  st.info(f"Начинаем обработку {len(links_to_download)} ссылок (скачивание / проверка архива)...")
                  st.warning("⚠️ Внимание: Интерфейс может не отвечать во время скачивания. Следите за прогрессом в терминале, где запущен Streamlit.")

                  try:
                       # Импортируем нужные функции здесь
                       from src.downloader import download_tracks, cleanup_temp_files
                       from src.playlist import create_playlist_json, create_m3u_playlist
                       from src.config import DOWNLOADS_DIR, PLAYLIST_JSON_FILE, PLAYLIST_M3U_FILE, PLAYLIST_JSON_SORT_ORDER, CLEANUP_THUMBNAILS_AFTER_DOWNLOAD

                       # Запускаем скачивание (блокирующая операция)
                       with st.spinner("Идет скачивание/обработка треков... Пожалуйста, подождите."):
                            processed_files, success_count, skip_count, error_count = download_tracks(links_to_download)

                       st.success(f"✅ Скачивание/обработка завершены!")
                       st.info(f"📊 Результат скачивания: Успешно: {success_count}, Пропущено (фильтр/архив): {skip_count}, Ошибки: {error_count}")

                       # Очистка временных файлов (опционально)
                       if CLEANUP_THUMBNAILS_AFTER_DOWNLOAD:
                           with st.spinner("Очистка временных файлов обложек..."):
                                cleanup_temp_files()
                       else:
                            st.info("ℹ️ Очистка файлов обложек отключена в config.py.")


                       # Генерация плейлистов
                       st.info("Генерация плейлистов...")
                       with st.spinner("Создание плейлистов..."):
                            if not os.path.isdir(DOWNLOADS_DIR):
                                 st.warning(f"Папка {DOWNLOADS_DIR} не найдена. Плейлисты не могут быть созданы.")
                                 json_created = False
                                 m3u_created = False
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

                       if json_created or m3u_created:
                            st.success("✅ Плейлисты успешно созданы/обновлены.")
                            try:
                                 playlist_rel_path = os.path.relpath(PLAYLIST_JSON_FILE, project_root)
                                 m3u_rel_path = os.path.relpath(PLAYLIST_M3U_FILE, project_root)
                                 st.markdown(f"* Веб-плеер использует: `{playlist_rel_path}`")
                                 st.markdown(f"* M3U плейлист сохранен в: `{m3u_rel_path}`")

                            except NameError: pass
                       else:
                            st.warning("Не удалось создать плейлисты (возможно, папка 'downloads' пуста или произошла ошибка).")

                       st.balloons() # Финальный успех!

                  except ImportError as import_err:
                       st.error(f"Критическая ошибка импорта модулей для скачивания: {import_err}")
                       st.code(traceback.format_exc())
                  except Exception as download_err:
                       st.error(f"Ошибка во время автоматического скачивания или создания плейлистов: {download_err}")
                       st.code(traceback.format_exc())

            st.markdown("---")
            st.info("🏁 Все этапы завершены.")

        # --- Общая обработка ошибок и закрытие драйвера ---
        except Exception as e:
            st.error(f"Произошла критическая ошибка на одном из этапов: {e}")
            st.error("Traceback:")
            st.code(traceback.format_exc())
        finally:
            if driver:
                try:
                    driver.quit()
                    st.info("Драйвер Chrome закрыт.")
                except Exception as e:
                    st.warning(f"Не удалось корректно закрыть драйвер Chrome: {e}")