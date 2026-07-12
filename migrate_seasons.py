"""מיגרציה חד-פעמית של earnings_sentiment.json לשיטת season_from_date החדשה.

הריצה: python migrate_seasons.py  (מתוך תיקיית chip-dashboard)

הלוגיקה זהה ל-season_from_date שב-dashboard.py:
  shifted = report_date + SEASON_EARLY_DAYS
  season  = רבעון(shifted) - 1
"""

import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SEASON_EARLY_DAYS = 21
SENTIMENT_FILE = Path("earnings_sentiment.json")
BACKUP_FILE = Path("earnings_sentiment.json.bak")


def season_from_date(d: str) -> str:
    dt = datetime.fromisoformat(d[:10])
    shifted = dt + timedelta(days=SEASON_EARLY_DAYS)
    q = (shifted.month - 1) // 3 + 1
    y = shifted.year
    q -= 1
    if q == 0:
        q, y = 4, y - 1
    return f"{y}Q{q}"


def main():
    if not SENTIMENT_FILE.exists():
        print(f"קובץ לא נמצא: {SENTIMENT_FILE}")
        return

    with open(SENTIMENT_FILE, "r", encoding="utf-8") as f:
        data: dict = json.load(f)

    # גיבוי לפני כל שינוי
    shutil.copy2(SENTIMENT_FILE, BACKUP_FILE)
    print(f"גיבוי נשמר: {BACKUP_FILE}\n")

    new_data: dict = {}
    table_rows: list[tuple] = []   # (symbol, report_date, old_key, new_key)
    had_error = False

    for sym, seasons in data.items():
        new_seasons: dict = {}

        for old_key, rec in seasons.items():
            rd = rec.get("report_date", "")
            if not rd or len(rd) < 10:
                print(f"  ⚠️  {sym} / {old_key}: report_date חסר או לא תקין — הרשומה לא הוזזה")
                # שמור במקומה המקורי
                new_seasons[old_key] = rec
                table_rows.append((sym, rd or "—", old_key, old_key + " (לא שונה)"))
                continue

            new_key = season_from_date(rd)

            if new_key in new_seasons:
                print(
                    f"  ❌  התנגשות: {sym} — שתי רשומות מתמפות ל-{new_key} "
                    f"(ישן: {old_key}, report_date={rd})"
                )
                had_error = True
                continue

            new_seasons[new_key] = rec
            table_rows.append((sym, rd, old_key, new_key))

        new_data[sym] = new_seasons

    if had_error:
        print("\n❌ נמצאו התנגשויות — הקובץ לא נכתב. תקן ידנית לפני ריצה חוזרת.")
        return

    # הדפסת טבלה
    changed = [(s, r, o, n) for s, r, o, n in table_rows if o != n]
    unchanged = [(s, r, o, n) for s, r, o, n in table_rows if o == n]

    print(f"{'סמל':<14} {'report_date':<14} {'מפתח ישן':<12} {'מפתח חדש':<12}")
    print("-" * 56)
    for sym, rd, old_key, new_key in sorted(table_rows):
        marker = "" if old_key == new_key else "  ← שונה"
        print(f"{sym:<14} {rd:<14} {old_key:<12} {new_key:<12}{marker}")

    print()
    if changed:
        print(f"✅ {len(changed)} רשומות הוזזו למפתח חדש.")
    else:
        print("✅ כל הרשומות כבר תחת המפתח הנכון — אין שינויים.")

    with open(SENTIMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print(f"✅ הקובץ נכתב: {SENTIMENT_FILE}")


if __name__ == "__main__":
    main()
