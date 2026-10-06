import asyncio
import logging

from . import config
from .bale_api import BaleAPI
from .config import BALE_BOT_TOKEN
from .db import init_db
from .handlers import handle
from .hafez import startup_report


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def _log_db_info():
    from .db import DATABASE_PATH, get_conn
    from .subscriptions import get_active_subscription

    with get_conn() as c:
        users = [
            r[0]
            for r in c.execute(
                "SELECT bale_user_id FROM users"
            )
        ]

        active = sum(
            1
            for u in users
            if get_active_subscription(u, c)
        )

    logging.info(
        "Database: %s | users=%d | active subscriptions=%d",
        DATABASE_PATH,
        len(users),
        active
    )


async def main():
    if not BALE_BOT_TOKEN:
        raise RuntimeError(
            "BALE_BOT_TOKEN در .env تنظیم نشده است"
        )

    init_db()
    startup_report()
    _log_db_info()

    api = BaleAPI(BALE_BOT_TOKEN)

    offset = None

    # اگر BOT_USERNAME در .env نباشد، از getMe دریافت می‌کنیم.
    if not config.BOT_USERNAME:
        try:
            me = await api.get_me()

            config.BOT_USERNAME = (
                (me.get("result") or {}).get(
                    "username",
                    ""
                )
                or ""
            )

        except Exception:
            logging.exception("getMe failed")

        if not config.BOT_USERNAME:
            logging.warning(
                "BOT_USERNAME is empty; "
                "set it in .env so invite links work"
            )

    logging.info("Hafez Bale Bot started")

    try:
        while True:
            try:
                data = await api.get_updates(
                    offset,
                    30
                )

                for up in data.get("result", []):
                    offset = (
                        up.get("update_id", 0) + 1
                    )

                    # -------------------------------------------------
                    # 1. تأیید مرحله پیش از پرداخت
                    # -------------------------------------------------
                    if up.get("pre_checkout_query"):
                        try:
                            query = up["pre_checkout_query"]

                            query_id = query.get("id")
                            invoice_payload = query.get(
                                "invoice_payload",
                                ""
                            )

                            logging.info(
                                "Pre-checkout query received: "
                                "id=%s payload=%s",
                                query_id,
                                invoice_payload
                            )

                            # فعلاً اگر payload مربوط به اشتراک ما باشد
                            # پرداخت را تأیید می‌کنیم.
                            if (
                                query_id
                                and invoice_payload.startswith(
                                    "hafez_subscription:"
                                )
                            ):
                                await api.answer_pre_checkout_query(
                                    query_id,
                                    ok=True
                                )
                            else:
                                await api.answer_pre_checkout_query(
                                    query_id,
                                    ok=False,
                                    error_message=(
                                        "اطلاعات پرداخت معتبر نیست."
                                    )
                                )

                        except Exception:
                            logging.exception(
                                "pre_checkout handler error"
                            )

                        continue

                    # -------------------------------------------------
                    # 2. پرداخت موفق
                    # -------------------------------------------------
                    if up.get("message"):
                        message = up["message"]

                        successful_payment = (
                            message.get(
                                "successful_payment"
                            )
                        )

                        if successful_payment:
                            try:
                                chat = message.get(
                                    "chat",
                                    {}
                                )

                                user = message.get(
                                    "from",
                                    {}
                                )

                                chat_id = chat.get("id")
                                user_id = user.get("id")

                                invoice_payload = (
                                    successful_payment.get(
                                        "invoice_payload",
                                        ""
                                    )
                                )

                                total_amount = (
                                    successful_payment.get(
                                        "total_amount"
                                    )
                                )

                                currency = (
                                    successful_payment.get(
                                        "currency"
                                    )
                                )

                                provider_payment_charge_id = (
                                    successful_payment.get(
                                        "provider_payment_charge_id"
                                    )
                                )

                                logging.info(
                                    "Successful payment received: "
                                    "user=%s amount=%s currency=%s "
                                    "payload=%s charge_id=%s",
                                    user_id,
                                    total_amount,
                                    currency,
                                    invoice_payload,
                                    provider_payment_charge_id
                                )

                                # فعلاً فقط پرداخت مربوط به اشتراک
                                # را قبول می‌کنیم.
                                if (
                                    user_id
                                    and invoice_payload.startswith(
                                        "hafez_subscription:"
                                    )
                                ):
                                    from .subscriptions import (
                                        activate_subscription
                                    )

                                    # از شناسه پرداخت به عنوان
                                    # payment_reference استفاده می‌کنیم.
                                    payment_reference = (
                                        provider_payment_charge_id
                                    )

                                    activate_subscription(
                                        int(user_id),
                                        days=30,
                                        plan="MONTHLY",
                                        payment_reference=(
                                            payment_reference
                                        )
                                    )

                                    await api.send_message(
                                        chat_id,
                                        "✅ پرداخت با موفقیت انجام شد!\n\n"
                                        "🎉 اشتراک ماهانه شما فعال شد.\n"
                                        "⏳ مدت اشتراک: ۳۰ روز\n\n"
                                        "اکنون می‌توانی بدون محدودیت سهمیه "
                                        "فال بگیری.",
                                    )

                            except Exception:
                                logging.exception(
                                    "successful payment handler error"
                                )

                            continue

                        # -------------------------------------------------
                        # 3. پیام‌های معمولی ربات
                        # -------------------------------------------------
                        try:
                            await handle(
                                api,
                                message
                            )

                        except Exception:
                            logging.exception(
                                "message handler error"
                            )

            except Exception:
                logging.exception(
                    "polling error"
                )

                await asyncio.sleep(3)

    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
