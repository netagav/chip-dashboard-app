"""
fetch_earnings_calendar.py — הרצה יומית דרך GitHub Actions.
מושך earnings_dates, דירוגי אנליסטים והיסטוריית הכנסות לכל הסימבולים,
ממזג עם הקובץ הקיים וכותב earnings_calendar.json.

חשוב: CORE_COMPANIES ו-VALUE_CHAIN_SYMBOLS חייבות להישאר
מסונכרנות עם dashboard.py.
"""
import json
import math
import random
import sys
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf

# --- שמור מסונכרן עם CORE_COMPANIES ב-dashboard.py ---
CORE_COMPANIES = sorted([
    "ASML", "AMAT", "LRCX", "KLAC", "NVDA", "AMD", "TSM", "INTC", "MU",
    "TXN", "ADI", "AVGO", "QCOM", "MRVL", "ARM",
    "TSEM", "NVMI", "CAMT",
    "MSFT", "META", "GOOGL", "AMZN", "ORCL",
    "005930.KS", "000660.KS",
])

# --- שמור מסונכרן עם value_chain ב-dashboard.py ---
VALUE_CHAIN_SYMBOLS = {
    "SHECY", "SUOPY", "ENTG",
    "SNPS", "CDNS", "ARM",
    "NVDA", "AMD", "QCOM",
    "AVGO", "COHR", "LITE", "MRVL",
    "INTC", "TXN", "ADI", "NXPI", "STM", "ON", "IFNNY", "RNECY", "MCHP",
    "MU", "WDC", "SNDK", "STX", "005930.KS", "000660.KS",
    "ASML", "AMAT", "LRCX", "TOELY", "ASMIY",
    "KLAC", "ONTO", "NVMI", "CAMT",
    "TSM", "GFS", "UMC", "TSEM",
    "AMKR", "TER", "ATEYY", "BESIY", "AEIS",
    "SMCI", "DELL", "HPE", "VRT", "ETN", "ANET",
}

ALL_SYMBOLS = sorted(set(CORE_COMPANIES) | VALUE_CHAIN_SYMBOLS)

DAYS_BACK = 120
DAYS_FWD = 120
OUTPUT_FILE = "earnings_calendar.json"
MIN_SUCCESS_RATIO = 1 / 3
MAX_RETRIES = 3
SLEEP_BASE = 2.0


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_iso(d):
    if d is None:
        return None
    if hasattr(d, "isoformat"):
        return d.isoformat()[:10]
    return str(d)[:10]


