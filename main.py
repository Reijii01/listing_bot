from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import sqlite3
import time
from datetime import datetime, timedelta



URL = "https://listedon.org/ru"
DB_PATH = "events.db"

# Настройки Selenium
options = Options()
options.add_argument("--headless")
options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
driver = webdriver.Chrome(options=options)

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
    driver.get(URL)
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.item")
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
        time.sleep(120)

if __name__ == "__main__":
    main_loop()

