# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import sys
import logging # Оставим импорт logging, т.к. он может понадобиться для логгирования в будущем

# --- Добавляем КОРЕНЬ ПРОЕКТА в sys.path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root) # Добавляем КОРЕНЬ проекта
# ---------------------------------------------------

# --- Импорты из src ---
# Импорты выполняются после добавления project_root в sys.path
try:
    from src.config import CSV_FILE, DATA_DIR
    from src.scraper import setup_driver, scroll_and_collect
    # Можно настроить логгер здесь, если потребуется
    # logger = logging.getLogger(__name__)
except ImportError as e:
     # Эта ошибка теперь не должна возникать, но оставим на всякий случай
     st.error(f"Критическая ошибка: Не удалось импортировать модули из 'src': {e}")
     st.error(f"Убедитесь, что структура папок верна, файл '{os.path.join(project_root, 'src', '__init__.py')}' существует, и запускаете скрипт из корневой папки проекта.")
     st.stop()
# ----------------------

# === Настройки по умолчанию ===
DEFAULT_SCROLL_WAIT_TIME = 2.0 # Секунды
DEFAULT_MAX_CONSECUTIVE_SAME_HEIGHT = 3 # Количество проверок высоты

# === Интерфейс Streamlit ===
st.set_page_config(page_title="SoundCloud Like Collector", layout="wide")
st.title("🎵 SoundCloud Like Collector")

# Показываем относительный путь к CSV от корня проекта
try:
    # Убедимся, что CSV_FILE импортирован
    csv_rel_path = os.path.relpath(CSV_FILE, project_root)
except NameError:
    csv_rel_path = os.path.join('data', 'liked_tracks.csv') # Запасной вариант
st.caption(f"Собирает лайки и сохраняет их в `{csv_rel_path}`")

# Колонки для ввода и настроек
col1, col2 = st.columns([2, 1])

with col1:
    username = st.text_input(
        "Имя пользователя SoundCloud:", "",
        help="То, что идет после soundcloud.com/"
    )
    start_button = st.button("🚀 Собрать лайки")

with col2:
    st.subheader("⚙️ Настройки скроллинга")
    scroll_wait = st.number_input(
        "Пауза после скролла (секунды):",
        min_value=0.5, max_value=10.0, value=DEFAULT_SCROLL_WAIT_TIME, step=0.1,
        help="Время ожидания загрузки новых треков. Увеличьте при медленном интернете."
        )
    max_wait_count = st.number_input(
        "Кол-во проверок конца страницы:",
        min_value=1, max_value=10, value=DEFAULT_MAX_CONSECUTIVE_SAME_HEIGHT, step=1,
        help="Сколько раз высота должна совпасть, чтобы остановить скроллинг."
        )

st.markdown("---")

# Инфо о CSV
existing_tracks = 0
try:
    # Убедимся, что CSV_FILE импортирован
    csv_full_path = CSV_FILE
    csv_exists = os.path.exists(csv_full_path)
    if csv_exists:
        try:
            df_existing = pd.read_csv(csv_full_path)
            existing_tracks = len(df_existing)
            st.info(f"ℹ️ Найден `{csv_rel_path}` ({existing_tracks} треков). Будет перезаписан.")
        except Exception as e:
            st.warning(f"⚠️ Не удалось прочитать `{csv_rel_path}`: {e}")
except NameError:
    st.warning("⚠️ Не удалось определить путь к CSV файлу (ошибка импорта?).")


# --- Логика обратной связи для Streamlit ---
# Используем session_state для хранения временных сообщений и прогресса
if 'status_message' not in st.session_state: st.session_state.status_message = ""
if 'progress_value' not in st.session_state: st.session_state.progress_value = 0
if 'progress_text' not in st.session_state: st.session_state.progress_text = ""
if 'caption_message' not in st.session_state: st.session_state.caption_message = ""

status_placeholder = st.empty()
progress_bar_placeholder = st.empty()
progress_text_placeholder = st.empty()
caption_placeholder = st.empty()

