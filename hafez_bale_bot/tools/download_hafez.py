import json
import os
import urllib.request

BASE_URL = "https://cdn.jsdelivr.net/gh/ganjoor/ganjoor-data@main/poets/hafez/ghazal/sh{}.json"
OUTPUT = "app/data/hafez_ghazals.json"


def download_ghazal(number):
    url = BASE_URL.format(number)

    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read()

    return json.loads(data.decode("utf-8"))


def main():
    os.makedirs("app/data", exist_ok=True)

    ghazals = []

    for number in range(1, 496):
        try:
            data = download_ghazal(number)

            sections = data.get("Sections", [])

            if not sections:
                print(f"[WARNING] Ghazal {number}: no sections")
                continue

            text = sections[0].get("PlainText", "").strip()

            if not text:
                print(f"[WARNING] Ghazal {number}: text is empty")
                continue

            interpretation = data.get("PoemSummary", "").strip()

            ghazal = {
                "id": data.get("Id"),
                "ghazal_number": number,
                "text": text,
                "interpretation": interpretation,
            }

            ghazals.append(ghazal)

            print(f"[OK] Ghazal {number}")

        except Exception as e:
            print(f"[ERROR] Ghazal {number}: {e}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            ghazals,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print(f"Total ghazals: {len(ghazals)}")
    print(f"Output: {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()