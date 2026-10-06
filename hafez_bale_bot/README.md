# Hafez Bale Bot v1
ربات فال حافظ برای بله با سهمیه ماهانه و سیستم دعوت.

## امکانات
- ۴ فال رایگان در ماه
- هر دعوت موفق و یکتا = ۴ فال اضافه
- اشتراک من
- فال حافظ
- آموزش
- دعوت از دوستان
- SQLite
- آماده برای اتصال پرداخت بله

## اجرا در Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# توکن بله را داخل .env قرار بده
python -m app.main

متن کامل غزل‌های حافظ عمداً در این نسخه نمونه است و در مرحله بعد دیتاست کامل را وارد می‌کنیم.

## v2 — کاربران، دیتابیس و سهمیه
- ماژول‌ها: `db.py` (اتصال/migration) · `users.py` · `quota.py` · `fortune_service.py` (نقطه اتصال سیستم واقعی فال) · `keyboards.py` · `texts.py` · `handlers.py` · `main.py` (فقط polling)
- migration خودکار است: با هر اجرای `python -m app.main` ستون‌های جدید به دیتابیس قبلی اضافه می‌شوند (قبلش یک نسخه `bot.db.bak-before-v2` ساخته می‌شود).
- ماه سهمیه بر اساس تاریخ واقعی (UTC) است و در دیتابیس ذخیره می‌شود، پس با ری‌استارت از بین نمی‌رود.
- نیازمندی جدیدی اضافه نشده است.

## v3 — دعوت از دوستان
- هر کاربر یک `invite_code` تصادفی و یکتا دارد؛ لینک: `https://ble.ir/<BOT_USERNAME>?start=ref_<invite_code>`
- هر دعوت موفق = ۴ فال دائمی (`users.bonus_balance`) که با ریست ماهانه پاک نمی‌شود.
- ضد تقلب: فقط کاربر کاملاً جدید حساب می‌شود، `UNIQUE(invited_user_id)` و trigger ضد self-referral در دیتابیس.
- migration خودکار است و قبلش `bot.db.bak-before-v3` ساخته می‌شود.
- اگر `BOT_USERNAME` در `.env` خالی باشد، ربات هنگام شروع از `getMe` می‌گیرد.

## v4 — سیستم فال حافظ
- دیتاست: `app/data/hafez_ghazals.json` (با `tools/import_hafez.py` ساخته می‌شود؛ جزئیات در `app/data/README.md`). متن‌های نمونه قبلی حذف شدند و دیتاست با متن placeholder رد می‌شود.
- انتخاب: `secrets.SystemRandom().choice` از بین غزل‌هایی که در ۱۰ فال اخیر همان کاربر نبوده‌اند (برای دیتاست کوچک، پنجره = نصف تعداد غزل‌ها).
- ترتیب امن: بررسی دسترسی ← انتخاب ← ارسال ← ثبت مصرف و history (جدول `fortune_history`) در یک تراکنش.
- ضد تقلب: کلید یکتای هر درخواست (`user:chat:message_id`)، قفل per-user، cooldown (`FORTUNE_COOLDOWN_SECONDS`، پیش‌فرض ۳).

## v5 — سیستم اشتراک (بدون درگاه پرداخت)
- جدول `subscriptions` (id، bale_user_id، plan_code=MONTHLY، status، started_at، expires_at، created_at) منبع اصلی است؛ حداکثر یک اشتراک `active` برای هر کاربر (ایندکس یکتا).
- فعال‌سازی دستی: `python -m tools.subscription_cli activate <user_id> [--days 30]` · `status` · `cancel`
- اشتراک فعال = فال بدون کسر سهمیه؛ سهمیه رایگان و پاداش دعوت دست‌نخورده می‌مانند. پایان اشتراک خودکار است.
