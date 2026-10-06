import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BALE_BOT_TOKEN = os.getenv(
    "BALE_BOT_TOKEN",
    ""
).strip()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_db = Path(
    os.getenv(
        "DATABASE_PATH",
        "data/bot.db"
    ).strip() or "data/bot.db"
).expanduser()

# مسیر نسبی نسبت به ریشه پروژه حل می‌شود
# تا ربات و CLI همیشه یک فایل دیتابیس را ببینند.
DATABASE_PATH = str(
    _db if _db.is_absolute()
    else PROJECT_ROOT / _db
)

BOT_USERNAME = os.getenv(
    "BOT_USERNAME",
    ""
).strip().lstrip("@")

# --- تنظیمات پرداخت Bale ---

BALE_PAYMENT_PROVIDER_TOKEN = os.getenv(
    "BALE_PAYMENT_PROVIDER_TOKEN",
    ""
).strip()

SUBSCRIPTION_PRICE_RIAL = int(
    os.getenv(
        "SUBSCRIPTION_PRICE_RIAL",
        "50000"
    )
)

# --- سهمیه رایگان ماهانه و پاداش دعوت ---

BASE_FREE = 4
REFERRAL_BONUS = 4

# --- سیستم فال حافظ ---

HAFEZ_DATASET_PATH = os.getenv(
    "HAFEZ_DATASET_PATH",
    str(
        Path(__file__).parent
        / "data"
        / "hafez_ghazals.json"
    )
)

# از آخرین N فال کاربر تکرار نشود
# (اگر تعداد غزل‌ها اجازه دهد)
FORTUNE_RECENT_WINDOW = 10

# فاصله حداقلی بین دو فال یک کاربر
FORTUNE_COOLDOWN_SECONDS = float(
    os.getenv(
        "FORTUNE_COOLDOWN_SECONDS",
        "3"
    )
)