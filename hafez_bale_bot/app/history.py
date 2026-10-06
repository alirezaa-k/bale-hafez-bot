"""تاریخچه فال‌های کاربر (جدول fortune_history)."""
from datetime import datetime

from .db import get_conn


def recent_poem_ids(uid, limit):
    if limit <= 0:
        return []
    with get_conn() as c:
        return [r["poem_id"] for r in c.execute(
            "SELECT poem_id FROM fortune_history WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit))]


def fortune_exists(request_key) -> bool:
    if not request_key:
        return False
    with get_conn() as c:
        return c.execute("SELECT 1 FROM fortune_history WHERE request_key=?", (request_key,)).fetchone() is not None


def last_fortune_at(uid):
    with get_conn() as c:
        r = c.execute("SELECT created_at FROM fortune_history WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    return datetime.fromisoformat(r["created_at"]) if r else None
