import sqlite3
from datetime import datetime

DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, join_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids
