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
        service = Service(ChromeDriverManager().install())
        logger.info("Запуск Chrome Driver...")
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("Драйвер успешно запущен.")
        return driver
    except ValueError as e:
        logger.critical(f"Ошибка инициализации WebDriver Manager: {e}. Проверьте сеть/версию.")
        raise # Передаем исключение выше для обработки в UI
    except WebDriverException as e:
        logger.critical(f"Ошибка Selenium WebDriver: {e}. Убедитесь, что Chrome установлен.")
        if driver: driver.quit() # Попытка закрыть драйвер, если он создался частично
        raise
    except Exception as e:
        logger.critical(f"Неожиданная ошибка при настройке драйвера: {e}", exc_info=True)
        if driver: driver.quit()
        raise

def scroll_and_collect(driver, profile_url, scroll_wait_time, max_consecutive_same_height, progress_callback=None):
    """
    Загружает страницу, скроллит и собирает ссылки на треки.
    progress_callback - функция для обновления UI (например, Streamlit).
    """
    logger.info(f"Загрузка страницы: {profile_url}")
    if progress_callback: progress_callback("info", f"Загрузка страницы: {profile_url}")

    try:
        driver.get(profile_url)
        time.sleep(5) # Ожидание начальной загрузки
    except WebDriverException as e:
        logger.error(f"Не удалось загрузить страницу {profile_url}. Ошибка: {e}")
        if progress_callback: progress_callback("error", f"Не удалось загрузить страницу. Ошибка: {e}")
        return None # Сигнализируем об ошибке

    collected_data = {} # Словарь {link: title}
    last_height = driver.execute_script("return document.body.scrollHeight")
    consecutive_same_height = 0
    scroll_count = 0

    logger.info("Начало скроллинга и сбора лайков...")
    if progress_callback: progress_callback("info", "Начинаем скроллинг и сбор лайков...")

    # Основной цикл скроллинга
    while True:
        scroll_count += 1
        current_found = len(collected_data)
        if progress_callback: progress_callback("status", f"Скролл #{scroll_count}. Найдено: {current_found}")

        try:
            # Прокрутка
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_wait_time) # Ожидание

            # --- Поиск элементов ---
            # Селекторы могут потребовать обновления при изменении SoundCloud
            selectors = [
                'div.soundList__item div.sound__header a.soundTitle__title', # Основной
                'li.soundList__item a.soundTitle__title' # Запасной
            ]
            track_elements = []
            for selector in selectors:
                 try:
                      elements = driver.find_elements(By.CSS_SELECTOR, selector)
                      if elements:
                           track_elements.extend(elements)
                 except NoSuchElementException: continue

            if not track_elements and scroll_count > 1:
                logger.warning(f"Скролл #{scroll_count}: треки не найдены.")
                if progress_callback: progress_callback("warning", f"Скролл #{scroll_count}: треки не найдены.")

            # --- Извлечение данных ---
            newly_found_count = 0
            for t_element in track_elements:
                 link = t_element.get_attribute('href')
                 title_span = None
                 title = None
                 try: # Ищем span внутри ссылки для текста
                     title_span = t_element.find_element(By.CSS_SELECTOR, 'span')
                     if title_span: title = title_span.text.strip()
                 except NoSuchElementException:
                     # Если span не найден, попробуем взять текст самой ссылки (менее надежно)
                     try: title = t_element.text.strip()
                     except Exception: pass # Игнорируем ошибки получения текста

                 if link and title and link not in collected_data:
                     collected_data[link] = title
                     newly_found_count += 1

            if newly_found_count > 0:
                 logger.debug(f"Скролл #{scroll_count}: Найдено новых {newly_found_count}")
                 if progress_callback: progress_callback("progress", len(collected_data)) # Обновляем прогресс

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
            logger.warning(f"Ошибка на скролле #{scroll_count}: {e}. Продолжаем.")
            if progress_callback: progress_callback("warning", f"Ошибка на скролле #{scroll_count}. Продолжаем.")
            continue
        except WebDriverException as e:
            logger.error(f"Критическая ошибка Selenium на скролле #{scroll_count}: {e}")
            if progress_callback: progress_callback("error", f"Ошибка Selenium: {e}")
            break # Прерываем цикл
        except Exception as e:
            logger.error(f"Неожиданная ошибка на скролле #{scroll_count}: {e}", exc_info=True)
            if progress_callback: progress_callback("error", f"Неожиданная ошибка: {e}")
            break

    # Преобразование в список кортежей [(Title, Link)]
    result_list = list(collected_data.items())
    # Меняем местами для формата [(Title, Link)]
    result_list = [(v, k) for k, v in result_list]

    logger.info(f"Сбор завершен. Собрано {len(result_list)} уникальных треков.")
    return result_list