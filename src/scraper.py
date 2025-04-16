# -*- coding: utf-8 -*-
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Настройка логгера
logger = logging.getLogger(__name__)

def setup_driver():
    """Настраивает и возвращает Selenium WebDriver для Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = None
    try:
        logger.info("Инициализация Chrome Driver Manager...")
        # Оборачиваем установку драйвера для лучшей диагностики
        try:
            service = Service(ChromeDriverManager().install())
        except ValueError as ve:
             logger.critical(f"Ошибка WebDriver Manager (возможно, проблема с сетью или версией): {ve}")
             raise # Передаем выше для обработки Streamlit
        except Exception as install_err:
            logger.critical(f"Неожиданная ошибка при установке ChromeDriver: {install_err}", exc_info=True)
            raise

        logger.info("Запуск Chrome Driver...")
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("Драйвер успешно запущен.")
        return driver
    except WebDriverException as e:
        logger.critical(f"Ошибка Selenium WebDriver при запуске Chrome: {e}. Убедитесь, что Chrome установлен и доступен.")
        if driver: driver.quit()
        raise
    except Exception as e:
        logger.critical(f"Неожиданная ошибка при настройке драйвера: {e}", exc_info=True)
        if driver: driver.quit()
        raise

# --- ИЗМЕНЕНО ОПРЕДЕЛЕНИЕ ФУНКЦИИ ---
def scroll_and_collect(driver, profile_url, scroll_wait_time, max_consecutive_same_height, progress_callback=None, max_tracks=0):
    """
    Загружает страницу, скроллит и собирает ссылки на треки.
    progress_callback - функция для обновления UI (например, Streamlit).
    max_tracks - максимальное количество треков для сбора (0 - без лимита).
    """
    logger.info(f"Загрузка страницы: {profile_url}")
    if progress_callback: progress_callback("info", f"Загрузка страницы: {profile_url}...")

    try:
        driver.get(profile_url)
        time.sleep(5) # Ожидание начальной загрузки (можно увеличить при медленной сети)
    except WebDriverException as e:
        logger.error(f"Не удалось загрузить страницу {profile_url}. Ошибка: {e}")
        if progress_callback: progress_callback("error", f"Не удалось загрузить страницу. Ошибка: {e}")
        return None # Сигнализируем об ошибке

    collected_data = {} # Словарь {link: title} для автоматической уникальности ссылок
    last_height = driver.execute_script("return document.body.scrollHeight")
    consecutive_same_height = 0
    scroll_count = 0
    reached_limit = False # Флаг для отслеживания причины остановки

    logger.info("Начало скроллинга и сбора лайков...")
    limit_info = f" (лимит: {max_tracks})" if max_tracks > 0 else ""
    if progress_callback: progress_callback("info", f"Начинаем скроллинг и сбор лайков{limit_info}...")

    # Основной цикл скроллинга
    while True:
        scroll_count += 1
        current_found = len(collected_data)
        if progress_callback: progress_callback("status", f"Скролл #{scroll_count}. Найдено: {current_found}")

        try:
            # Прокрутка
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Динамическое ожидание вместо фиксированного time.sleep
            # WebDriverWait(driver, scroll_wait_time * 2).until(
            #     lambda d: d.execute_script("return document.readyState") == "complete"
            # ) # Можно поэкспериментировать с WebDriverWait, но time.sleep проще
            time.sleep(scroll_wait_time)

            # --- Поиск элементов ---
            selectors = [
                'div.soundList__item div.sound__header a.soundTitle__title', # Основной селектор
                'li.soundList__item a.soundTitle__title' # Запасной селектор
            ]
            track_elements = []
            for selector in selectors:
                 try:
                      # Ищем видимые элементы, чтобы избежать скрытых/старых
                      elements = driver.find_elements(By.CSS_SELECTOR, selector)
                      # Фильтруем только видимые, если возможно (может замедлить)
                      # track_elements.extend([el for el in elements if el.is_displayed()])
                      track_elements.extend(elements) # Пока берем все
                 except NoSuchElementException: continue
                 # Если нашли элементы по одному селектору, можно прекратить поиск по другим
                 # if track_elements: break

            if not track_elements and scroll_count > 1: # Предупреждение, если после первого скролла ничего не найдено
                logger.warning(f"Скролл #{scroll_count}: треки не найдены с использованием селекторов.")
                # Можно добавить дополнительную паузу или проверку здесь
                # time.sleep(scroll_wait_time * 2)


            # --- Извлечение данных ---
            newly_found_count = 0
            for t_element in track_elements:
                 link = t_element.get_attribute('href')
                 title_span = None
                 title = None
                 try:
                     title_span = t_element.find_element(By.CSS_SELECTOR, 'span')
                     if title_span: title = title_span.text.strip()
                 except NoSuchElementException:
                     try: title = t_element.text.strip()
                     except Exception: pass

                 # Добавляем только если есть ссылка и название, и ссылки еще нет в словаре
                 if link and title and link not in collected_data:
                     collected_data[link] = title
                     newly_found_count += 1
                     # Оптимизация: если лимит задан, проверяем сразу после добавления нового
                     # --- ДОБАВЛЕНО: Проверка лимита сразу после нахождения нового трека ---
                     if max_tracks > 0 and len(collected_data) >= max_tracks:
                         logger.info(f"Достигнут лимит в {max_tracks} треков ({len(collected_data)} собрано). Остановка сбора.")
                         if progress_callback:
                             progress_callback("progress", len(collected_data))
                             progress_callback("success", f"Достигнут лимит в {max_tracks} треков.")
                         reached_limit = True # Устанавливаем флаг
                         break # Выход из цикла for t_element
                     # --- КОНЕЦ ПРОВЕРКИ ЛИМИТА ---


            # Если вышли из цикла for из-за лимита, выходим и из while
            if reached_limit:
                break

            if newly_found_count > 0:
                 logger.debug(f"Скролл #{scroll_count}: Найдено новых {newly_found_count}")
                 if progress_callback: progress_callback("progress", len(collected_data))

            # --- Проверка конца страницы ---
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                consecutive_same_height += 1
                logger.debug(f"Высота не изменилась ({consecutive_same_height}/{max_consecutive_same_height})")
                if progress_callback: progress_callback("caption", f"Проверка конца страницы ({consecutive_same_height}/{max_consecutive_same_height})...")
                if consecutive_same_height >= max_consecutive_same_height:
                    logger.info("Достигнут конец страницы.")
                    if progress_callback: progress_callback("success", "Достигнут конец страницы.")
                    break # Выход из цикла while
            else:
                last_height = new_height
                consecutive_same_height = 0 # Сбрасываем счетчик

        # --- Обработка исключений цикла ---
        except (NoSuchElementException, TimeoutException) as e:
            logger.warning(f"Ошибка на скролле #{scroll_count} при поиске элементов: {e}. Продолжаем.")
            if progress_callback: progress_callback("warning", f"Ошибка на скролле #{scroll_count}. Продолжаем.")
            time.sleep(scroll_wait_time) # Доп. пауза при ошибке
            continue
        except WebDriverException as e:
            # Обработка ошибок, связанных с драйвером/браузером
            if "disconnected" in str(e) or "target window already closed" in str(e):
                 logger.error(f"Критическая ошибка Selenium: Браузер был закрыт или потерял соединение.")
                 if progress_callback: progress_callback("error", "Браузер закрыт или соединение потеряно.")
            else:
                 logger.error(f"Критическая ошибка Selenium на скролле #{scroll_count}: {e}")
                 if progress_callback: progress_callback("error", f"Ошибка Selenium: {e}")
            break # Прерываем цикл при критической ошибке
        except Exception as e:
            logger.error(f"Неожиданная ошибка на скролле #{scroll_count}: {e}", exc_info=True)
            if progress_callback: progress_callback("error", f"Неожиданная ошибка: {e}")
            break

    # Преобразование словаря {link: title} в список кортежей [(Title, Link)]
    result_list = [(v, k) for k, v in collected_data.items()]

    # --- ИЗМЕНЕНО: Обновление финального сообщения в логе ---
    final_message = f"Сбор завершен. Собрано {len(result_list)} уникальных треков."
    if reached_limit: # Проверяем флаг
        final_message += f" (Достигнут лимит: {max_tracks})"
    elif consecutive_same_height >= max_consecutive_same_height:
         final_message += " (Достигнут конец страницы)"
    else:
         final_message += " (Остановлено по другой причине?)" # На всякий случай

    logger.info(final_message)
    return result_list