import os
import asyncio
import mysql.connector
from pyrogram import Client, filters, idle
from pyrogram.types import Message

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
DB_CONFIG = {
    "host": "localhost",
    "user": "your_user",
    "password": "your_password",
    "database": "gift_db"
}

conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor(dictionary=True)

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    receiver_id INT,
    gift_id VARCHAR(255) NOT NULL,
    status ENUM('pending', 'sent', 'received') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
)""")
conn.commit()

app = Client("storozh", API_ID, API_HASH)

async def get_file_id(message: Message) -> str:
    if message.document:
        return message.document.file_id
    elif message.photo:
        return message.photo.file_id
    elif message.video:
        return message.video.file_id
    elif message.audio:
        return message.audio.file_id
    elif message.voice:
        return message.voice.file_id
    return None

@app.on_message(filters.private & ~filters.me)
async def handle_message(client, message: Message):
    user_id = message.from_user.id

    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (telegram_id) VALUES (%s)", (user_id,))
        conn.commit()

    file_id = await get_file_id(message)
    if file_id:
        cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        sender_id = cursor.fetchone()["id"]
        cursor.execute(
            "INSERT INTO gifts (sender_id, file_id) VALUES (%s, %s)",
            (sender_id, file_id)
        )
        conn.commit()
        await message.reply("Подарок сохранён! Он будет отправлен получателю после проверки.")

async def gift_sender():
    while True:
        await asyncio.sleep(60)  # Check every minute

        cursor.execute("""
            SELECT g.id, g.file_id, u.telegram_id as receiver_tg_id
            FROM gifts g
            JOIN users u ON g.receiver_id = u.id
            WHERE g.status = 'pending'
        """)

        for gift in cursor.fetchall():
            try:
                await app.send_document(
                    chat_id=gift["receiver_tg_id"],
                    document=gift["file_id"]
                )
                cursor.execute(
                    "UPDATE gifts SET status = 'sent' WHERE id = %s",
                    (gift["id"],)
                )
                conn.commit()
            except Exception as e:
                print(f"Error sending gift {gift['id']}: {e}")

async def main():
    await app.start()
    asyncio.create_task(gift_sender())
    print("Bot started!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())