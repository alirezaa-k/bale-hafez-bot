"""
ساخت app/data/hafez_ghazals.json از یک فایل متنی/JSON که خودتان تهیه کرده‌اید.

استفاده:
  python -m tools.import_hafez --input divan.txt [--interpretations interp.json] [--out app/data/hafez_ghazals.json]

فرمت ورودی TXT (UTF-8):
  ## 1
  مصرع اول بیت ۱
  مصرع دوم بیت ۱
  <یک خط خالی بین بیت‌ها>
  مصرع اول بیت ۲
  مصرع دوم بیت ۲
  ### تعبیر          (اختیاری)
  متن تعبیر همین غزل
  ## 2
  ...
فرمت ورودی JSON: لیستی از {"id"/"ghazal_number"/"number", "text", "interpretation"/"taabir" (اختیاری)}
فایل --interpretations (اختیاری): JSON به شکل {"1": "تعبیر ...", "2": "..."} یا لیست {"number":1,"interpretation":"..."}
"""
import argparse
import json
import re
import sys
from pathlib import Path

from app.hafez import DatasetError, validate_poems

_AR2FA = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ۀ", "\u200f": "", "\u200e": ""})


def clean(s: str) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n").translate(_AR2FA)
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def parse_txt(content: str) -> list:
    items, cur, mode = [], None, "text"
    for line in content.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^##\s*(\d+)\s*$", line.strip())
        if m:
            cur = {"id": int(m.group(1)), "ghazal_number": int(m.group(1)), "text": [], "interpretation": []}
            items.append(cur); mode = "text"; continue
        if cur is None:
            continue
        if re.match(r"^###\s*تعبیر\s*$", line.strip()):
            mode = "interpretation"; continue
        cur[mode].append(line)
    for it in items:
        it["text"] = clean("\n".join(it["text"]))
        it["interpretation"] = clean("\n".join(it["interpretation"])) or None
    return items


def parse_json(raw) -> list:
    out = []
    for i, it in enumerate(raw):
        num = it.get("ghazal_number", it.get("number", it.get("id")))
        out.append({
            "id": it.get("id", num), "ghazal_number": num,
            "text": clean(it.get("text") or it.get("poem") or ""),
            "interpretation": clean(it.get("interpretation") or it.get("taabir") or "") or None,
        })
    return out


def merge_interpretations(items, raw):
    if isinstance(raw, list):
        raw = {str(x["number"]): x["interpretation"] for x in raw}
    for it in items:
        t = raw.get(str(it["ghazal_number"]))
        if t:
            it["interpretation"] = clean(t)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--interpretations")
    ap.add_argument("--out", default="app/data/hafez_ghazals.json")
    a = ap.parse_args(argv)

    src = Path(a.input).read_text(encoding="utf-8")
    items = parse_json(json.loads(src)) if a.input.lower().endswith(".json") else parse_txt(src)
    if a.interpretations:
        merge_interpretations(items, json.loads(Path(a.interpretations).read_text(encoding="utf-8")))
    try:
        poems = validate_poems(items)
    except DatasetError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        [{"id": p.id, "ghazal_number": p.ghazal_number, "text": p.text, "interpretation": p.interpretation} for p in poems],
        ensure_ascii=False, indent=1), encoding="utf-8")
    with_i = sum(1 for p in poems if p.interpretation)
    print(f"OK: {len(poems)} poems written to {out} ({with_i} with interpretation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