def update_streamlit_ui(type, message):
     if type == "status":
          st.session_state.status_message = message
     elif type == "progress":
          # Обновляем прогресс - message это количество найденных треков
          st.session_state.progress_value = min(message / 1000, 1.0) # Примерная шкала до 1000
          st.session_state.progress_text = f"Собрано {message} треков..."
     elif type == "caption":
          st.session_state.caption_message = message
     elif type == "info": # Используем для начальных сообщений
          status_placeholder.info(message)
     elif type == "warning":
          status_placeholder.warning(message)
     elif type == "error":
          status_placeholder.error(message)
     elif type == "success": # Используем для финального сообщения
         status_placeholder.success(message)

     # Обновляем плейсхолдеры из session_state
     if st.session_state.status_message: status_placeholder.info(st.session_state.status_message)
     if st.session_state.progress_text:
          progress_bar_placeholder.progress(st.session_state.progress_value)
          progress_text_placeholder.text(st.session_state.progress_text)
     if st.session_state.caption_message: caption_placeholder.caption(st.session_state.caption_message)


# Запуск сбора
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


    if not username.strip():
        st.warning("⚠️ Пожалуйста, введите имя пользователя SoundCloud.")
    else:
        profile_url = f"https://soundcloud.com/{username.strip()}/likes"
        st.markdown(f"🔗 Собираем лайки: [{profile_url}]({profile_url})")
        st.markdown(f"(Пауза: {scroll_wait} сек, Проверок конца: {max_wait_count})")

        driver = None
        try:
            # Проверяем, что функции действительно импортированы
            if 'setup_driver' not in globals() or 'scroll_and_collect' not in globals():
                 st.error("Критическая ошибка: Не удалось импортировать функции из src.")
                 st.stop()

            with st.spinner("Инициализация драйвера Chrome..."):
                driver = setup_driver() # setup_driver теперь вызывает st.stop() при критической ошибке

            # Запускаем сбор с передачей callback функции
            collected_list = scroll_and_collect(
                driver, profile_url, scroll_wait, max_wait_count, update_streamlit_ui
            )

            # Очищаем UI элементы после завершения scroll_and_collect
            status_placeholder.empty()
            progress_bar_placeholder.empty()
            progress_text_placeholder.empty()
            caption_placeholder.empty()

            if collected_list is not None:
                st.success(f"✅ Завершено! Собрано уникальных треков: {len(collected_list)}")
                if collected_list:
                    df_new = pd.DataFrame(collected_list, columns=["Title", "Link"])
                    st.dataframe(df_new, height=300)
                    try:
                         # Проверяем, что переменные пути импортированы
                         if 'DATA_DIR' not in globals() or 'CSV_FILE' not in globals():
                              st.error("Критическая ошибка: Не удалось импортировать пути из src.config.")
                              st.stop()

                         # Убедимся что папка data существует
                         os.makedirs(DATA_DIR, exist_ok=True)
                         # Сохраняем CSV
                         df_new.to_csv(CSV_FILE, index=False, encoding='utf-8')
                         # Получаем относительный путь для отображения
                         csv_display_path = os.path.relpath(CSV_FILE, project_root)
                         st.info(f"💾 Данные сохранены в `{csv_display_path}`.")
                         # Кнопка скачивания
                         csv_data = df_new.to_csv(index=False).encode('utf-8')
                         st.download_button(
                            label="⬇️ Скачать CSV", data=csv_data,
                            file_name=f"{username.strip()}_liked_tracks.csv", mime="text/csv"
                         )
                         st.markdown(f"➡️ Теперь можно запустить `python run_downloader.py` для скачивания.")
                    except Exception as e: st.error(f"Не удалось сохранить CSV: {e}")
                else: st.warning("Не найдено ни одного лайка.")
            else:
                 # Если scroll_and_collect вернул None (ошибка загрузки страницы)
                 st.error("Сбор лайков не удался из-за ошибки загрузки страницы.")

        except Exception as e: # Ловим ошибки от setup_driver или другие
            st.error(f"Произошла критическая ошибка: {e}")
            # Добавим вывод traceback для диагностики, если нужно
            # import traceback
            # st.error("Traceback:")
            # st.code(traceback.format_exc())
        finally:
            if driver:
                try:
                    driver.quit()
                    st.info("Драйвер Chrome закрыт.")
                except Exception as e:
                    st.warning(f"Не удалось корректно закрыть драйвер Chrome: {e}")