def _retry(fn, sym, label):
    """מריץ fn() עם retry/backoff. מחזיר (result, success)."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(), True
        except Exception as exc:
            wait = SLEEP_BASE * (2 ** attempt) + random.uniform(0, 1.5)
            print(f"  [{sym}:{label}] ניסיון {attempt+1}/{MAX_RETRIES}: {exc} — {wait:.1f}ש'")
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)
    return None, False


# ─────────────────────────── לוח הדוחות ────────────────────────────────────

def fetch_calendar_one(sym, lo, hi):
    def _do():
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
            out.append({
                "date":       d.isoformat(),
                "symbol":     sym,
                "eps_est":    _clean(row.get("EPS Estimate")),
                "eps_actual": eps_act,
                "surprise":   _clean(row.get("Surprise(%)")),
                "is_future":  eps_act is None,
            })
        return out
    result, ok = _retry(_do, sym, "calendar")
    return result if ok else None


# ─────────────────────────── דירוגים ────────────────────────────────────────

def fetch_price_targets(sym):
    def _do():
        t = yf.Ticker(sym)
        apt = getattr(t, "analyst_price_targets", None)
        if apt is not None:
            mean = apt.get("mean"); low = apt.get("low"); high = apt.get("high")
            if not mean or not low or not high:
                return None
            return {
                "current": _clean(apt.get("current")), "low": _clean(low),
                "mean": _clean(mean), "median": _clean(apt.get("median")),
                "high": _clean(high), "currency": "USD",
            }
        info = t.info or {}
        mean = info.get("targetMeanPrice"); low = info.get("targetLowPrice")
        high = info.get("targetHighPrice")
        if not mean or not low or not high:
            return None
        return {
            "current": _clean(info.get("currentPrice")), "low": _clean(low),
            "mean": _clean(mean), "median": _clean(info.get("targetMedianPrice")),
            "high": _clean(high), "currency": info.get("currency", "USD"),
        }
    return _retry(_do, sym, "price_targets")


def fetch_recommendation_dist(sym):
    def _do():
        rec = yf.Ticker(sym).recommendations
        if rec is None or rec.empty:
            return None
        row = rec.iloc[0]
        return {
            "strongBuy":  int(row.get("strongBuy",  0) or 0),
            "buy":        int(row.get("buy",         0) or 0),
            "hold":       int(row.get("hold",        0) or 0),
            "sell":       int(row.get("sell",        0) or 0),
            "strongSell": int(row.get("strongSell",  0) or 0),
        }
    return _retry(_do, sym, "rec_dist")


def fetch_upgrades_downgrades(sym):
    def _do():
        df = yf.Ticker(sym).upgrades_downgrades
        if df is None or df.empty:
            return []
        df = df.copy()
        if "GradeDate" in df.columns:
            df["_date"] = pd.to_datetime(df["GradeDate"]).dt.date
        elif "GradeDate" in str(df.index.name):
            df = df.reset_index()
            df["_date"] = pd.to_datetime(df["GradeDate"]).dt.date
        else:
            df = df.reset_index()
            df["_date"] = pd.to_datetime(df.iloc[:, 0]).dt.date
        return [
            {
                "date":       _to_iso(row.get("_date")),
                "firm":       str(row.get("Firm", "") or ""),
                "action":     str(row.get("Action", "") or ""),
                "from_grade": str(row.get("FromGrade", "") or ""),
                "to_grade":   str(row.get("ToGrade", "") or ""),
            }
            for _, row in df.iterrows()
        ]
    return _retry(_do, sym, "upgrades")


# ─────────────────────────── היסטוריית תוצאות ───────────────────────────────

def fetch_eps_history(sym):
    def _do():
        df = yf.Ticker(sym).earnings_dates
        if df is None or df.empty:
            return []
        reported = df[df["Reported EPS"].notna()]
        return [
            {
                "date":         _to_iso(dt),
                "reported_eps": _clean(row.get("Reported EPS")),
                "eps_estimate": _clean(row.get("EPS Estimate")),
                "surprise_pct": _clean(row.get("Surprise(%)")),
            }
            for dt, row in reported.iterrows()
        ]
    return _retry(_do, sym, "eps_history")


def fetch_quarterly_revenue(sym):
    def _do():
        qf = yf.Ticker(sym).quarterly_financials
        if qf is None or qf.empty:
            return []
        for name in ("Total Revenue", "TotalRevenue", "Revenue"):
            if name in qf.index:
                row = qf.loc[name].dropna()
                return [
                    {"date": _to_iso(dt), "revenue_b": _clean(float(v) / 1e9), "row_name": name}
                    for dt, v in row.items()
                ]
        return []
    return _retry(_do, sym, "revenue")


# ─────────────────────────── טעינה ומיזוג ───────────────────────────────────

def load_existing(path):
    empty = {"earnings_calendar": [], "ratings": {}, "earnings_history": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            return {**empty, "earnings_calendar": raw}
        return {
            "earnings_calendar": raw.get("earnings_calendar", []),
            "ratings":           raw.get("ratings", {}),
            "earnings_history":  raw.get("earnings_history", {}),
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return empty


def _merge_list(existing, new, key_fn):
    """מיזוג רשימות לפי מפתח; new גובר. ממוין יורד לפי מפתח."""
    merged = {key_fn(r): r for r in existing}
    for r in new:
        merged[key_fn(r)] = r
    return sorted(merged.values(), key=key_fn, reverse=True)


# ─────────────────────────── main ────────────────────────────────────────────

def main():
    today = datetime.now(timezone.utc).date()
    lo = today - timedelta(days=DAYS_BACK)
    hi = today + timedelta(days=DAYS_FWD)

    existing = load_existing(OUTPUT_FILE)
    print(f"קיים: {len(existing['earnings_calendar'])} לוח, "
          f"{len(existing['ratings'])} דירוגים, "
          f"{len(existing['earnings_history'])} היסטוריות")

    # ── לוח הדוחות (CORE_COMPANIES בלבד) ──────────────────────────────────
    print("\n=== לוח הדוחות ===")
    cal_new: dict = {}
    cal_ok = 0
    for sym in CORE_COMPANIES:
        print(f"  {sym}...", end=" ", flush=True)
        records = fetch_calendar_one(sym, lo, hi)
        if records is None:
            print("כישלון")
        else:
            for r in records:
                cal_new[(r["symbol"], r["date"])] = r
            print(str(len(records)))
            cal_ok += 1
        time.sleep(SLEEP_BASE + random.uniform(0, 1.5))

    cal_existing = {(r["symbol"], r["date"]): r for r in existing["earnings_calendar"]}
    cal_merged = {**cal_existing, **cal_new}
    final_calendar = sorted(
        [r for r in cal_merged.values() if lo.isoformat() <= r["date"] <= hi.isoformat()],
        key=lambda r: (r["date"], r["symbol"]),
    )

    # ── דירוגים (ALL_SYMBOLS) ──────────────────────────────────────────────
    print("\n=== דירוגי אנליסטים ===")
    ratings_ok = 0
    final_ratings = dict(existing["ratings"])
    for sym in ALL_SYMBOLS:
        print(f"  {sym}...", end=" ", flush=True)
        old = final_ratings.get(sym, {})

        pt,  ok1 = fetch_price_targets(sym)
        time.sleep(SLEEP_BASE * 0.5 + random.uniform(0, 0.5))
        rd,  ok2 = fetch_recommendation_dist(sym)
        time.sleep(SLEEP_BASE * 0.5 + random.uniform(0, 0.5))
        ud,  ok3 = fetch_upgrades_downgrades(sym)

        if ok1 or ok2 or ok3:
            final_ratings[sym] = {
                "price_targets":       pt  if pt  is not None else old.get("price_targets"),
                "recommendation_dist": rd  if rd  is not None else old.get("recommendation_dist"),
                "upgrades_downgrades": _merge_list(
                    old.get("upgrades_downgrades", []),
                    ud or [],
                    lambda r: (r.get("date", ""), r.get("firm", "")),
                ),
            }
            ratings_ok += 1
            print("OK")
        else:
            print("כישלון")
        time.sleep(SLEEP_BASE + random.uniform(0, 1.5))

    # ── היסטוריית תוצאות (ALL_SYMBOLS) ────────────────────────────────────
    print("\n=== היסטוריית תוצאות ===")
    hist_ok = 0
    final_history = dict(existing["earnings_history"])
    for sym in ALL_SYMBOLS:
        print(f"  {sym}...", end=" ", flush=True)
        old = final_history.get(sym, {})

        eps, ok1 = fetch_eps_history(sym)
        time.sleep(SLEEP_BASE * 0.5 + random.uniform(0, 0.5))
        rev, ok2 = fetch_quarterly_revenue(sym)

        if ok1 or ok2:
            final_history[sym] = {
                "eps_history": _merge_list(
                    old.get("eps_history", []), eps or [],
                    lambda r: r.get("date", ""),
                ),
                "quarterly_revenue": _merge_list(
                    old.get("quarterly_revenue", []), rev or [],
                    lambda r: r.get("date", ""),
                ),
            }
            hist_ok += 1
            print("OK")
        else:
            print("כישלון")
        time.sleep(SLEEP_BASE + random.uniform(0, 1.5))

    # ── בדיקת בטיחות ──────────────────────────────────────────────────────
    total_core = len(CORE_COMPANIES)
    total_all  = len(ALL_SYMBOLS)
    if (cal_ok    < total_core * MIN_SUCCESS_RATIO and
            ratings_ok < total_all  * MIN_SUCCESS_RATIO and
            hist_ok    < total_all  * MIN_SUCCESS_RATIO):
        print(f"\n⛔ כל המקטעים מתחת ל-{MIN_SUCCESS_RATIO:.0%} — הקובץ לא יעודכן.")
        sys.exit(1)

    output = {
        "earnings_calendar": final_calendar,
        "ratings":           final_ratings,
        "earnings_history":  final_history,
        "generated_at":      today.isoformat(),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {len(final_calendar)} לוח · {len(final_ratings)} דירוגים · "
          f"{len(final_history)} היסטוריות → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
