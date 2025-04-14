import os
import threading
import time

from dotenv import load_dotenv
from pyrogram import Client, filters, idle

from database.setup import db_cursor, db_conn

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

app = Client("storozh", api_id=API_ID, api_hash=API_HASH)


@app.on_message(filters.private)
def handle_private_message(client, message):
    user_id = message.from_user.id
    try:
        db_cursor.execute("INSERT IGNORE INTO users (telegram_id) VALUES (%s)", (user_id,))
        db_conn.commit()
    except Exception as e:
        print(f"[DB] Ошибка при сохранении пользователя {user_id}: {e}")


def process_pending_gifts():
    while True:
        try:
            db_cursor.execute("SELECT id, receiver_id, file_id FROM gifts WHERE status = 'pending'")
            pending_gifts = db_cursor.fetchall()
            for gift_id, user_id, file_id in pending_gifts:
                db_cursor.execute("SELECT telegram_id FROM users WHERE id = %s", (user_id,))
                result = db_cursor.fetchone()
                if result:
                    receiver_tg_id = result[0]
                    try:
                        app.send_document(receiver_tg_id, file_id)
                        db_cursor.execute("UPDATE gifts SET status = 'sent' WHERE id = %s", (gift_id,))
                        db_conn.commit()
                        print(f"[GIFT] Подарок ID {gift_id} отправлен пользователю {receiver_tg_id}")
                    except Exception as send_err:
                        print(f"[GIFT] Ошибка отправки файла пользователю {receiver_tg_id}: {send_err}")
        except Exception as e:
            print(f"[DB] Ошибка при проверке подарков: {e}")
        time.sleep(60)


if __name__ == "__main__":
    app.start()
    print("Userbot запущен. Ожидание личных сообщений и проверка подарков...")
    gift_thread = threading.Thread(target=process_pending_gifts, daemon=True)
    gift_thread.start()
    try:
        idle()
    finally:
        app.stop()
        db_cursor.close()
        db_conn.close()
        print("Userbot остановлен.")
