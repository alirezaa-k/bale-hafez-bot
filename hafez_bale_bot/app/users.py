"""مدیریت کاربران: ثبت‌نام، سیستم دعوت (referral)، پروفایل."""
import sqlite3

from .config import REFERRAL_BONUS
from .subscriptions import STATUS_ACTIVE
from .db import get_conn, month_key, month_start, new_invite_code, now_iso

STATUS_REWARDED = "rewarded"


def roll_month(c, uid):
    """
    اگر ماه عوض شده باشد فقط سهمیه ماهانه (monthly_used) ریست می‌شود.
    پاداش دعوت (bonus_balance) عمداً دست‌نخورده می‌ماند.
    """
    key = month_key()
    c.execute(
        "UPDATE users SET monthly_used=0,month_key=?,quota_month_start=? "
        "WHERE bale_user_id=? AND month_key!=?",
        (key, month_start(), uid, key),
    )
    _sync_subscription_cache(c, uid)


def _sync_subscription_cache(c, uid):
    """users.subscription_until همیشه از جدول subscriptions (منبع اصلی) ساخته می‌شود."""
    c.execute(
        "UPDATE users SET subscription_until=(SELECT MAX(expires_at) FROM subscriptions s "
        "WHERE s.bale_user_id=users.bale_user_id AND s.status=?) WHERE bale_user_id=?",
        (STATUS_ACTIVE, uid),
    )


def get_user(uid):
    with get_conn() as c:
        roll_month(c, uid)
        return c.execute("SELECT * FROM users WHERE bale_user_id=?", (uid,)).fetchone()


def get_user_by_invite_code(code):
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE invite_code=?", (code,)).fetchone()


def register_user(uid, username="", first_name="", referral_code=None):
    """
    کاربر را ثبت/به‌روز می‌کند.
    خروجی: (row, created, reward) ؛ reward = مقدار پاداشی که به دعوت‌کننده داده شد (۰ اگر نبود).
    دعوت فقط وقتی حساب می‌شود که کاربر «همین الان برای اولین بار» ثبت شده باشد.
    """
    now = now_iso()
    reward = 0
    with get_conn() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO users(bale_user_id,username,first_name,created_at,month_key,"
            "last_seen_at,quota_month_start,invite_code) VALUES(?,?,?,?,?,?,?,?)",
            (uid, username, first_name, now, month_key(), now, month_start(), new_invite_code(c)),
        )
        created = cur.rowcount == 1
        c.execute(
            "UPDATE users SET username=?,first_name=?,last_seen_at=? WHERE bale_user_id=?",
            (username, first_name, now, uid),
        )
        roll_month(c, uid)

        if created and referral_code:
            inviter = c.execute(
                "SELECT bale_user_id FROM users WHERE invite_code=?", (referral_code,)
            ).fetchone()
            if inviter and inviter["bale_user_id"] != uid:
                try:
                    # UNIQUE(invited_user_id) و trigger ضد self-referral جلوی تکرار را در سطح دیتابیس می‌گیرند
                    c.execute(
                        "INSERT INTO referrals(inviter_user_id,invited_user_id,referral_code,created_at,"
                        "bonus_granted,reward_amount,status) VALUES(?,?,?,?,1,?,?)",
                        (inviter["bale_user_id"], uid, referral_code, now, REFERRAL_BONUS, STATUS_REWARDED),
                    )
                except sqlite3.IntegrityError:
                    pass
                else:
                    c.execute(
                        "UPDATE users SET bonus_balance=bonus_balance+? WHERE bale_user_id=?",
                        (REFERRAL_BONUS, inviter["bale_user_id"]),
                    )
                    reward = REFERRAL_BONUS
        row = c.execute("SELECT * FROM users WHERE bale_user_id=?", (uid,)).fetchone()
    return row, created, reward


def ensure_user(uid, username="", first_name="", referral_code=None):
    """سازگار با نسخه قبلی: فقط ردیف کاربر را برمی‌گرداند."""
    return register_user(uid, username, first_name, referral_code)[0]


def referral_count(uid):
    with get_conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM referrals WHERE inviter_user_id=? AND status=?", (uid, STATUS_REWARDED)
        ).fetchone()[0]


def total_draws(uid) -> int:
    with get_conn() as c:
        return c.execute("SELECT COUNT(*) FROM draws WHERE bale_user_id=?", (uid,)).fetchone()[0]
