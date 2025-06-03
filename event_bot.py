import time
import sqlite3
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from config import TOKEN, DB_PATH, GROUP_CHAT_ID

bot = Bot(token=TOKEN)
previous_tickers = set()

def get_unique_tickers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT ticker FROM events")
    tickers = [row[0] for row in c.fetchall()]
    conn.close()
    return tickers

def show_available_coins(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_CHAT_ID:
        return

    tickers = get_unique_tickers()
    if not tickers:
        update.message.reply_text("⚠️ Пока нет доступных монет.")
        return

    keyboard = [
        [InlineKeyboardButton(ticker, callback_data=f"coin_{ticker}")]
        for ticker in tickers
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("💰 Доступные монеты:", reply_markup=reply_markup)

def handle_coin_button(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.message.chat.id != GROUP_CHAT_ID:
        return

    query.answer()
    data = query.data
    if data.startswith("coin_"):
        ticker = data.replace("coin_", "")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT date, time, exchange FROM events WHERE ticker = ?", (ticker,))
        rows = c.fetchall()
        conn.close()

        seen_exchanges = set()
        unique_events = []
        for date, time, exchange in rows:
            if exchange not in seen_exchanges:
                unique_events.append((date, time, exchange))
                seen_exchanges.add(exchange)

        if not unique_events:
            query.edit_message_text(
                text=f"🔎 Монета <b>{ticker}</b> пока не добавлялась ни на одну биржу.",
                parse_mode="HTML"
            )
            return

        message = f"📊 История добавлений монеты <b>{ticker}</b> на биржи:\n\n"
        for date, time, exchange in unique_events:
            message += f"📅 {date} в {time} — <b>{exchange}</b>\n"

        query.edit_message_text(text=message, parse_mode="HTML")

def start(update: Update, context: CallbackContext):
    if update.effective_chat.id != GROUP_CHAT_ID:
        return
    update.message.reply_text("✅ Бот активен в этой группе.")

def fetch_unsent_events(sent_ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM events ORDER BY rowid DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()

    new_events = []
    for row in rows:
        event_id = row[0]
        if event_id not in sent_ids:
            new_events.append({
                "id": row[0],
                "date": row[1],
                "time": row[2],
                "ticker": row[3],
                "type": row[4],
                "exchange": row[5],
                "pair": row[6],
                "pair_link": row[7],
            })
    return new_events[::-1]

def send_event(event):
    text = (
        f"🆕 <b>Добавлено новое событие:</b>\n"
        f"📅 <b>Дата:</b> {event['date']}\n"
        f"⏰ <b>Время:</b> {event['time']}\n"
        f"💱 <b>Пара:</b> {event['pair']}\n"
        f"📈 <b>Биржа:</b> {event['exchange']}\n"
        f"🔖 <b>Тип:</b> {event['type']}\n"
        f"🔗 <a href='{event['pair_link']}'>Ссылка на торговлю</a>"
    )
    try:
        bot.send_message(chat_id=GROUP_CHAT_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
        print(f"✅ Отправлено событие {event['id']} в группу")
    except Exception as e:
        print(f"❌ Ошибка при отправке события: {e}")

def notify_deleted_ticker(ticker):
    text = f"⚠️ Монета <b>{ticker}</b> была удалена из базы данных (возможно, устарела)."
    try:
        bot.send_message(chat_id=GROUP_CHAT_ID, text=text, parse_mode="HTML")
        print(f"📤 Уведомление об удалении {ticker} отправлено")
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления об удалении: {e}")

def notification_loop():
    sent_ids = set()
    global previous_tickers

    while True:
        try:
            new_events = fetch_unsent_events(sent_ids)
            for event in new_events:
                send_event(event)
                sent_ids.add(event["id"])

            current_tickers = set(get_unique_tickers())
            if previous_tickers:
                deleted = previous_tickers - current_tickers
                for ticker in deleted:
                    notify_deleted_ticker(ticker)

            previous_tickers = current_tickers

        except Exception as e:
            print("⚠️ Ошибка в цикле отправки:", e)

        time.sleep(30)

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("coins", show_available_coins))
    dp.add_handler(CallbackQueryHandler(handle_coin_button))

    updater.start_polling()
    print("✅ Бот запущен.")

    notification_loop()

if __name__ == "__main__":
    main()

