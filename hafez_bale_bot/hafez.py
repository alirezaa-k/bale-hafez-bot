"""
دیتاست غزل‌های حافظ: بارگذاری، اعتبارسنجی و دسترسی.

فایل داده: app/data/hafez_ghazals.json  (یا مسیر HAFEZ_DATASET_PATH)
فرمت: لیستی از آبجکت‌ها
  {"id": 1, "ghazal_number": 1, "text": "<متن کامل؛ مصرع‌ها در خط جدا، بیت‌ها با یک خط خالی>",
   "interpretation": "<تعبیر؛ اختیاری>"}
برای ساخت این فایل از tools/import_hafez.py استفاده کنید.
"""
import json
import logging
from pathlib import Path
from typing import NamedTuple, Optional

from . import config

log = logging.getLogger(__name__)

EXPECTED_FULL_SIZE = 495  # تعداد غزل‌ها در نسخه قزوینی-غنی؛ فقط برای هشدار «ناقص بودن»


class Poem(NamedTuple):
    id: int
    ghazal_number: int
    text: str
    interpretation: Optional[str]


class DatasetError(Exception):
    pass


_PLACEHOLDER_MARKERS = ("[متن", "اینجا قرار", "تعبیر نمونه")


def validate_poems(raw) -> list:
    """لیست خام را اعتبارسنجی و به Poem تبدیل می‌کند؛ در صورت مشکل DatasetError."""
    if not isinstance(raw, list) or not raw:
        raise DatasetError("dataset must be a non-empty JSON list")
    poems, seen, problems = [], set(), []
    for i, item in enumerate(raw):
        where = f"item #{i}"
        if not isinstance(item, dict):
            problems.append(f"{where}: not an object"); continue
        try:
            pid = int(item.get("id", item.get("ghazal_number")))
            number = int(item.get("ghazal_number", pid))
        except (TypeError, ValueError):
            problems.append(f"{where}: id/ghazal_number missing or not an integer"); continue
        where = f"poem id={pid}"
        text = (item.get("text") or "").strip()
        interp = (item.get("interpretation") or "").strip() or None
        if pid in seen:
            problems.append(f"{where}: duplicate id"); continue
        if len([l for l in text.splitlines() if l.strip()]) < 2:
            problems.append(f"{where}: text is empty or too short"); continue
        if any(m in text for m in _PLACEHOLDER_MARKERS) or (interp and any(m in interp for m in _PLACEHOLDER_MARKERS)):
            problems.append(f"{where}: looks like placeholder text"); continue
        seen.add(pid)
        poems.append(Poem(pid, number, text, interp))
    if problems:
        raise DatasetError(f"{len(problems)} problem(s): " + "; ".join(problems[:10]))
    return poems


def load_poems(path=None) -> list:
    p = Path(path or config.HAFEZ_DATASET_PATH)
    if not p.exists():
        raise DatasetError(f"dataset file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise DatasetError(f"invalid JSON in {p}: {e}")
    return validate_poems(raw)


_cache = {"poems": None, "error": None}


def reload_dataset():
    _cache["poems"], _cache["error"] = None, None
    try:
        _cache["poems"] = {p.id: p for p in load_poems()}
    except DatasetError as e:
        _cache["error"] = str(e)
    return _cache["poems"]


def get_poems() -> dict:
    """{id: Poem}؛ اگر دیتاست آماده نباشد DatasetError."""
    if _cache["poems"] is None and _cache["error"] is None:
        reload_dataset()
    if _cache["poems"] is None:
        raise DatasetError(_cache["error"])
    return _cache["poems"]


def startup_report():
    """گزارش وضعیت دیتاست در لاگ هنگام شروع ربات."""
    try:
        poems = get_poems()
    except DatasetError as e:
        log.error("Hafez dataset NOT ready: %s -- فال حافظ غیرفعال است (سهمیه کم نمی‌شود). "
                  "راهنما: python -m tools.import_hafez --help", e)
        return
    n = len(poems)
    with_i = sum(1 for p in poems.values() if p.interpretation)
    log.info("Hafez dataset: %d poems, %d with interpretation", n, with_i)
    if n < EXPECTED_FULL_SIZE - 10:
        log.warning("Hafez dataset looks incomplete (%d of ~%d)", n, EXPECTED_FULL_SIZE)
    if with_i < n:
        log.warning("%d poems have no interpretation (it will be omitted from the message)", n - with_i)
