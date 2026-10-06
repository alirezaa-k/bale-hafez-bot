"""handlerهای پیام‌های ربات؛ هر بخش منو یک تابع جداست."""
import asyncio
import logging
import re
import uuid
from collections import defaultdict

from . import config
from . import keyboards as kb
from . import texts
from . import history
from .db import utcnow
from .fortune_service import FortuneUnavailable, generate_fortune
from .quota import can_draw, commit_draw, preview_after_draw
from .subscriptions import (
    get_active_subscription,
    latest_subscription,
    refresh_expired,
)
from .users import get_user, referral_count, register_user, total_draws

log = logging.getLogger(__name__)


REF_PREFIX = "ref_"
_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,64}$")


def referral_code(text):
    """از متن `/start ref_<code>` کد دعوت را بیرون می‌کشد."""
    parts = (text or "").split(maxsplit=1)

    if (
        len(parts) == 2
        and parts[0].split("@")[0] == "/start"
        and parts[1].startswith(REF_PREFIX)
    ):
        code = parts[1][len(REF_PREFIX):].strip()

        if _CODE_RE.match(code):
            return code

    return None


async def on_start(api, chat, uid, name, row):
    await api.send_message(
        chat,
        texts.welcome(name, row),
        kb.main_menu()
    )


_user_locks = defaultdict(asyncio.Lock)


def _request_key(uid, chat, msg):
    mid = msg.get("message_id")

    if mid is not None:
        return f"{uid}:{chat}:{mid}"

    return None


async def on_fortune(api, chat, uid, name, row, msg=None):
    """
    ترتیب امن:
    بررسی دسترسی ← انتخاب غزل ← آماده‌سازی متن ← ارسال موفق
    ← ثبت مصرف و history.
    """

    key = _request_key(uid, chat, msg or {})

    async with _user_locks[uid]:

        if key and history.fortune_exists(key):
            return

        row = get_user(uid)

        if not can_draw(row):
            await api.send_message(
                chat,
                texts.NO_QUOTA,
                kb.subscription_menu()
            )
            return

        cooldown = config.FORTUNE_COOLDOWN_SECONDS
        last = history.last_fortune_at(uid)

        if (
            cooldown > 0
            and last
            and (utcnow() - last).total_seconds() < cooldown
        ):
            await api.send_message(
                chat,
                texts.COOLDOWN,
                kb.fortune_menu()
            )
            return

        try:
            f = generate_fortune(row)

        except FortuneUnavailable as e:
            log.error("fortune unavailable: %s", e)

            await api.send_message(
                chat,
                texts.FORTUNE_UNAVAILABLE,
                kb.main_menu()
            )
            return

        parts = texts.fortune_messages(
            f,
            preview_after_draw(row)
        )

        for i, part in enumerate(parts):
            markup = (
                kb.fortune_menu()
                if i == len(parts) - 1
                else None
            )

            await api.send_message(
                chat,
                part,
                markup
            )

        ok, mode, _ = commit_draw(
            uid,
            f["id"],
            f["number"],
            key,
            f["type"]
        )

        if not ok:
            log.warning(
                "fortune sent but commit failed: user=%s mode=%s",
                uid,
                mode
            )


async def on_subscription(api, chat, uid, name, row):
    log.warning(
        "SUB_DEBUG uid=%s chat=%s row_uid=%s",
        uid,
        chat,
        row["bale_user_id"] if row else None,
    )

    refresh_expired(uid)

    active = get_active_subscription(uid)

    log.warning(
        "SUB_DEBUG active=%s",
        dict(active) if active else None,
    )

    page = texts.subscription_page(
        get_user(uid),
        active,
        None if active else latest_subscription(uid)
    )

    await api.send_message(
        chat,
        page,
        kb.main_menu() if active else kb.subscription_menu()
    )


async def on_buy(api, chat, uid, name, row):
    await api.send_message(
        chat,
        texts.BUY_SUBSCRIPTION,
        kb.purchase_menu()
    )


