"""
Allowed user management — persisted in SQLite.
The owner (OWNER_ID) is always allowed and is the only one who can add/remove users.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "assistant.db")
OWNER_ID = 7760759598


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS allowed_users (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            note TEXT DEFAULT ''
        )
    """)
    con.commit()
    return con


def is_allowed(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    con = _conn()
    row = con.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,)).fetchone()
    return row is not None


def add_user(user_id: int, added_by: int, note: str = "") -> str:
    if user_id == OWNER_ID:
        return "That's the owner — already has full access."
    con = _conn()
    con.execute(
        "INSERT OR REPLACE INTO allowed_users (user_id, added_by, note) VALUES (?, ?, ?)",
        (user_id, added_by, note),
    )
    con.commit()
    return f"User {user_id} added."


def remove_user(user_id: int) -> str:
    if user_id == OWNER_ID:
        return "Cannot remove the owner."
    con = _conn()
    con.execute("DELETE FROM allowed_users WHERE user_id = ?", (user_id,))
    con.commit()
    return f"User {user_id} removed."


def list_users() -> list[dict]:
    con = _conn()
    rows = con.execute("SELECT user_id, note FROM allowed_users").fetchall()
    return [dict(r) for r in rows]
