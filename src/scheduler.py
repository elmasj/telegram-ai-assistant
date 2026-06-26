"""
Persistent task scheduler — stores scheduled jobs in SQLite so they
survive bot restarts, and fires them via APScheduler at the right time.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "assistant.db")

_scheduler: AsyncIOScheduler = None
_send_fn = None  # injected from bot.py: async def send(chat_id, text)


def init(scheduler: AsyncIOScheduler, send_fn):
    global _scheduler, _send_fn
    _scheduler = scheduler
    _send_fn = send_fn
    _create_table()
    _restore_jobs()


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            run_at TEXT NOT NULL,
            fired INTEGER DEFAULT 0
        )
    """)
    con.commit()
    return con


def _create_table():
    _conn()


def schedule_task(user_id: int, prompt: str, run_at: datetime) -> int:
    """Save a task to DB and register it with APScheduler. Returns task id."""
    con = _conn()
    cur = con.execute(
        "INSERT INTO scheduled_tasks (user_id, prompt, run_at) VALUES (?, ?, ?)",
        (user_id, prompt, run_at.isoformat()),
    )
    con.commit()
    task_id = cur.lastrowid
    _register(task_id, user_id, prompt, run_at)
    return task_id


def list_tasks(user_id: int) -> list[dict]:
    con = _conn()
    rows = con.execute(
        "SELECT id, prompt, run_at FROM scheduled_tasks WHERE user_id = ? AND fired = 0 ORDER BY run_at",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def cancel_task(task_id: int) -> bool:
    con = _conn()
    con.execute("UPDATE scheduled_tasks SET fired = 1 WHERE id = ?", (task_id,))
    con.commit()
    try:
        _scheduler.remove_job(f"task_{task_id}")
    except Exception:
        pass
    return True


def _register(task_id: int, user_id: int, prompt: str, run_at: datetime):
    if run_at <= datetime.now():
        return
    _scheduler.add_job(
        _fire,
        trigger=DateTrigger(run_date=run_at),
        args=[task_id, user_id, prompt],
        id=f"task_{task_id}",
        replace_existing=True,
    )


async def _fire(task_id: int, user_id: int, prompt: str):
    from src import agent, memory
    logger.info(f"Firing scheduled task {task_id} for user {user_id}: {prompt}")
    try:
        history = memory.load(user_id)
        reply, history = agent.chat(history, prompt)
        memory.save(user_id, history)
        await _send_fn(user_id, reply)
    except Exception as e:
        logger.exception(f"Scheduled task {task_id} failed")
        await _send_fn(user_id, f"Scheduled task failed: {e}")
    finally:
        con = _conn()
        con.execute("UPDATE scheduled_tasks SET fired = 1 WHERE id = ?", (task_id,))
        con.commit()


def _restore_jobs():
    """Re-register pending jobs after a bot restart."""
    con = _conn()
    rows = con.execute(
        "SELECT id, user_id, prompt, run_at FROM scheduled_tasks WHERE fired = 0"
    ).fetchall()
    now = datetime.now()
    for row in rows:
        run_at = datetime.fromisoformat(row["run_at"])
        if run_at > now:
            _register(row["id"], row["user_id"], row["prompt"], run_at)
        else:
            # Missed while bot was offline — fire immediately
            con.execute("UPDATE scheduled_tasks SET fired = 1 WHERE id = ?", (row["id"],))
    con.commit()
