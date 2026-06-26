"""
Per-user conversation history stored in SQLite.
Keeps the last N turns per Telegram user_id.
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "assistant.db")
MAX_HISTORY = 40  # max message objects per user


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            user_id INTEGER PRIMARY KEY,
            history TEXT NOT NULL DEFAULT '[]'
        )
    """)
    con.commit()
    return con


def load(user_id: int) -> list[dict]:
    con = _conn()
    row = con.execute("SELECT history FROM chat_history WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return json.loads(row[0])
    return []


def _serialize_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return [c if isinstance(c, dict) else c.model_dump() for c in content]
    return str(content)


def _has_tool_use(content) -> bool:
    if isinstance(content, list):
        return any(
            (c.get("type") == "tool_use" if isinstance(c, dict) else getattr(c, "type", None) == "tool_use")
            for c in content
        )
    return False


def save(user_id: int, history: list[dict]):
    # Serialize content that may contain Anthropic SDK objects
    serializable = []
    for msg in history:
        content = _serialize_content(msg["content"])
        serializable.append({"role": msg["role"], "content": content})

    # Drop any trailing assistant message that ends with tool_use (no result pair saved yet)
    # This prevents corrupted history when a tool call fails mid-flight
    while serializable and serializable[-1]["role"] == "assistant" and _has_tool_use(serializable[-1]["content"]):
        serializable.pop()
        if serializable and serializable[-1]["role"] == "user":
            last_content = serializable[-1]["content"]
            if isinstance(last_content, list) and any(
                (c.get("type") == "tool_result" if isinstance(c, dict) else False)
                for c in last_content
            ):
                serializable.pop()

    # Trim to avoid unbounded growth
    serializable = serializable[-MAX_HISTORY:]

    con = _conn()
    con.execute(
        "INSERT OR REPLACE INTO chat_history (user_id, history) VALUES (?, ?)",
        (user_id, json.dumps(serializable)),
    )
    con.commit()


def clear(user_id: int):
    con = _conn()
    con.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    con.commit()
