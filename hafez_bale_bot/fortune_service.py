"""
سرویس انتخاب فال. handlers فقط generate_fortune() را صدا می‌زنند.
انتخاب: random واقعی (secrets) از بین غزل‌هایی که در N فال اخیر همان کاربر نبوده‌اند.
هیچ ترتیب/اندیس/modulo/timestamp‌ای در انتخاب دخالت ندارد.
"""
import secrets

from . import config
from .hafez import DatasetError, get_poems
from .history import recent_poem_ids


class FortuneUnavailable(Exception):
    """دیتاست حافظ آماده نیست."""


_rng = secrets.SystemRandom()


def pick_poem_id(ids, recent, choice=None):
    """
    ids: همه idها ؛ recent: idهای اخیر کاربر (جدیدترین اول).
    هرگز غزل فال قبلی را برنمی‌گرداند مگر فقط یک غزل وجود داشته باشد.
    """
    choice = choice or _rng.choice
    pool = [i for i in ids if i not in set(recent)]
    if not pool:  # نباید رخ دهد چون پنجره کوچک می‌شود؛ محافظ اضافه
        pool = [i for i in ids if not recent or i != recent[0]] or list(ids)
    return choice(pool)


def generate_fortune(user_row, choice=None) -> dict:
    """خروجی: {"type","id","number","text","interpretation"}"""
    try:
        poems = get_poems()
    except DatasetError as e:
        raise FortuneUnavailable(str(e))
    ids = list(poems)
    # پنجره اخیر: حداکثر N؛ اگر غزل‌ها کم باشند حداکثر نصف آن‌ها، تا هم تکرار پشت‌سرهم نشود هم انتخاب random بماند
    window = min(config.FORTUNE_RECENT_WINDOW, len(ids) // 2)
    recent = recent_poem_ids(user_row["bale_user_id"], window)
    poem = poems[pick_poem_id(ids, recent, choice)]
    return {"type": "hafez", "id": poem.id, "number": poem.ghazal_number,
            "text": poem.text, "interpretation": poem.interpretation}
