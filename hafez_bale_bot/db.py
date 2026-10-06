"""لایه پایین دیتابیس: اتصال، زمان، ساخت جدول‌ها و migration (SQLite)."""
import logging
import secrets
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import BASE_FREE, DATABASE_PATH, REFERRAL_BONUS

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utcnow().isoformat()


def month_key() -> str:
    """کلید ماه جاری بر اساس تاریخ واقعی (UTC)، مثل 2026-10."""
    return utcnow().strftime("%Y-%m")


def month_start() -> str:
    """تاریخ شروع دوره سهمیه ماه جاری، مثل 2026-10-01."""
    return utcnow().strftime("%Y-%m-01")


@contextmanager
def get_conn():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


BASE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,bale_user_id INTEGER UNIQUE NOT NULL,
  username TEXT,first_name TEXT,created_at TEXT NOT NULL,monthly_used INTEGER NOT NULL DEFAULT 0,
  monthly_bonus INTEGER NOT NULL DEFAULT 0,month_key TEXT NOT NULL,subscription_until TEXT);
CREATE TABLE IF NOT EXISTS referrals(
  id INTEGER PRIMARY KEY AUTOINCREMENT,inviter_user_id INTEGER NOT NULL,
  invited_user_id INTEGER UNIQUE NOT NULL,created_at TEXT NOT NULL,bonus_granted INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS subscriptions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,bale_user_id INTEGER NOT NULL,plan_code TEXT NOT NULL,
  started_at TEXT NOT NULL,expires_at TEXT NOT NULL,payment_reference TEXT);
CREATE TABLE IF NOT EXISTS draws(
  id INTEGER PRIMARY KEY AUTOINCREMENT,bale_user_id INTEGER NOT NULL,ghazal_number INTEGER NOT NULL,created_at TEXT NOT NULL);
'''

# ستون‌های جدید این مرحله (اضافه‌شدن با ALTER TABLE روی دیتابیس موجود، بدون از بین رفتن داده)
NEW_COLUMNS = {
    "users": [
        ("last_seen_at", "TEXT"),
        ("quota_month_start", "TEXT"),
        ("invite_code", "TEXT"),  # کد دعوت اختصاصی (یکتا)
        ("bonus_balance", "INTEGER NOT NULL DEFAULT 0"),  # پاداش دعوت؛ با ریست ماهانه صفر نمی‌شود
    ],
    "referrals": [
        ("referral_code", "TEXT"),
        ("reward_amount", "INTEGER NOT NULL DEFAULT 0"),
        ("status", "TEXT NOT NULL DEFAULT 'rewarded'"),
    ],
    "draws": [
        ("draw_type", "TEXT NOT NULL DEFAULT 'hafez'"),
        ("source", "TEXT NOT NULL DEFAULT 'free'"),  # free | subscription | gift
    ],
}


def _columns(c, table):
    return {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}


def _new_invite_code(c) -> str:
    while True:
        code = secrets.token_hex(5)
        if not c.execute("SELECT 1 FROM users WHERE invite_code=?", (code,)).fetchone():
            return code


def new_invite_code(c) -> str:
    return _new_invite_code(c)


SCHEMA_VERSION = 3


def _user_version(c) -> int:
    return c.execute("PRAGMA user_version").fetchone()[0]


def init_db():
    db_file = Path(DATABASE_PATH)
    existed = db_file.exists() and db_file.stat().st_size > 0

    with get_conn() as c:
        c.executescript(BASE_SCHEMA)
        missing = any(col not in _columns(c, t) for t, cols in NEW_COLUMNS.items() for col, _ in cols)
        outdated = _user_version(c) < SCHEMA_VERSION

    # قبل از migration روی دیتابیس موجود، یک نسخه پشتیبان بگیر
    if existed and (missing or outdated):
        backup = db_file.with_name(db_file.name + ".bak-before-v3")
        if not backup.exists():
            shutil.copy2(db_file, backup)
            log.info("DB backup created: %s", backup)

    with get_conn() as c:
        for table, cols in NEW_COLUMNS.items():
            have = _columns(c, table)
            for col, decl in cols:
                if col not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                    log.info("migrated: %s.%s added", table, col)

        # پر کردن مقدار کاربران قدیمی
        c.execute("UPDATE users SET last_seen_at=created_at WHERE last_seen_at IS NULL")
        c.execute("UPDATE users SET quota_month_start=month_key||'-01' WHERE quota_month_start IS NULL")
        for r in c.execute("SELECT id FROM users WHERE invite_code IS NULL").fetchall():
            c.execute("UPDATE users SET invite_code=? WHERE id=?", (_new_invite_code(c), r["id"]))

        # v3: پاداش دعوت از monthly_bonus (که ماهانه صفر می‌شد) به bonus_balance (دائمی) منتقل می‌شود.
        # مقدار «باقی‌مانده» هر کاربر دقیقاً حفظ می‌شود. اجرای دوباره بی‌خطر است (monthly_bonus بعد از انتقال صفر می‌شود).
        for r in c.execute("SELECT bale_user_id,monthly_used,monthly_bonus,month_key FROM users WHERE monthly_bonus>0").fetchall():
            if r["month_key"] == month_key():
                used = min(r["monthly_used"], BASE_FREE)
                remaining = max(0, BASE_FREE + r["monthly_bonus"] - r["monthly_used"])
                carry = max(0, remaining - (BASE_FREE - used))
                c.execute(
                    "UPDATE users SET monthly_used=?,bonus_balance=bonus_balance+?,monthly_bonus=0 WHERE bale_user_id=?",
                    (used, carry, r["bale_user_id"]),
                )
            else:
                c.execute("UPDATE users SET monthly_bonus=0 WHERE bale_user_id=?", (r["bale_user_id"],))

        # referrals قدیمی (در صورت وجود) کامل شوند
        c.execute("UPDATE referrals SET reward_amount=? WHERE bonus_granted=1 AND reward_amount=0", (REFERRAL_BONUS,))
        c.execute(
            "UPDATE referrals SET referral_code=(SELECT invite_code FROM users WHERE bale_user_id=referrals.inviter_user_id) "
            "WHERE referral_code IS NULL"
        )

        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_invite_code ON users(invite_code)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_draws_user ON draws(bale_user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_user_id, status)")
        # جلوگیری سطح دیتابیس از self-referral (UNIQUE روی invited_user_id هم از referral تکراری جلوگیری می‌کند)
        c.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_referrals_no_self BEFORE INSERT ON referrals "
            "WHEN NEW.inviter_user_id = NEW.invited_user_id "
            "BEGIN SELECT RAISE(ABORT,'self referral is not allowed'); END"
        )
    with get_conn() as c:
        c.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
