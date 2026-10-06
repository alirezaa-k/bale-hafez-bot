import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_db = Path(os.getenv("DATABASE_PATH", "data/bot.db").strip() or "data/bot.db").expanduser()
# مسیر نسبی نسبت به ریشه پروژه حل می‌شود (نه پوشه‌ای که ربات/CLI از آن اجرا شده)، تا ربات و CLI همیشه یک فایل را ببینند
DATABASE_PATH = str(_db if _db.is_absolute() else PROJECT_ROOT / _db)
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")

# سهمیه رایگان ماهانه و پاداش دعوت (قبلاً در db.py بودند؛ همان مقادیر)
BASE_FREE = 4
REFERRAL_BONUS = 4

# --- سیستم فال حافظ ---
HAFEZ_DATASET_PATH = os.getenv("HAFEZ_DATASET_PATH", str(Path(__file__).parent / "data" / "hafez_ghazals.json"))
FORTUNE_RECENT_WINDOW = 10   # از آخرین N فال کاربر تکرار نشود (اگر تعداد غزل‌ها اجازه دهد)
FORTUNE_COOLDOWN_SECONDS = float(os.getenv("FORTUNE_COOLDOWN_SECONDS", "3"))  # فاصله حداقلی بین دو فال یک کاربر
