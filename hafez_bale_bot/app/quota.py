"""سهمیه فال رایگان (ماهانه + پاداش دعوت) و ثبت مصرف فال."""
from .config import BASE_FREE
from .db import get_conn, now_iso
from .subscriptions import get_active_subscription
from .users import roll_month

SOURCE_FREE = "free"                  # از سهمیه ماهانه
SOURCE_SUBSCRIPTION = "subscription"  # اشتراک
SOURCE_GIFT = "gift"                  # از پاداش دعوت


def has_active_subscription(row, c=None):
    """اشتراک فعال = ردیف status='active' با expires_at > اکنون در جدول subscriptions (نه کش users)."""
    return bool(row) and get_active_subscription(row["bale_user_id"], c) is not None


def monthly_remaining(row) -> int:
    return max(0, BASE_FREE - row["monthly_used"])


def bonus_remaining(row) -> int:
    return max(0, row["bonus_balance"])


def remaining_free(row) -> int:
    """کل فال رایگان باقی‌مانده = ماهانه + پاداش دعوت (بدون سقف ۴)."""
    return monthly_remaining(row) + bonus_remaining(row)


def spend_plan(row, c=None):
    """مصرف از کجا انجام می‌شود؟ ترتیب: اشتراک ← ماهانه ← پاداش دعوت ؛ None یعنی دسترسی ندارد."""
    if has_active_subscription(row, c):
        return SOURCE_SUBSCRIPTION
    if monthly_remaining(row) > 0:
        return SOURCE_FREE
    if bonus_remaining(row) > 0:
        return SOURCE_GIFT
    return None


def can_draw(row) -> bool:
    return spend_plan(row) is not None


def preview_after_draw(row) -> dict:
    """وضعیت سهمیه «بعد از» این فال، برای نمایش در پیام (قبل از ثبت واقعی مصرف)."""
    d = dict(row)
    plan = spend_plan(row)
    if plan == SOURCE_FREE:
        d["monthly_used"] += 1
    elif plan == SOURCE_GIFT:
        d["bonus_balance"] -= 1
    return d


def quota_line(row) -> str:
    if has_active_subscription(row):
        return "فال رایگان این ماه: ♾️ (اشتراک فعال)"
    m, b = monthly_remaining(row), bonus_remaining(row)
    if b:
        return f"فال رایگان باقی‌مانده: {m + b} (ماهانه {m} از {BASE_FREE} + هدیه دعوت {b})"
    return f"فال رایگان این ماه: {m} از {BASE_FREE}"


def commit_draw(uid, poem_id, ghazal_number, request_key=None, draw_type="hafez"):
    """
    ثبت نهایی فال (بعد از ارسال موفق): کم کردن سهمیه + ثبت در draws + ثبت در fortune_history
    همه در یک تراکنش. request_key یکتا است، پس همان درخواست هرگز دوبار مصرف نمی‌شود.
    خروجی: (ok, mode, history_id) ؛ mode در حالت ناموفق: "limit" | "duplicate" | "user_not_found"
    """
    with get_conn() as c:
        c.execute("BEGIN IMMEDIATE")
        if request_key and c.execute("SELECT 1 FROM fortune_history WHERE request_key=?", (request_key,)).fetchone():
            return False, "duplicate", None
        roll_month(c, uid)
        row = c.execute("SELECT * FROM users WHERE bale_user_id=?", (uid,)).fetchone()
        if not row:
            return False, "user_not_found", None
        source = spend_plan(row, c)
        if source is None:
            return False, "limit", None
        if source == SOURCE_FREE:
            c.execute("UPDATE users SET monthly_used=monthly_used+1 WHERE bale_user_id=?", (uid,))
        elif source == SOURCE_GIFT:
            c.execute("UPDATE users SET bonus_balance=bonus_balance-1 WHERE bale_user_id=?", (uid,))
        now = now_iso()
        c.execute(
            "INSERT INTO draws(bale_user_id,ghazal_number,created_at,draw_type,source) VALUES(?,?,?,?,?)",
            (uid, ghazal_number, now, draw_type, source),
        )
        cur = c.execute(
            "INSERT INTO fortune_history(user_id,poem_id,source,request_key,created_at) VALUES(?,?,?,?,?)",
            (uid, poem_id, source, request_key, now),
        )
        return True, source, cur.lastrowid
