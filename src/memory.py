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
    con.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def log_message(user_id: int, message: str):
    from datetime import datetime
    con = _conn()
    con.execute(
        "INSERT INTO activity_log (user_id, message, timestamp) VALUES (?, ?, ?)",
        (user_id, message[:500], datetime.now().isoformat()),
    )
    con.commit()


def get_user_logs(user_id: int = None, limit: int = 20) -> list[dict]:
    con = _conn()
    if user_id:
        rows = con.execute(
            "SELECT user_id, message, timestamp FROM activity_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT user_id, message, timestamp FROM activity_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"user_id": r[0], "message": r[1], "timestamp": r[2]} for r in rows]


def load(user_id: int) -> list[dict]:
    con = _conn()
    row = con.execute("SELECT history FROM chat_history WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        history = json.loads(row[0])
        # Validate and clean on load — auto-fix any corruption before it hits Claude
        cleaned = _clean_history(history)
        if len(cleaned) != len(history):
            # Save the cleaned version back
            con.execute(
                "INSERT OR REPLACE INTO chat_history (user_id, history) VALUES (?, ?)",
                (user_id, json.dumps(cleaned)),
            )
            con.commit()
        return cleaned
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


def _is_tool_result_block(content) -> bool:
    if isinstance(content, list):
        return any(
            (c.get("type") == "tool_result" if isinstance(c, dict) else False)
            for c in content
        )
    return False


def _clean_history(history: list[dict]) -> list[dict]:
    """
    Remove any incomplete or orphaned tool_use/tool_result pairs from history.
    Does a full forward pass so corruption anywhere (not just the tail) is caught.
    """
    # Collect tool_use IDs from all assistant messages
    tool_use_ids: set[str] = set()
    for msg in history:
        if msg["role"] == "assistant":
            content = msg["content"]
            if isinstance(content, list):
                for block in content:
                    b = block if isinstance(block, dict) else block.model_dump()
                    if b.get("type") == "tool_use":
                        tool_use_ids.add(b["id"])

    clean = []
    i = 0
    while i < len(history):
        msg = history[i]
        role = msg["role"]
        content = msg["content"]

        if role == "user" and _is_tool_result_block(content):
            # Only keep if ALL tool_result IDs have a matching tool_use
            if isinstance(content, list):
                ids = [
                    (b if isinstance(b, dict) else b.model_dump()).get("tool_use_id")
                    for b in content
                    if (b if isinstance(b, dict) else b.model_dump()).get("type") == "tool_result"
                ]
                if all(tid in tool_use_ids for tid in ids):
                    clean.append(msg)
                # else: orphaned tool_result block — skip it
            i += 1
            continue

        if role == "assistant" and _has_tool_use(content):
            # Peek ahead: must be followed by a matching tool_result user message
            if i + 1 < len(history) and _is_tool_result_block(history[i + 1]["content"]):
                clean.append(msg)
            # else: tool_use with no following tool_result — drop it
            i += 1
            continue

        clean.append(msg)
        i += 1

    # Final tail cleanup: drop trailing tool_use assistant or orphaned tool_result user
    while clean and clean[-1]["role"] == "assistant" and _has_tool_use(clean[-1]["content"]):
        clean.pop()
    while clean and clean[-1]["role"] == "user" and _is_tool_result_block(clean[-1]["content"]):
        clean.pop()
        if clean and clean[-1]["role"] == "assistant" and _has_tool_use(clean[-1]["content"]):
            clean.pop()

    return clean


def save(user_id: int, history: list[dict]):
    # Serialize content that may contain Anthropic SDK objects
    serializable = []
    for msg in history:
        content = _serialize_content(msg["content"])
        serializable.append({"role": msg["role"], "content": content})

    serializable = _clean_history(serializable)
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
