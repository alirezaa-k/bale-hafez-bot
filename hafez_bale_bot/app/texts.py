"""متن پیام‌های ربات."""

from .config import REFERRAL_BONUS
from .subscriptions import days_remaining, is_expired, parse_dt
from .quota import (
    bonus_remaining,
    has_active_subscription,
    quota_line,
    remaining_free,
)

INTENT_HINT = "🕊 نیتت را در دل کن و سپس روی «🔮 فال حافظ» بزن."

SEP = "━━━━━━━━━━━━"

MESSAGE_LIMIT = 3900  # سقف پیام بله ۴۰۹۶ کاراکتر است


def welcome(name, row):
    return (
        f"سلام {name or 'دوست عزیز'} 🌹\n\n"
        "به فال حافظ خوش آمدی.\n\n"
        f"🎁 {quota_line(row)}\n\n"
        f"{INTENT_HINT}"
    )


NO_QUOTA = (
    "سهمیه فال رایگان این ماه تمام شده است. 🔒\n\n"
    "برای ادامه، اشتراک بگیر یا دوستانت را دعوت کن؛ "
    "هر دعوت موفق ۴ فال اضافه می‌دهد."
)

FORTUNE_UNAVAILABLE = (
    "فال حافظ موقتاً در دسترس نیست. 🙏\n\n"
    "سهمیه‌ات کم نشد؛ کمی بعد دوباره امتحان کن."
)

COOLDOWN = "⏳ لطفاً چند ثانیه صبر کن و دوباره فال بگیر."


def _chunk(text, limit):
    """متن بلند را روی مرز بیت‌ها به تکه‌های کوچک‌تر از limit می‌شکند."""
    parts, cur = [], ""

    for block in text.split("\n\n"):
        cand = f"{cur}\n\n{block}" if cur else block

        if len(cand) <= limit:
            cur = cand
        else:
            if cur:
                parts.append(cur)

            while len(block) > limit:
                parts.append(block[:limit])
                block = block[limit:]

            cur = block

    if cur:
        parts.append(cur)

    return parts


def fortune_messages(f, row_after):
    """فال را به یک یا چند پیام برای رعایت سقف طول تبدیل می‌کند."""

    head = (
        f"🔮 فال حافظ\n\n"
        f"📜 غزل شماره {f['number']}\n\n"
        f"{f['text']}"
    )

    if f.get("interpretation"):
        mid = (
            f"{SEP}\n\n"
            "🔮 تعبیر فال\n\n"
            f"{f['interpretation']}\n\n"
            f"{SEP}"
        )
    else:
        mid = SEP

    foot = (
        "🌹 نیتت روشن، دلت آرام\n\n"
        f"📊 {quota_line(row_after)}"
    )

    full = f"{head}\n\n{mid}\n\n{foot}"

    if len(full) <= MESSAGE_LIMIT:
        return [full]

    parts = _chunk(head, MESSAGE_LIMIT)
    tail = f"{mid}\n\n{foot}"
    parts += _chunk(tail, MESSAGE_LIMIT)

    return parts


def _date(iso):
    try:
        return parse_dt(iso).strftime("%Y-%m-%d") + " (UTC)"
    except (ValueError, TypeError):
        return str(iso)[:10] + " (UTC)"


def subscription_page(row, active=None, latest=None):
    """active: اشتراک فعال؛ latest: آخرین اشتراک کاربر."""

    if active:
        return (
            "👤 اشتراک من\n\n"
            "نوع اشتراک: ماهانه\n"
            "وضعیت: فعال ✅\n"
            f"تاریخ شروع: {_date(active['started_at'])}\n"
            f"تاریخ پایان: {_date(active['expires_at'])}\n"
            f"روز باقی‌مانده: {days_remaining(active)}\n\n"
            "با اشتراک فعال، فال بدون محدودیت سهمیه می‌گیری.\n"
            f"🎁 سهمیه رایگان محفوظ: {remaining_free(row)} فال"
        )

    expired = ""

    if latest and is_expired(latest):
        expired = (
            f"اشتراک قبلی شما در تاریخ "
            f"{_date(latest['expires_at'])} منقضی شد.\n\n"
        )

    return (
        "👤 اشتراک من\n\n"
        "وضعیت: بدون اشتراک\n"
        f"فال رایگان باقی‌مانده: {remaining_free(row)}\n\n"
        f"{expired}"
        "برای دریافت فال بیشتر باید اشتراک تهیه کنی. 💳"
    )


BUY_SUBSCRIPTION = (
    "💳 خرید اشتراک\n\n"
    "⭐ اشتراک ماهانه\n"
    "⏳ مدت: ۳۰ روز\n\n"
    "با خرید اشتراک:\n"
    "• دریافت فال بدون محدودیت سهمیه\n"
    "• حفظ سهمیه رایگان باقی‌مانده\n"
    "• فعال‌سازی خودکار پس از پرداخت موفق\n\n"
    "💰 قیمت: ۵٬۰۰۰ تومان\n\n"
    "برای پرداخت روی «💳 ادامه به پرداخت» بزن."
)


GUIDE = (
    "📖 آموزش فال\n\n"
    "۱) نیتت را در دل کن.\n"
    "۲) «🔮 فال حافظ» را بزن.\n"
    "۳) یک غزل تصادفی با تعبیرش برایت ارسال می‌شود.\n\n"
    "سهمیه پایه: ۴ فال رایگان در ماه. "
    "هر دعوت موفق: ۴ فال اضافه.\n\n"
    "🚧 آموزش کامل به‌زودی اضافه می‌شود."
)


def invite_page(link, count):
    return (
        "🎁 دعوت از دوستان\n\n"
        f"با دعوت از هر دوست، {REFERRAL_BONUS} فال رایگان دریافت می‌کنی.\n\n"
        f"لینک دعوت اختصاصی شما:\n{link}\n\n"
        f"تعداد دعوت‌های موفق:\n{count}\n\n"
        f"🎯 پاداش هر دعوت: {REFERRAL_BONUS} فال رایگان "
        "(دائمی؛ با شروع ماه جدید از بین نمی‌رود)"
    )


def profile_page(row, used_total, invites, active_sub=None):
    username = (
        f"@{row['username']}"
        if row["username"]
        else "—"
    )

    status = (
        f"فعال ✅ (تا "
        f"{parse_dt(active_sub['expires_at']).strftime('%Y-%m-%d')})"
        if active_sub
        else "ندارید"
    )

    lines = [
        "👤 پروفایل من\n",
        f"نام: {row['first_name'] or '—'}",
        f"Username: {username}",
        f"فال رایگان باقی‌مانده: {remaining_free(row)}",
    ]

    if bonus_remaining(row):
        lines.append(
            f"🎁 شامل هدیه دعوت: {bonus_remaining(row)}"
        )

    lines += [
        f"دعوت‌های موفق: {invites}",
        f"اشتراک: {status}",
        f"تعداد کل فال‌های استفاده‌شده: {used_total}",
    ]

    return "\n".join(lines)