import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "assistant.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def save_note(title: str, content: str, tags: str = "") -> str:
    """Save a note or piece of research to the local database."""
    con = _conn()
    con.execute(
        "INSERT INTO notes (title, content, tags, created_at) VALUES (?, ?, ?, ?)",
        (title, content, tags, datetime.now().isoformat()),
    )
    con.commit()
    return f"Note '{title}' saved."


def list_notes(tag: str = "") -> list[dict]:
    """List saved notes, optionally filtered by tag."""
    con = _conn()
    if tag:
        rows = con.execute(
            "SELECT id, title, tags, created_at FROM notes WHERE tags LIKE ? ORDER BY created_at DESC",
            (f"%{tag}%",),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT id, title, tags, created_at FROM notes ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]


def get_note(note_id: int) -> dict:
    """Retrieve the full content of a note by its ID."""
    con = _conn()
    row = con.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return dict(row) if row else {}


def delete_note(note_id: int) -> str:
    """Delete a note by ID."""
    con = _conn()
    con.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    con.commit()
    return f"Note {note_id} deleted."
