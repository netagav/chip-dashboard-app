"""
fetch_earnings_calendar.py — הרצה יומית דרך GitHub Actions.
מושך earnings_dates לכל CORE_COMPANIES, ממזג עם הקובץ הקיים,
וכותב earnings_calendar.json.

חשוב: רשימת CORE_COMPANIES כאן חייבת להישאר מסונכרנת עם dashboard.py.
"""
import json
import math
import random
import sys
import time
from datetime import datetime, timezone, timedelta

import yfinance as yf

# --- שמור מסונכרן עם CORE_COMPANIES ב-dashboard.py ---
CORE_COMPANIES = sorted([
    "ASML", "AMAT", "LRCX", "KLAC", "NVDA", "AMD", "TSM", "INTC", "MU",
    "TXN", "ADI", "AVGO", "QCOM", "MRVL", "ARM",
    "TSEM", "NVMI", "CAMT", "MBLY",
    "MSFT", "META", "GOOGL", "AMZN", "ORCL",
    "005930.KS", "000660.KS",
])

DAYS_BACK = 120
DAYS_FWD = 120
OUTPUT_FILE = "earnings_calendar.json"
MIN_SUCCESS_RATIO = 1 / 3   # פחות מזה — הקובץ לא יעודכן
MAX_RETRIES = 3
SLEEP_BASE = 2.0             # שניות בין סימבולים


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_one(sym, lo, hi):
    """מושך earnings_dates לסימבול אחד עם retry ו-backoff.
    מחזיר רשימת רשומות (יכול להיות ריקה), או None אם כל הניסיונות נכשלו."""
    for attempt in range(MAX_RETRIES):
        try:
            df = yf.Ticker(sym).earnings_dates
            if df is None or df.empty:
                return []
            out = []
            for dt in df.index:
                d = dt.date() if hasattr(dt, "date") else dt
                if not (lo <= d <= hi):
                    continue
                row = df.loc[dt]
                eps_act = _clean(row.get("Reported EPS"))
                eps_est = _clean(row.get("EPS Estimate"))
                surp    = _clean(row.get("Surprise(%)"))
                out.append({
                    "date":       d.isoformat(),
                    "symbol":     sym,
                    "eps_est":    eps_est,
                    "eps_actual": eps_act,
                    "surprise":   surp,
                    "is_future":  eps_act is None,
                })
            return out
        except Exception as exc:
            wait = SLEEP_BASE * (2 ** attempt) + random.uniform(0, 1.5)
            print(f"  [{sym}] ניסיון {attempt + 1}/{MAX_RETRIES} נכשל: {exc} — המתנה {wait:.1f}ש'")
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)
    return None


def load_existing(path):
    """טוען קובץ קיים. מחזיר {(symbol, date_str): record} או {} אם אין קובץ."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            (r["symbol"], r["date"]): r
            for r in data
            if "symbol" in r and "date" in r
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    today = datetime.now(timezone.utc).date()
    lo = today - timedelta(days=DAYS_BACK)
    hi = today + timedelta(days=DAYS_FWD)

    existing = load_existing(OUTPUT_FILE)
    print(f"נטענו {len(existing)} רשומות קיימות")

    new_records: dict = {}
    success_count = 0
    fail_count = 0

    for sym in CORE_COMPANIES:
        print(f"מושך: {sym}...", end=" ", flush=True)
        records = fetch_one(sym, lo, hi)
        if records is None:
            print("כישלון")
            fail_count += 1
        else:
            for r in records:
                new_records[(r["symbol"], r["date"])] = r
            print(f"{len(records)} רשומות")
            success_count += 1
        time.sleep(SLEEP_BASE + random.uniform(0, 1.5))

    total = len(CORE_COMPANIES)
    print(f"\nהצליחו {success_count}/{total} · נכשלו {fail_count}")

    if success_count < total * MIN_SUCCESS_RATIO:
        print(
            f"⛔ פחות מ-{MIN_SUCCESS_RATIO:.0%} הצליחו — "
            f"הקובץ לא יעודכן כדי לשמור על הנתונים הקיימים."
        )
        sys.exit(1)

    # מיזוג: חדש גובר על קיים לאותו (symbol, date)
    merged = {**existing, **new_records}

    # סנן לחלון הרלוונטי בלבד
    final = [
        r for r in merged.values()
        if lo.isoformat() <= r["date"] <= hi.isoformat()
    ]
    final.sort(key=lambda r: (r["date"], r["symbol"]))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"✓ נשמרו {len(final)} רשומות ל-{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
