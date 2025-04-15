import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "github_4",
    "database": "storozh"
}

db_conn = mysql.connector.connect(**DB_CONFIG)
db_cursor = db_conn.cursor(dictionary=True)

db_cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")

db_cursor.execute("""
CREATE TABLE IF NOT EXISTS gifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT,
    gift_id BIGINT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")

db_cursor.execute("""
CREATE TABLE IF NOT EXISTS gifts_to_send (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    gift_id INT NOT NULL UNIQUE,
    status ENUM('pending', 'sent', 'received') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gift_id) REFERENCES gifts(id)
)""")
db_conn.commit()
