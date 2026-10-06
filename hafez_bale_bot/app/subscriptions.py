"""
سیستم اشتراک (فعلاً بدون درگاه پرداخت؛ فعال‌سازی دستی با activate_subscription).

منبع حقیقت: جدول subscriptions (bale_user_id, plan_code, started_at, expires_at, status).
اشتراک «فعال» یعنی: status == 'active' (بدون حساسیت به حروف) و expires_at > اکنون.
مقایسه زمان با parse واقعی datetime انجام می‌شود (نه مقایسه رشته‌ای)، پس قالب‌های
`2026-11-05T08:14:56+00:00`، `...Z`، `2026-11-05 08:14:56` (بدون timezone = UTC) همه درست کار می‌کنند.
"""
from datetime import datetime, timedelta, timezone

from .db import get_conn, utcnow

PLAN_MONTHLY = "MONTHLY"
MONTHLY_DAYS = 30

STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
STATUS_REPLACED = "replaced"
STATUS_CANCELLED = "cancelled"


def parse_dt(value) -> datetime:
    """رشته/datetime را به datetime آگاه از timezone (UTC) تبدیل می‌کند؛ ValueError اگر نامعتبر."""
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if s[-1:] in ("Z", "z"):
            s = s[:-1] + "+00:00"
        if "T" not in s and " " in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _status(sub) -> str:
    return str(sub["status"] or "").strip().lower()


def is_active(sub, now=None) -> bool:
    """status == 'active' و expires_at > اکنون."""
    if not sub or _status(sub) != STATUS_ACTIVE:
        return False
    try:
        return parse_dt(sub["expires_at"]) > (now or utcnow())
    except (ValueError, TypeError):
        return False


def get_active_subscription(user_id, c=None):
    """
    اشتراک فعال کاربر (یا None). فقط خواندنی است (روی دیتابیس چیزی نمی‌نویسد)، پس داخل تراکنش‌های
    دیگر هم بی‌خطر صدا زده می‌شود. اگر چند ردیف فعال باشد، آن‌که دیرتر تمام می‌شود برگردانده می‌شود.
    """
    def run(conn):
        now, best = utcnow(), None
        for r in conn.execute("SELECT * FROM subscriptions WHERE bale_user_id=? ORDER BY id DESC", (user_id,)):
            if is_active(r, now) and (best is None or parse_dt(r["expires_at"]) > parse_dt(best["expires_at"])):
                best = r
        return best
    if c is not None:
        return run(c)
    with get_conn() as conn:
        return run(conn)


def latest_subscription(user_id):
    with get_conn() as c:
        return c.execute("SELECT * FROM subscriptions WHERE bale_user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()


def is_expired(sub) -> bool:
    """اشتراکی که زمانش تمام شده (چه status هنوز active مانده باشد چه expired)."""
    if not sub or _status(sub) not in (STATUS_ACTIVE, STATUS_EXPIRED):
        return False
    try:
        return parse_dt(sub["expires_at"]) <= utcnow()
    except (ValueError, TypeError):
        return False


def expire_due(c, user_id=None):
    """status ردیف‌های active که زمانشان تمام شده را expired می‌کند (فقط برای تمیز بودن داده؛ تشخیص فعال بودن به آن وابسته نیست)."""
    q, args = "SELECT * FROM subscriptions WHERE lower(trim(status))=?", [STATUS_ACTIVE]
    if user_id is not None:
        q += " AND bale_user_id=?"; args.append(user_id)
    now = utcnow()
    for r in c.execute(q, args).fetchall():
        if not is_active(r, now):
            c.execute("UPDATE subscriptions SET status=? WHERE id=?", (STATUS_EXPIRED, r["id"]))


def refresh_expired(user_id=None):
    with get_conn() as c:
        expire_due(c, user_id)


def activate_subscription(user_id, days=MONTHLY_DAYS, plan=PLAN_MONTHLY, payment_reference=None):
    """
    اشتراک جدید برای کاربر فعال می‌کند (فقط کاربر ثبت‌شده؛ در غیر این صورت ValueError).
    اگر کاربر همین الان اشتراک فعال دارد، اشتراک قبلی «replaced» می‌شود و روزهای باقی‌مانده‌اش
    به اشتراک جدید اضافه می‌شود (تمدید: پایان جدید = پایان قبلی + days)، پس چیزی از دست نمی‌رود.
    سهمیه رایگان کاربر دست‌نخورده می‌ماند. خروجی: dict اشتراک جدید.
    """
    if days <= 0:
        raise ValueError("days must be positive")
    now = utcnow()
    with get_conn() as c:
        c.execute("BEGIN IMMEDIATE")
        if not c.execute("SELECT 1 FROM users WHERE bale_user_id=?", (user_id,)).fetchone():
            raise ValueError(f"user {user_id} not found")
        expire_due(c, user_id)
        base = now
        for cur in c.execute(
                "SELECT * FROM subscriptions WHERE bale_user_id=? AND lower(trim(status))=?", (user_id, STATUS_ACTIVE)).fetchall():
            base = max(base, parse_dt(cur["expires_at"]))
            c.execute("UPDATE subscriptions SET status=? WHERE id=?", (STATUS_REPLACED, cur["id"]))
        end = base + timedelta(days=days)
        sid = c.execute(
            "INSERT INTO subscriptions(bale_user_id,plan_code,started_at,expires_at,payment_reference,status,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (user_id, plan, now.isoformat(), end.isoformat(), payment_reference, STATUS_ACTIVE, now.isoformat()),
        ).lastrowid
        c.execute("UPDATE users SET subscription_until=? WHERE bale_user_id=?", (end.isoformat(), user_id))
        return dict(c.execute("SELECT * FROM subscriptions WHERE id=?", (sid,)).fetchone())


def cancel_subscription(user_id) -> bool:
    """لغو اشتراک فعال (برای تست/مدیریت). سهمیه رایگان دست‌نخورده می‌ماند."""
    with get_conn() as c:
        c.execute("BEGIN IMMEDIATE")
        n = c.execute("UPDATE subscriptions SET status=? WHERE bale_user_id=? AND lower(trim(status))=?",
                      (STATUS_CANCELLED, user_id, STATUS_ACTIVE)).rowcount
        c.execute("UPDATE users SET subscription_until=NULL WHERE bale_user_id=?", (user_id,))
        return n > 0


def days_remaining(sub) -> int:
    secs = (parse_dt(sub["expires_at"]) - utcnow()).total_seconds()
    return 0 if secs <= 0 else int(-(-secs // 86400))  # گرد به بالا