async def on_payment(api, chat, uid, name, row):
    """ساخت Invoice واقعی برای اشتراک ماهانه."""

    provider_token = getattr(
        config,
        "BALE_PAYMENT_PROVIDER_TOKEN",
        ""
    ).strip()

    price_rial = getattr(
        config,
        "SUBSCRIPTION_PRICE_RIAL",
        50000
    )

    if not provider_token:
        log.error("BALE_PAYMENT_PROVIDER_TOKEN is not configured")

        await api.send_message(
            chat,
            "⚠️ درگاه پرداخت هنوز تنظیم نشده است.\n\n"
            "لطفاً کمی بعد دوباره تلاش کن.",
            kb.purchase_menu()
        )
        return

    try:
        price_rial = int(price_rial)

    except (TypeError, ValueError):
        log.error(
            "Invalid SUBSCRIPTION_PRICE_RIAL: %r",
            price_rial
        )

        await api.send_message(
            chat,
            "⚠️ مبلغ اشتراک به‌درستی تنظیم نشده است.",
            kb.purchase_menu()
        )
        return

    if price_rial <= 0:
        await api.send_message(
            chat,
            "⚠️ مبلغ اشتراک معتبر نیست.",
            kb.purchase_menu()
        )
        return

    # payload یکتا برای هر خرید
    payment_payload = (
        f"hafez_subscription:{uid}:{uuid.uuid4().hex}"
    )

    try:
        await api.send_invoice(
            chat_id=chat,
            title="اشتراک ماهانه فال حافظ",
            description=(
                "اشتراک ۳۰ روزه فال حافظ با دریافت "
                "فال بدون محدودیت سهمیه."
            ),
            payload=payment_payload,
            provider_token=provider_token,
            currency="IRR",
            prices=[
                {
                    "label": "اشتراک ماهانه",
                    "amount": price_rial,
                }
            ],
            start_parameter=f"sub_{uid}",
        )

        log.info(
            "Subscription invoice sent: user=%s amount=%s payload=%s",
            uid,
            price_rial,
            payment_payload
        )

    except Exception:
        log.exception(
            "Failed to send subscription invoice: user=%s",
            uid
        )

        await api.send_message(
            chat,
            "❌ ارسال فاکتور پرداخت ناموفق بود.\n\n"
            "لطفاً کمی بعد دوباره امتحان کن.",
            kb.purchase_menu()
        )


async def on_guide(api, chat, uid, name, row):
    await api.send_message(
        chat,
        texts.GUIDE,
        kb.main_menu()
    )


async def on_invite(api, chat, uid, name, row):
    username = config.BOT_USERNAME or "YOUR_BOT_USERNAME"

    link = (
        f"https://ble.ir/{username}"
        f"?start={REF_PREFIX}{get_user(uid)['invite_code']}"
    )

    await api.send_message(
        chat,
        texts.invite_page(
            link,
            referral_count(uid)
        ),
        kb.main_menu()
    )


async def on_profile(api, chat, uid, name, row):
    await api.send_message(
        chat,
        texts.profile_page(
            get_user(uid),
            total_draws(uid),
            referral_count(uid),
            get_active_subscription(uid)
        ),
        kb.main_menu()
    )


async def on_back(api, chat, uid, name, row):
    await api.send_message(
        chat,
        "منوی اصلی:",
        kb.main_menu()
    )


# متن دکمه → handler
ROUTES = {
    kb.BTN_FAL: on_fortune,
    kb.BTN_AGAIN: on_fortune,

    kb.BTN_SUB: on_subscription,
    "💳 اشتراک من": on_subscription,

    kb.BTN_BUY: on_buy,
    "🛒 خرید اشتراک": on_buy,

    kb.BTN_PAYMENT: on_payment,
    "💳 ادامه به پرداخت": on_payment,

    kb.BTN_GUIDE: on_guide,
    "📖 آموزش گرفتن فال": on_guide,

    kb.BTN_INVITE: on_invite,
    "👥 دعوت از دوستان": on_invite,

    kb.BTN_PROFILE: on_profile,

    kb.BTN_BACK: on_back,
    kb.BTN_HOME: on_back,
}


async def handle(api, msg):
    text = (msg.get("text") or "").strip()

    chat = msg.get("chat", {}).get("id")

    if not chat:
        return

    u = msg.get("from", {})

    uid = int(u.get("id"))
    name = u.get("first_name", "")

    row, created, reward = register_user(
        uid,
        u.get("username", "") or "",
        name,
        referral_code(text)
    )

    if reward:
        log.info(
            "referral rewarded: invited=%s reward=%s",
            uid,
            reward
        )

    if text.startswith("/start"):
        await on_start(
            api,
            chat,
            uid,
            name,
            row
        )
        return

    fn = ROUTES.get(text)

    if fn:
        if fn is on_fortune:
            await fn(
                api,
                chat,
                uid,
                name,
                row,
                msg
            )
        else:
            await fn(
                api,
                chat,
                uid,
                name,
                row
            )

        return

    await api.send_message(
        chat,
        "از منوی زیر انتخاب کن:",
        kb.main_menu()
    )
