
import sqlite3
import json

DB_NAME = "chat_history.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                thread_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (thread_id)
                    REFERENCES conversations(thread_id)
            )
        """)


def create_conversation(thread_id, user_id, title):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations
            (thread_id, user_id, title)
            VALUES (?, ?, ?)
            """,
            (thread_id, user_id, title)
        )


def get_conversations(user_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT thread_id, title
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC, rowid DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def save_message(thread_id, role, content):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages
            (thread_id, role, content)
            VALUES (?, ?, ?)
            """,
            (thread_id, role, content)
        )


def get_messages(thread_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE thread_id = ?
            ORDER BY id
            """,
            (thread_id,)
        ).fetchall()

        return [dict(row) for row in rows]
