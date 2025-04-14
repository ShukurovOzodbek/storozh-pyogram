import os
import threading
import time

from dotenv import load_dotenv
from pyrogram import Client, filters, idle

from database.setup import db_cursor, db_conn

load_dotenv()

API_ID = os.getenv("APP_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

app = Client("storozh", api_id=API_ID, api_hash=API_HASH, phone_number=PHONE_NUMBER)


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
        # for gift in app.get_available_gifts():
        #     print(gift)

        try:
            db_cursor.execute("SELECT id, user_id, gift_id FROM gifts WHERE status = 'pending'")
            pending_gifts = db_cursor.fetchall()
            for gift in pending_gifts:
                db_cursor.execute("SELECT telegram_id FROM users WHERE id = %s", (gift.get("user_id"),))
                result = db_cursor.fetchone()
                if result:
                    receiver_tg_id = result["telegram_id"]
                    try:
                        app.send_gift(receiver_tg_id, gift_id=int(gift.get("gift_id")), hide_my_name=True)
                        db_cursor.execute("UPDATE gifts SET status = 'sent' WHERE id = %s", (gift.get("id"),))
                        db_conn.commit()
                        print(f"[GIFT] Подарок ID {gift.get("gift_id")} отправлен пользователю {receiver_tg_id}")
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
