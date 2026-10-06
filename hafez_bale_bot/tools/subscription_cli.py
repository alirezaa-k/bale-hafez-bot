"""
مدیریت دستی اشتراک برای تست (تا وقتی درگاه پرداخت وصل نشده).
  python -m tools.subscription_cli activate <user_id> [--days 30]
  python -m tools.subscription_cli status <user_id>
  python -m tools.subscription_cli cancel <user_id>
  python -m tools.subscription_cli list <user_id>     (همه ردیف‌های اشتراک کاربر؛ برای عیب‌یابی)
برای تست انقضا: activate با --days 0.002 (حدود ۳ دقیقه).
"""
import argparse
import sys

from app.db import DATABASE_PATH, get_conn, init_db
from app.subscriptions import (activate_subscription, cancel_subscription, days_remaining,
                               get_active_subscription, latest_subscription)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["activate", "status", "cancel", "list"])
    ap.add_argument("user_id", type=int)
    ap.add_argument("--days", type=float, default=30)
    a = ap.parse_args(argv)
    init_db()
    print(f"DB: {DATABASE_PATH}")
    if a.cmd == "list":
        with get_conn() as c:
            rows = c.execute("SELECT id,plan_code,started_at,expires_at,status FROM subscriptions WHERE bale_user_id=? ORDER BY id", (a.user_id,)).fetchall()
        for r in rows:
            print(tuple(r))
        print(f"{len(rows)} row(s)")
        return 0
    if a.cmd == "activate":
        try:
            s = activate_subscription(a.user_id, a.days)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr); return 1
        print(f"OK: subscription #{s['id']} {s['plan_code']} active {s['started_at']} -> {s['expires_at']}")
    elif a.cmd == "cancel":
        print("cancelled" if cancel_subscription(a.user_id) else "no active subscription")
    else:
        act = get_active_subscription(a.user_id)
        if act:
            print(f"ACTIVE #{act['id']} until {act['expires_at']} ({days_remaining(act)} day(s) left)")
        else:
            last = latest_subscription(a.user_id)
            print("NO active subscription" + (f"; last: #{last['id']} {last['status']} ended {last['expires_at']}" if last else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
