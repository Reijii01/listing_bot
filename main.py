from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlite3
import time
import random
import tempfile
from datetime import datetime, timedelta



URL = "https://listedon.org/ru"
DB_PATH = "events.db"

# Настройки Selenium
options = Options()
options.add_argument("--headless")  # Без GUI
options.add_argument("--no-sandbox")  # Нужно в Docker и без GUI
options.add_argument("--disable-dev-shm-usage")  # Избежать проблем с памятью
options.add_argument("--disable-gpu")  # Отключить GPU


def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        date TEXT,
        time TEXT,
        ticker TEXT,
        type TEXT,
        exchange TEXT,
        pair TEXT,
        pair_link TEXT,
        last_seen TEXT
    )''')
    conn.commit()
    conn.close()

def fetch_events():
    # Создаём драйвер внутри функции
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        delay = random.uniform(2, 5)
        print(f"⏳ Задержка перед запросом: {delay:.2f} сек")
        time.sleep(delay)

        driver.get(URL)
        print("✅ Страница загружена. Длина source:", len(driver.page_source))
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.item")))
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.item")
            print(f"🔍 Найдено строк: {len(rows)}")
        except Exception as e:
            print("❌ Не удалось найти строки с событиями:", e)
            rows = []
        events = []

        for row in rows:
            try:
                event_id = row.get_attribute("id")
                date_raw = row.find_element(By.CSS_SELECTOR, "td.date").text
                time_str = row.find_element(By.CSS_SELECTOR, "td.date .time").text
                date_only = date_raw.replace(time_str, "").strip()

                ticker = row.find_element(By.CSS_SELECTOR, "strong a").text.strip()
                type_ = row.find_element(By.CSS_SELECTOR, "td.type").text.strip()
                exchange = row.find_elements(By.CSS_SELECTOR, "td")[3].find_element(By.TAG_NAME, "a").text.strip()
                pair_tag = row.find_element(By.CSS_SELECTOR, "td .pair")
                pair = pair_tag.text.strip()
                pair_link = pair_tag.get_attribute("href")

                events.append({
                    "id": event_id,
                    "date": date_only,
                    "time": time_str,
                    "ticker": ticker,
                    "type": type_,
                    "exchange": exchange,
                    "pair": pair,
                    "pair_link": pair_link
                })
            except Exception as e:
                print(f"⚠️ Ошибка при разборе строки: {e}")
        return events
    except Exception as e:
        print(f"❌ Ошибка при загрузке страницы: {e}")
        return []
    finally:
        driver.quit()  # Драйвер гарантированно закроется даже при ошибке

def save_new_events(events):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.now().isoformat()

    for e in events:
        c.execute("SELECT 1 FROM events WHERE id = ?", (e["id"],))
        if not c.fetchone():
            print("🆕 Новое событие найдено:", e)
            c.execute('''INSERT INTO events (id, date, time, ticker, type, exchange, pair, pair_link, last_seen)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (e["id"], e["date"], e["time"], e["ticker"], e["type"],
                       e["exchange"], e["pair"], e["pair_link"], now_str))
        else:
            # Обновляем дату последнего появления
            c.execute("UPDATE events SET last_seen = ? WHERE id = ?", (now_str, e["id"]))

    conn.commit()
    conn.close()



def delete_old_tickers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Получаем текущую временную метку
    two_weeks_ago = (datetime.now() - timedelta(days=14)).isoformat()

    # Получаем тикеры и дату их последнего упоминания
    c.execute("SELECT ticker, MAX(last_seen) FROM events GROUP BY ticker")
    tickers = c.fetchall()

    for ticker, last_seen in tickers:
        if last_seen < two_weeks_ago:
            print(f"🗑️ Удаление устаревшего тикера: {ticker}")
            c.execute("DELETE FROM events WHERE ticker = ?", (ticker,))

    conn.commit()
    conn.close()

def main_loop():
    create_db()
    while True:
        try:
            print(f"[{datetime.now()}] Проверка событий...")
            events = fetch_events()
            save_new_events(events)
            delete_old_tickers()
        except Exception as e:
            print("❌ Ошибка в цикле:", e)
        time.sleep(300)

if __name__ == "__main__":
    main_loop()

