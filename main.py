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


@app.on_message(filters.private & filters.star_gift & filters.incoming)
async def handle_gift_message(client, message):
    user_id = message.from_user.id
    if user_id != app.me.id:
        db_cursor.execute("SELECT id FROM users WHERE telegram_id = (%s)", (user_id,))
        user = db_cursor.fetchone()

        if not user:
            try:
                db_cursor.execute("INSERT IGNORE INTO users (telegram_id) VALUES (%s)", (user_id,))
                db_conn.commit()
            except Exception as e:
                print(f"[DB] Ошибка при сохранении пользователя {user_id}: {e}")

        if message.gift.owner:
            if message.gift.owner.id == app.me.id:
                query = """
                    INSERT INTO gifts (message_id, gift_id)
                    VALUES (%s, %s)
                    """
                db_cursor.execute(query, (message.id, message.gift.id,))
                db_conn.commit()
        else:
            query = """
                INSERT INTO gifts (gift_id)
                VALUES (%s)
                """
            db_cursor.execute(query, (message.gift.id,))
            db_conn.commit()


@app.on_message(filters.private & filters.incoming)
async def handle_private_message(client, message):
    user_id = message.from_user.id
    try:
        db_cursor.execute("INSERT IGNORE INTO users (telegram_id) VALUES (%s)", (user_id,))
        db_conn.commit()
        print(f"[DB] Пользователь {user_id} сохранен: {e}")
    except Exception as e:
        print(f"[DB] Ошибка при сохранении пользователя {user_id}: {e}")


def process_pending_gifts():
    while True:
        try:
            db_cursor.execute("SELECT id, user_id, gift_id FROM gifts_to_send WHERE status = 'pending'")
            pending_gifts = db_cursor.fetchall()
            for gift in pending_gifts:
                db_cursor.execute("SELECT telegram_id FROM users WHERE id = %s", (gift.get("user_id"),))
                user = db_cursor.fetchone()

                db_cursor.execute("SELECT message_id, gift_id FROM gifts WHERE id = %s",
                                  (gift.get("gift_id"),))
                result = db_cursor.fetchone()
                if user:
                    receiver_tg_id = user.get("telegram_id")
                    gift_tg_id = result.get("gift_id")
                    message_id = result.get("message_id")
                    try:
                        if message_id is None:
                            app.send_gift(receiver_tg_id, gift_id=int(result.get("gift_id")), hide_my_name=True)
                            print(f"[GIFT] Подарок ID {gift_tg_id} отправлен пользователю {receiver_tg_id}")
                        else:
                            app.transfer_gift(message_id=result.get("message_id"), to_chat_id=receiver_tg_id)
                            db_conn.commit()
                            print(f"[GIFT] Подарок ID {gift_tg_id} отправлен пользователю {receiver_tg_id}")

                        update_query = """UPDATE gifts_to_send SET status = 'sent' WHERE id = %s"""
                        db_cursor.execute(update_query, (gift.get("id"),))
                        db_conn.commit()
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
