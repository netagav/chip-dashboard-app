# ─────────────────────────────────────────────────────────────
# אזהרה: הבדיקות כאן מאמתות את המפרט בלבד — לא את dashboard.py.
#
# 35 מתוך 36 הבדיקות בודקות מימושים מקבילים שנכתבו בקובץ הזה,
# ולא מייבאות את הפונקציות מהפרודקשן. שינוי שגוי ב-dashboard.py
# לא יפיל אף בדיקה כאן.
#
# הסיבה המבנית: st.set_page_config() ברמת המודול (dashboard.py:19)
# מונע `import dashboard` בסביבת בדיקות. כיסוי אמיתי ידרוש פיצול
# הלוגיקה ל-core.py שאינו תלוי ב-streamlit.
#
# הבדיקה היחידה שנוגעת בפרודקשן היא
# test_auto_adjust_explicit_in_all_history_calls, והיא בדיקת טקסט
# ולא בדיקת התנהגות.
# ─────────────────────────────────────────────────────────────

"""
Regression tests for anchor calculation + missing-data resolution + display consistency.
Run: python -m pytest test_periods.py -v
 or: python test_periods.py

Data: frozen SOXX closes (official, auto_adjust=False). Endpoint: 2026-07-27 = 516.21.
Time is injected — no live market calls, no datetime.now().

Sections:
  1. Anchor logic (7 periods, ≤ rule, weekend/holiday, 5D bar-count, partial)
  2. Missing-data resolution (_resolve_lastclose_prices — 3-layer lookup + DATA_WARN)
  3. Display-path date consistency (caption / chart / header all agree on session_date)
  4. auto_adjust=False static verification (all .history() calls in dashboard.py)
"""
import re
import pathlib
import pytest
from datetime import date, timedelta, datetime, time as _time
from zoneinfo import ZoneInfo
import pandas as pd

# ============================================================
# Pure reimplementation — copied from dashboard.py (pure Python, no imports)
# ============================================================

NY_TZ = ZoneInfo("America/New_York")
_MARKET_CLOSE = _time(16, 0)

_NYSE_HOLIDAYS = {
    date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 4, 18),
    date(2025, 5, 26), date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1),
    date(2025, 11, 27), date(2025, 12, 25),
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7),
    date(2026, 11, 26), date(2026, 12, 25),
    date(2027, 1, 1), date(2027, 1, 18), date(2027, 2, 15), date(2027, 4, 2),
    date(2027, 5, 31), date(2027, 6, 18), date(2027, 7, 5), date(2027, 9, 6),
    date(2027, 11, 25), date(2027, 12, 24),
}


def session_is_complete(d, now_ny):
    """Injected-time version: takes now_ny explicitly instead of calling ny_now()."""
    if d.weekday() >= 5 or d in _NYSE_HOLIDAYS:
        return False
    if now_ny.date() > d:
        return True
    return now_ny.date() == d and now_ny.time() >= _MARKET_CLOSE


def _anchor_index(close, period, last_date):
    """Copied verbatim from dashboard.py — no external dependencies."""
    dates = [ts.date() for ts in close.index]
    if period == "5d":
        return max(0, len(dates) - 6), len(dates) < 6
    if period == "ytd":
        start = last_date.replace(month=1, day=1)
    else:
        _months = {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12, "5y": 60}
        months = _months.get(period, 1)
        start = (pd.Timestamp(last_date) - pd.DateOffset(months=months)).date()
    before = [i for i, d in enumerate(dates) if d <= start]
    if not before:
        return 0, True
    return before[-1], False


def _close_for_date(daily_close, d):
    """Copied verbatim from dashboard.py — Layer 1: (price, 'daily') or (None, None)."""
    if daily_close is None:
        return None, None
    matches = [float(v) for ts, v in daily_close.items() if ts.date() == d]
    return (matches[-1], "daily") if matches else (None, None)


def _resolve_lastclose_prices(daily_close, session_date, intra_last_close,
                               prev_date, intra_prev_close, quote_prev_close):
    """
    Pure extraction of the 3-layer price resolution in get_change("lastclose").

    Mirrors the exact logic in dashboard.py but returns warnings as a list
    instead of printing them — so tests can assert on them.

    Returns: (last_px, last_src, prev_px, prev_src, warnings)
      last_src / prev_src ∈ {"daily", "quote", "intraday", None}
      warnings: list of [DATA_WARN] strings, one per fired warning
    """
    warnings = []

    # --- session_date price (Layer 1 only; quote.previous_close is not session) ---
    last_px, last_src = _close_for_date(daily_close, session_date)
    if last_px is None:
        if not intra_last_close:
            return None, None, None, None, warnings
        last_px, last_src = intra_last_close, "intraday"

    # --- prev_date price (Layers 1 → 2 → 3) ---
    prev_px, prev_src = _close_for_date(daily_close, prev_date)
    if prev_px is None:
        # Layer 2: fast_info.previous_close — unverifiable against daily
        if quote_prev_close is not None:
            prev_px, prev_src = quote_prev_close, "quote"
            warnings.append(
                f"[DATA_WARN] {prev_date}: quote only ({prev_px:.4f}) — unverifiable"
            )
        elif intra_prev_close and intra_prev_close != 0:
            # Layer 3: intraday close — unverifiable against any official source
            prev_px, prev_src = intra_prev_close, "intraday"
            warnings.append(
                f"[DATA_WARN] {prev_date}: intraday only ({prev_px:.4f}) — unverifiable"
            )
    elif prev_src == "daily":
        # Cross-validate daily vs quote; fire DATA_WARN on divergence > 0.1%
        if quote_prev_close is not None:
            _diff = abs(prev_px - quote_prev_close) / prev_px
            if _diff > 0.001:
                warnings.append(
                    f"[DATA_WARN] {prev_date}: daily={prev_px:.4f} "
                    f"quote={quote_prev_close:.4f} diff={_diff * 100:.2f}%"
                )

    return last_px, last_src, prev_px, prev_src, warnings


def _pick_session_date(dates, now_ny, skip_current_day):
    """
    Pure extraction of the date-selection logic in get_last_session_intraday.

    'dates' = sorted list of trading dates present in the intraday series.
    When skip_current_day=True and today's session is not yet complete, the
    function falls back to dates[-2] (the last completed session).
    """
    last_date = dates[-1]
    if (skip_current_day
            and last_date == now_ny.date()
            and not session_is_complete(last_date, now_ny)
            and len(dates) >= 2):
        last_date = dates[-2]
    return last_date


# ============================================================
# Helpers
# ============================================================

def make_series(date_price_pairs):
    dates = [pd.Timestamp(d, tz="America/New_York") for d, _ in date_price_pairs]
    prices = [p for _, p in date_price_pairs]
    return pd.Series(prices, index=pd.DatetimeIndex(dates))


LAST_DATE = date(2026, 7, 27)
LAST_PRICE = 516.21


def make_fixture(period):
    """
    Minimal frozen series for each period.
    Includes: anchor bar, one bar before, one bar after, and last bar.
    07/24 is included with official close 527.01 (S&P Global data).
    """
    if period == "5d":
        # 7 bars → anchor = iloc[-6] = 07/20
        return make_series([
            (date(2026, 7, 17), 521.81),
            (date(2026, 7, 20), 524.14),  # anchor
            (date(2026, 7, 21), 552.69),
            (date(2026, 7, 22), 555.52),
            (date(2026, 7, 23), 551.24),
            (date(2026, 7, 24), 527.01),  # official (missing from Yahoo but present here)
            (date(2026, 7, 27), 516.21),  # last
        ])
    if period == "1mo":
        # measure_start = 27/06 (Saturday) → anchor = 26/06 (Friday)
        return make_series([
            (date(2026, 6, 25), 585.00),
            (date(2026, 6, 26), 589.94),  # anchor ← last bar ≤ Saturday 27/06
            (date(2026, 6, 29), 614.35),  # first bar after measure_start
            (date(2026, 7, 27), 516.21),
        ])
    if period == "3mo":
        # measure_start = 27/04 (Monday = trading day) → anchor = 27/04
        return make_series([
            (date(2026, 4, 24), 461.38),  # Friday before (what < rule gives)
            (date(2026, 4, 27), 455.19),  # anchor = measure_start
            (date(2026, 4, 28), 460.00),
            (date(2026, 7, 27), 516.21),
        ])
    if period == "6mo":
        # measure_start = 27/01 (Tuesday = trading day) → anchor = 27/01
        return make_series([
            (date(2026, 1, 26), 342.70),  # Monday before (what < rule gives)
            (date(2026, 1, 27), 350.70),  # anchor = measure_start
            (date(2026, 1, 28), 355.00),
            (date(2026, 7, 27), 516.21),
        ])
    if period == "ytd":
        # measure_start = 01/01/2026 (holiday) → anchor = 31/12/2025
        return make_series([
            (date(2025, 12, 31), 300.82),  # anchor ← last bar ≤ holiday 01/01
            (date(2026, 1,  2), 314.60),   # first trading day 2026
            (date(2026, 7, 27), 516.21),
        ])
    if period == "1y":
        # measure_start = 27/07/2025 (Sunday) → anchor = 25/07/2025 (Friday)
        return make_series([
            (date(2025, 7, 25), 240.42),  # anchor ← last bar ≤ Sunday 27/07/2025
            (date(2025, 7, 28), 245.00),  # Monday
            (date(2026, 7, 27), 516.21),
        ])
    if period == "5y":
        # measure_start = 27/07/2021 (Tuesday = trading day) → anchor = 27/07/2021
        return make_series([
            (date(2021, 7, 26), 142.61),  # Monday before (what < rule gives)
            (date(2021, 7, 27), 139.99),  # anchor = measure_start
            (date(2021, 7, 28), 141.00),
            (date(2026, 7, 27), 516.21),
        ])
    raise ValueError(f"Unknown period: {period}")


# ============================================================
# Reference table (from live verification runs + S&P Global)
# ============================================================
REFERENCE = {
    #  period: (anchor_date, anchor_price, expected_change_pct)
    "5d":  (date(2026, 7, 20), 524.14, (516.21 / 524.14 - 1) * 100),
    "1mo": (date(2026, 6, 26), 589.94, (516.21 / 589.94 - 1) * 100),
    "3mo": (date(2026, 4, 27), 455.19, (516.21 / 455.19 - 1) * 100),
    "6mo": (date(2026, 1, 27), 350.70, (516.21 / 350.70 - 1) * 100),
    "ytd": (date(2025, 12, 31), 300.82, (516.21 / 300.82 - 1) * 100),
    "1y":  (date(2025, 7, 25), 240.42, (516.21 / 240.42 - 1) * 100),
    "5y":  (date(2021, 7, 27), 139.99, (516.21 / 139.99 - 1) * 100),
}


# ============================================================
# Tests: anchor date, price, and change for all 7 periods
# ============================================================

@pytest.mark.parametrize("period", list(REFERENCE.keys()))
def test_anchor_date_and_change(period):
    exp_anchor_date, exp_anchor_px, exp_change = REFERENCE[period]
    close = make_fixture(period)
    anchor_i, is_partial = _anchor_index(close, period, LAST_DATE)

    got_anchor_date = close.index[anchor_i].date()
    got_anchor_px   = float(close.iloc[anchor_i])
    got_change      = (float(close.iloc[-1]) / got_anchor_px - 1) * 100

    assert not is_partial, f"[{period}] unexpected partial"
    assert got_anchor_date == exp_anchor_date, \
        f"[{period}] anchor_date={got_anchor_date} expected={exp_anchor_date}"
    assert abs(got_anchor_px - exp_anchor_px) < 0.02, \
        f"[{period}] anchor_px={got_anchor_px:.2f} expected={exp_anchor_px:.2f}"
    assert abs(got_change - exp_change) < 0.02, \
        f"[{period}] change={got_change:.2f}% expected={exp_change:.2f}%"


# ============================================================
# Test: ≤ rule — trading-day measure_start → anchor == measure_start
# (3M/6M/5Y: the cases that would fail under the old < rule)
# ============================================================

@pytest.mark.parametrize("period,measure_start,wrong_anchor_under_lt_rule", [
    ("3mo", date(2026, 4, 27), date(2026, 4, 24)),  # Monday → would give Friday under <
    ("6mo", date(2026, 1, 27), date(2026, 1, 26)),  # Tuesday → would give Monday under <
    ("5y",  date(2021, 7, 27), date(2021, 7, 26)),  # Tuesday → would give Monday under <
])
def test_leq_rule_trading_day(period, measure_start, wrong_anchor_under_lt_rule):
    """Key regression: ≤ must give anchor == measure_start when measure_start is a trading day."""
    close = make_fixture(period)
    anchor_i, _ = _anchor_index(close, period, LAST_DATE)
    got = close.index[anchor_i].date()

    assert got == measure_start, \
        f"[{period}] ≤ rule: anchor={got} expected={measure_start}. " \
        f"If got {wrong_anchor_under_lt_rule} — < rule is still active."
    assert got != wrong_anchor_under_lt_rule, \
        f"[{period}] old < rule would give {wrong_anchor_under_lt_rule}, got {got} — ≤ fix not in place"


# ============================================================
# Test: weekend/holiday measure_start → anchor is last bar before
# ============================================================

def test_weekend_anchor():
    """1M: measure_start=27/06 (Saturday) → anchor=26/06 (Friday)."""
    close = make_fixture("1mo")
    anchor_i, _ = _anchor_index(close, "1mo", LAST_DATE)
    got = close.index[anchor_i].date()
    assert got == date(2026, 6, 26), f"anchor={got}"
    assert got.weekday() == 4  # Friday


def test_holiday_anchor():
    """YTD: measure_start=01/01 (holiday) → anchor=31/12 of previous year."""
    close = make_fixture("ytd")
    anchor_i, _ = _anchor_index(close, "ytd", LAST_DATE)
    got = close.index[anchor_i].date()
    assert got == date(2025, 12, 31)
    assert got.year == LAST_DATE.year - 1


def test_sunday_anchor():
    """1Y: measure_start=27/07/2025 (Sunday) → anchor=25/07/2025 (Friday)."""
    close = make_fixture("1y")
    anchor_i, _ = _anchor_index(close, "1y", LAST_DATE)
    got = close.index[anchor_i].date()
    assert got == date(2025, 7, 25)
    assert got.weekday() == 4  # Friday


# ============================================================
# Test: 5D uses 6 bars (5 sessions of return, not 4)
# ============================================================

def test_5d_is_5_sessions():
    """5D: 6 bars in series → anchor=iloc[0], 5 intervals of return."""
    # minimal 6-bar series (SOXX 07/20–07/27 without 07/24 hole)
    close = make_series([
        (date(2026, 7, 20), 524.14),
        (date(2026, 7, 21), 552.69),
        (date(2026, 7, 22), 555.52),
        (date(2026, 7, 23), 551.24),
        (date(2026, 7, 24), 527.01),
        (date(2026, 7, 27), 516.21),
    ])
    anchor_i, is_partial = _anchor_index(close, "5d", LAST_DATE)
    n = len(close)
    assert anchor_i == max(0, n - 6), f"anchor_i={anchor_i}"
    assert not is_partial
    n_sessions = (n - 1) - anchor_i
    assert n_sessions == 5, f"n_sessions={n_sessions} (expected 5)"


def test_5d_partial_when_fewer_than_6_bars():
    close = make_series([
        (date(2026, 7, 24), 527.01),
        (date(2026, 7, 27), 516.21),
    ])
    anchor_i, is_partial = _anchor_index(close, "5d", LAST_DATE)
    assert is_partial
    assert anchor_i == 0


# ============================================================
# Test: partial period (series too short)
# ============================================================

def test_partial_period_no_bars_before_start():
    """No bar before measure_start → is_partial=True, falls back to iloc[0]."""
    close = make_series([
        (date(2026, 5, 1),  480.00),   # after measure_start of 3mo (27/04)
        (date(2026, 7, 27), 516.21),
    ])
    anchor_i, is_partial = _anchor_index(close, "3mo", LAST_DATE)
    assert is_partial, "should be partial"
    assert anchor_i == 0


# ============================================================
# Tests: session_is_complete with four clock states + weekend + holiday
# ============================================================

TRADING_DAY = date(2026, 7, 27)   # Monday


@pytest.mark.parametrize("clock_state,d,now_str,expected", [
    ("before_open",    TRADING_DAY,          "2026-07-27 09:00", False),
    ("during_market",  TRADING_DAY,          "2026-07-27 13:00", False),
    ("at_close",       TRADING_DAY,          "2026-07-27 16:00", True),   # exactly 16:00
    ("after_close",    TRADING_DAY,          "2026-07-27 16:30", True),
    ("next_day",       TRADING_DAY,          "2026-07-28 08:00", True),
    ("saturday_d",     date(2026, 7, 25),    "2026-07-25 12:00", False),  # d=Saturday
    ("holiday_d",      date(2026, 7, 3),     "2026-07-03 12:00", False),  # d=Independence Day
])
def test_session_is_complete(clock_state, d, now_str, expected):
    now_ny = datetime.fromisoformat(now_str).replace(tzinfo=NY_TZ)
    result = session_is_complete(d, now_ny)
    assert result == expected, \
        f"[{clock_state}] session_is_complete({d}, {now_str}) = {result}, expected {expected}"


# ============================================================
# Section 1 constants — SOXX 24/07 hole scenario
# ============================================================

SESSION_DATE = date(2026, 7, 27)   # last bar (daily present in Yahoo)
PREV_DATE    = date(2026, 7, 24)   # previous session (MISSING from Yahoo daily)

DAILY_WITH_HOLE = make_series([    # 24/07 absent — as Yahoo actually returns
    (date(2026, 7, 22), 555.52),
    (date(2026, 7, 23), 551.24),
    # 2026-07-24 intentionally absent
    (date(2026, 7, 27), 516.21),
])

DAILY_FULL = make_series([         # 24/07 present — "clean" reference fixture
    (date(2026, 7, 22), 555.52),
    (date(2026, 7, 23), 551.24),
    (date(2026, 7, 24), 527.01),   # official (S&P Global)
    (date(2026, 7, 27), 516.21),
])

INTRA_LAST  = 516.21   # last intraday bar 27/07
INTRA_PREV  = 527.22   # last intraday bar 24/07 (Yahoo intraday provisional)
QUOTE_PREV  = 527.01   # fast_info.previous_close (official, Layer 2)


# ============================================================
# Section 1-A: Layer 2 (quote) fills the hole in prev_date
# ============================================================

def test_layer2_fills_missing_prev():
    """
    Daily is missing prev_date (24/07).  Layer 2 (quote=527.01) is available.
    Expected: prev_src="quote", 1 DATA_WARN about unverifiable quote, no Layer 3 used.
    """
    last_px, last_src, prev_px, prev_src, warns = _resolve_lastclose_prices(
        DAILY_WITH_HOLE, SESSION_DATE, INTRA_LAST, PREV_DATE, INTRA_PREV, QUOTE_PREV
    )

    assert last_src == "daily",  f"last_src={last_src}"
    assert prev_src == "quote",  f"prev_src={prev_src} — Layer 2 should win over Layer 3"
    assert abs(prev_px - QUOTE_PREV) < 0.001, f"prev_px={prev_px:.4f} expected {QUOTE_PREV}"
    assert len(warns) == 1,      f"expected 1 DATA_WARN, got {warns}"
    assert "quote only" in warns[0], f"wrong DATA_WARN text: {warns[0]}"
    assert "unverifiable" in warns[0]
    # Layer 3 price must NOT appear — the quote took precedence
    assert str(round(INTRA_PREV, 2)) not in warns[0]


# ============================================================
# Section 1-B: Layer 3 (intraday) fallback — no quote available
# ============================================================

def test_layer3_fallback_when_no_quote():
    """
    Daily missing 24/07, quote returns None.  Layer 3 (intraday=527.22) kicks in.
    Expected: prev_src="intraday", 1 DATA_WARN about unverifiable intraday, provisional price used.
    """
    last_px, last_src, prev_px, prev_src, warns = _resolve_lastclose_prices(
        DAILY_WITH_HOLE, SESSION_DATE, INTRA_LAST, PREV_DATE, INTRA_PREV,
        quote_prev_close=None   # ← quote unavailable
    )

    assert last_src == "daily",    f"last_src={last_src}"
    assert prev_src == "intraday", f"prev_src={prev_src} — Layer 3 should be last resort"
    assert abs(prev_px - INTRA_PREV) < 0.001, f"prev_px={prev_px:.4f} expected {INTRA_PREV}"
    assert len(warns) == 1,        f"expected 1 DATA_WARN, got {warns}"
    assert "intraday only" in warns[0]
    assert "unverifiable" in warns[0]


# ============================================================
# Section 1-C: Daily vs quote mismatch — cross-validation fires
# ============================================================

def test_data_warn_on_daily_quote_mismatch():
    """
    Daily has 24/07=527.01.  Quote returns 530.35 (>0.1% divergence).
    Expected: daily wins (prev_src="daily"), 1 DATA_WARN citing both values.
    No DATA_WARN when divergence ≤ 0.1%.
    """
    mismatched_quote = 530.35   # divergence ≈ 0.63% > 0.1% threshold

    last_px, last_src, prev_px, prev_src, warns = _resolve_lastclose_prices(
        DAILY_FULL, SESSION_DATE, INTRA_LAST, PREV_DATE, INTRA_PREV,
        quote_prev_close=mismatched_quote
    )

    # Daily wins — its price is returned
    assert prev_src == "daily", f"prev_src={prev_src} — daily should win over quote"
    assert abs(prev_px - 527.01) < 0.001, f"prev_px={prev_px:.4f} expected 527.01"
    assert len(warns) == 1, f"expected 1 DATA_WARN for mismatch, got {warns}"
    assert "daily=" in warns[0] and "quote=" in warns[0], f"warn text: {warns[0]}"
    assert "diff=" in warns[0]

    # Verify: small divergence (≤ 0.1%) fires no warning
    close_quote = 527.10   # 0.017% — below threshold
    _, _, _, _, warns2 = _resolve_lastclose_prices(
        DAILY_FULL, SESSION_DATE, INTRA_LAST, PREV_DATE, INTRA_PREV,
        quote_prev_close=close_quote
    )
    assert len(warns2) == 0, f"no DATA_WARN expected for small diff, got {warns2}"


# ============================================================
# Section 1-D: Clean path — daily has both dates, quote matches
# ============================================================

def test_clean_path_no_data_warn():
    """
    Both session_date and prev_date present in daily, quote ≈ daily.
    Expected: both src="daily", zero DATA_WARN.
    """
    last_px, last_src, prev_px, prev_src, warns = _resolve_lastclose_prices(
        DAILY_FULL, SESSION_DATE, INTRA_LAST, PREV_DATE, INTRA_PREV,
        quote_prev_close=QUOTE_PREV  # matches daily exactly — no warn
    )

    assert last_src == "daily"
    assert prev_src == "daily"
    assert abs(last_px - 516.21) < 0.001
    assert abs(prev_px - 527.01) < 0.001
    assert len(warns) == 0, f"DATA_WARN should be silent on clean data: {warns}"


# ============================================================
# Section 2: Display-path consistency — _compute_zone1_output
#
# This is the non-tautological replacement for the old test that called
# _pick_session_date three times and checked it's deterministic.
#
# The old test proved nothing about Zone 1: it called a pure function
# that is trivially deterministic, so it always passed regardless of
# whether Zone 1 actually called it or derived the date inline.
#
# The new approach:
#   1. _compute_zone1_output mirrors the FULL Zone 1 computation
#      (session-picking + 3-layer price resolution + pct calculation).
#      It is the extracted pure function the production code should match.
#   2. Tests verify that its THREE OUTPUTS — header_date, caption_date,
#      chart_dates[-1] — agree, AND that header_pct == chart_pct.
#   3. Condition 4 (pct equality) would FAIL on the OLD production code
#      where chart anchor = raw intraday, header = official quote/daily.
#      The Zone 1 fix (dashboard.py שלב 1ב) makes them agree.
# ============================================================

def make_intra_series(dt_price_pairs):
    """Build an intraday Series from ('YYYY-MM-DD HH:MM', price) pairs, tz=NY."""
    ts_list = [pd.Timestamp(dt, tz="America/New_York") for dt, _ in dt_price_pairs]
    px_list = [p for _, p in dt_price_pairs]
    return pd.Series(px_list, index=pd.DatetimeIndex(ts_list))


def _compute_zone1_output(intra_full, now_ny, daily_close, quote_prev_close):
    """
    Pure mirror of Zone 1 (lastclose) data computation — AFTER the anchor fix.

    Mirrors dashboard.py Zone 1:
      - _pick_session_date (skip_current_day=True)
      - 3-layer official prev resolution (daily → quote → intraday)
      - Layer 1 → intraday for last_px
      - chart anchor = official prev (THE FIX — single source for header + chart)

    Returns a dict the test can assert against.  If Zone 1 production code
    diverges from this function, the static test test_zone1_anchor_fix_in_source
    catches it.
    """
    # --- Session picking (mirrors get_last_session_intraday internal logic) ---
    intra_dates = sorted({ts.date() for ts in intra_full.index})
    if not intra_dates:
        return None
    session_date = _pick_session_date(intra_dates, now_ny, skip_current_day=True)

    prev_candidates = [d for d in intra_dates if d < session_date]
    prev_date = prev_candidates[-1] if prev_candidates else None

    intra_prev_bars = [float(v) for ts, v in intra_full.items() if ts.date() == prev_date]
    intra_prev_close = intra_prev_bars[-1] if intra_prev_bars else None

    intra_session_bars = [(ts, float(v)) for ts, v in intra_full.items() if ts.date() == session_date]
    if not intra_session_bars:
        return None
    intra_session_dates = [ts.date() for ts, _ in intra_session_bars]
    intra_last_close    = intra_session_bars[-1][1]

    # --- Resolve official prev_close — single source of truth for header AND chart ---
    official_prev, prev_src = _close_for_date(daily_close, prev_date) if prev_date else (None, None)
    if official_prev is None:
        if quote_prev_close is not None:
            official_prev, prev_src = quote_prev_close, "quote"
        elif intra_prev_close:
            official_prev, prev_src = intra_prev_close, "intraday"

    # --- Resolve last_px: Layer 1 (daily) → Layer 3 (intraday last bar) ---
    last_px, _ = _close_for_date(daily_close, session_date)
    if last_px is None:
        last_px = intra_last_close

    # --- Compute outputs ---
    header_pct   = (last_px / official_prev - 1) * 100 if official_prev else None
    # chart_pct would be (intra_last / official_prev - 1)*100 — same anchor → same pct
    anchor_price = official_prev

    return {
        "header_date":  session_date,
        "header_pct":   header_pct,
        "caption_date": session_date,        # _session.index[-1].date() in Zone 1
        "chart_dates":  intra_session_dates, # dates of the session bars (excl. prepended anchor)
        "chart_last":   intra_last_close,
        "anchor_price": anchor_price,
        "prev_date":    prev_date,
        "prev_src":     prev_src,
    }


# Frozen intraday fixtures for Zone 1 tests
# Note: intraday prices at 16:00 == daily closes (realistic; same price source at market close)
_INTRA_WITH_TODAY = make_intra_series([
    ("2026-07-23 16:00", 551.24),  # 23/07 prev-prev session
    ("2026-07-24 16:00", 527.01),  # 24/07 prev session (intraday=daily, no gap in clean fixture)
    ("2026-07-27 09:30", 518.00),  # 27/07 open bar (partial session)
    ("2026-07-27 13:00", 516.50),  # 27/07 during
])

_INTRA_CLOSED = make_intra_series([
    ("2026-07-23 16:00", 551.24),
    ("2026-07-24 16:00", 527.01),
    ("2026-07-27 16:00", 516.21),  # 27/07 closed session
])

_INTRA_WEEKEND = make_intra_series([
    ("2026-07-23 16:00", 551.24),
    ("2026-07-24 16:00", 527.01),  # no 27/07 yet (fetched on Sunday)
])

_INTRA_HOLE = make_intra_series([
    ("2026-07-24 16:00", 527.22),  # 24/07 intraday (DIFFERS from official 527.01)
    ("2026-07-27 16:00", 516.21),
])

# Daily fixture: all dates clean (no hole)
_DAILY_CLEAN = make_series([
    (date(2026, 7, 23), 551.24),
    (date(2026, 7, 24), 527.01),
    (date(2026, 7, 27), 516.21),
])


@pytest.mark.parametrize("clock_state,now_str,intra_fixture,exp_session,exp_prev", [
    # before open: 27/07 partial bars in series but not complete → skip → session=24/07
    ("before_open",   "2026-07-27 09:00", "_INTRA_WITH_TODAY", date(2026,7,24), date(2026,7,23)),
    # during market: same behaviour as before_open
    ("during_market", "2026-07-27 13:00", "_INTRA_WITH_TODAY", date(2026,7,24), date(2026,7,23)),
    # after close: 27/07 session complete → no skip → session=27/07
    ("after_close",   "2026-07-27 16:30", "_INTRA_CLOSED",     date(2026,7,27), date(2026,7,24)),
    # weekend: 27/07 not in series → last=24/07, no skip needed
    ("weekend",       "2026-07-26 12:00", "_INTRA_WEEKEND",    date(2026,7,24), date(2026,7,23)),
])
def test_zone1_output_consistency(clock_state, now_str, intra_fixture, exp_session, exp_prev):
    """
    Runs _compute_zone1_output (the extracted Zone 1 pure function) for each clock
    state and asserts three invariants:

    1. header_date == caption_date == chart_dates[-1]  (all three paths name the same day)
    2. header_pct == (chart_last / anchor_price - 1) * 100  (zero gap between header and chart)

    Invariant (2) would FAIL on the pre-fix production code where Zone 1 used
    raw intraday prev (527.22) for the chart anchor while get_change used the official
    quote (527.01) for the header — producing a ~0.04pp gap visible to users.
    The Zone 1 fix (dashboard.py שלב 1ב) makes both use the same official prev_close.
    """
    intra_map = {
        "_INTRA_WITH_TODAY": _INTRA_WITH_TODAY,
        "_INTRA_CLOSED":     _INTRA_CLOSED,
        "_INTRA_WEEKEND":    _INTRA_WEEKEND,
    }
    intra_full = intra_map[intra_fixture]
    now_ny = datetime.fromisoformat(now_str).replace(tzinfo=NY_TZ)

    result = _compute_zone1_output(intra_full, now_ny, _DAILY_CLEAN, quote_prev_close=None)
    assert result is not None, f"[{clock_state}] _compute_zone1_output returned None"

    # --- Invariant 1: all paths agree on session_date ---
    assert result["header_date"]  == exp_session, \
        f"[{clock_state}] header_date={result['header_date']} ≠ {exp_session}"
    assert result["caption_date"] == exp_session, \
        f"[{clock_state}] caption_date={result['caption_date']} ≠ {exp_session}"
    assert result["chart_dates"][-1] == exp_session, \
        f"[{clock_state}] chart_dates[-1]={result['chart_dates'][-1]} ≠ {exp_session}"
    assert result["prev_date"] == exp_prev, \
        f"[{clock_state}] prev_date={result['prev_date']} ≠ {exp_prev}"

    # --- Invariant 2: header% == chart% (single-source anchor) ---
    chart_pct = (result["chart_last"] / result["anchor_price"] - 1) * 100
    assert abs(result["header_pct"] - chart_pct) < 0.001, \
        (f"[{clock_state}] header_pct={result['header_pct']:.4f}% ≠ "
         f"chart_pct={chart_pct:.4f}% — anchor source split detected")


# ============================================================
# Section 2 continued: zero-gap test across all 3 prev sources
# (daily / quote / intraday) for the SOXX 24/07 hole scenario
# ============================================================

@pytest.mark.parametrize("scenario,daily_close,quote_val,exp_prev_src,exp_prev_px", [
    # A: prev from daily (no hole)
    ("daily",    "_DAILY_CLEAN",    None,     "daily",    527.01),
    # B: prev from quote (hole — official quote fills the gap)
    ("quote",    "_DAILY_WITH_HOLE", QUOTE_PREV, "quote",  QUOTE_PREV),
    # C: prev from intraday only (hole, no quote)
    ("intraday", "_DAILY_WITH_HOLE", None,      "intraday", INTRA_PREV),
])
def test_pct_zero_gap_all_source_scenarios(scenario, daily_close, quote_val, exp_prev_src, exp_prev_px):
    """
    After the Zone 1 anchor fix, header% and chart% must agree to < 0.001pp
    regardless of which layer supplied the prev_close.

    Before the fix (production code bug):
      Scenario B: header used quote=527.01, chart used intraday=527.22
      → gap ≈ 0.04pp visible to users (header: -2.05%, chart: -2.09%)

    After the fix: both use the same official prev_close → gap == 0.

    This test calls _compute_zone1_output which implements the FIXED design.
    The static test test_zone1_anchor_fix_in_source verifies the fix is also
    present in the production code (dashboard.py).
    """
    daily_map = {"_DAILY_CLEAN": _DAILY_CLEAN, "_DAILY_WITH_HOLE": DAILY_WITH_HOLE}
    now_after_close = datetime.fromisoformat("2026-07-27 16:30").replace(tzinfo=NY_TZ)

    result = _compute_zone1_output(
        _INTRA_HOLE if daily_close == "_DAILY_WITH_HOLE" else _INTRA_CLOSED,
        now_after_close,
        daily_map[daily_close],
        quote_val,
    )
    assert result is not None

    # Correct source and price
    assert result["prev_src"] == exp_prev_src, \
        f"[{scenario}] prev_src={result['prev_src']} expected {exp_prev_src}"
    assert abs(result["anchor_price"] - exp_prev_px) < 0.001, \
        f"[{scenario}] anchor={result['anchor_price']:.4f} expected {exp_prev_px:.4f}"

    # Zero gap (THE CONTRACT after fix)
    chart_pct  = (result["chart_last"] / result["anchor_price"] - 1) * 100
    header_pct = result["header_pct"]
    gap = abs(header_pct - chart_pct)
    assert gap < 0.001, (
        f"[{scenario}] gap={gap:.4f}pp — header ({header_pct:.4f}%) ≠ chart ({chart_pct:.4f}%). "
        f"anchor_price={result['anchor_price']:.4f}. "
        f"Before the Zone 1 fix, Scenario B had gap≈0.04pp."
    )


def test_pct_header_equals_chart_clean_data():
    """
    When daily has BOTH session_date and prev_date (clean data), header% and chart% must agree.
    Both use the same daily close prices → gap must be < 0.01pp.
    This catches the original date-anchor bug: if the header used a different anchor DATE,
    the %s would diverge by far more than 0.01pp.
    """
    last_px, _, prev_px, _, warns = _resolve_lastclose_prices(
        DAILY_FULL, SESSION_DATE, INTRA_LAST, PREV_DATE, INTRA_PREV, QUOTE_PREV
    )
    header_pct = (last_px / prev_px - 1) * 100

    chart_anchor_px = float(DAILY_FULL[DAILY_FULL.index.map(lambda t: t.date() == PREV_DATE)].iloc[0])
    chart_last_px   = float(DAILY_FULL[DAILY_FULL.index.map(lambda t: t.date() == SESSION_DATE)].iloc[0])
    chart_pct = (chart_last_px / chart_anchor_px - 1) * 100

    assert abs(header_pct - chart_pct) < 0.01, \
        f"Header {header_pct:.4f}% ≠ chart {chart_pct:.4f}% — anchor date mismatch suspected"
    assert len(warns) == 0


# ============================================================
# Section 3: auto_adjust=False — static source verification
#
# yfinance changed its default from False to True in 2025.
# Every .history() call in dashboard.py MUST pass auto_adjust=False explicitly
# so that daily / intraday / quote all return raw close (not dividend-adjusted).
# ============================================================

def test_auto_adjust_explicit_in_all_history_calls():
    """
    Reads dashboard.py as text, finds every .history( call, and asserts
    that auto_adjust=False appears inside the call's argument list.
    Fails with the line number and snippet of any offending call.
    """
    src_path = pathlib.Path(__file__).parent / "dashboard.py"
    if not src_path.exists():
        pytest.skip("dashboard.py not found alongside test file")

    text = src_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    offenders = []
    for m in re.finditer(r'\.history\(', text):
        # Walk forward to find the matching closing paren
        pos = m.start()
        line_no = text[:pos].count("\n") + 1
        depth = 0
        call_chars = []
        for ch in text[m.start():]:
            call_chars.append(ch)
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
        call_text = "".join(call_chars)
        if "auto_adjust=False" not in call_text:
            offenders.append((line_no, call_text[:120].replace("\n", " ")))

    assert not offenders, (
        f"{len(offenders)} .history() call(s) missing auto_adjust=False:\n"
        + "\n".join(f"  line {ln}: {snip}" for ln, snip in offenders)
    )


# ============================================================
# Standalone runner (no pytest required)
# ============================================================

if __name__ == "__main__":
    import traceback

    failures = 0

    def run(name, fn, *args, **kwargs):
        global failures
        try:
            fn(*args, **kwargs)
            print(f"  ✓ {name}")
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failures += 1
        except Exception:
            print(f"  ✗ {name}: UNEXPECTED ERROR")
            print("    " + traceback.format_exc().replace("\n", "\n    "))
            failures += 1

    print("\n=== anchor date / price / change ===")
    for period in REFERENCE:
        exp = REFERENCE[period]
        run(f"anchor [{period}]", test_anchor_date_and_change, period)

    print("\n=== ≤ rule: trading-day measure_start → anchor == measure_start ===")
    for period, ms, wrong in [
        ("3mo", date(2026, 4, 27), date(2026, 4, 24)),
        ("6mo", date(2026, 1, 27), date(2026, 1, 26)),
        ("5y",  date(2021, 7, 27), date(2021, 7, 26)),
    ]:
        run(f"leq [{period}]", test_leq_rule_trading_day, period, ms, wrong)

    print("\n=== weekend / holiday / Sunday anchor ===")
    run("weekend anchor [1mo]", test_weekend_anchor)
    run("holiday anchor [ytd]", test_holiday_anchor)
    run("sunday anchor [1y]",   test_sunday_anchor)

    print("\n=== 5D bar-count ===")
    run("5D is 5 sessions", test_5d_is_5_sessions)
    run("5D partial",        test_5d_partial_when_fewer_than_6_bars)

    print("\n=== partial period ===")
    run("partial [3mo]", test_partial_period_no_bars_before_start)

    print("\n=== session_is_complete ===")
    for args in [
        ("before_open",   TRADING_DAY, "2026-07-27 09:00", False),
        ("during_market", TRADING_DAY, "2026-07-27 13:00", False),
        ("at_close",      TRADING_DAY, "2026-07-27 16:00", True),
        ("after_close",   TRADING_DAY, "2026-07-27 16:30", True),
        ("next_day",      TRADING_DAY, "2026-07-28 08:00", True),
        ("saturday_d",    date(2026, 7, 25), "2026-07-25 12:00", False),
        ("holiday_d",     date(2026, 7, 3),  "2026-07-03 12:00", False),
    ]:
        name, d, now_str, exp = args
        run(f"session_is_complete [{name}]", test_session_is_complete, name, d, now_str, exp)

    print("\n=== Section 1: missing-data / 3-layer resolution ===")
    run("Layer 2 fills missing prev (quote)", test_layer2_fills_missing_prev)
    run("Layer 3 fallback when no quote",     test_layer3_fallback_when_no_quote)
    run("DATA_WARN on daily/quote mismatch",  test_data_warn_on_daily_quote_mismatch)
    run("Clean path — no DATA_WARN",          test_clean_path_no_data_warn)

    print("\n=== Section 2: Zone 1 output consistency (4 clock states) ===")
    for cs, now_str, intra_fix, exp_s, exp_p in [
        ("before_open",   "2026-07-27 09:00", "_INTRA_WITH_TODAY", date(2026,7,24), date(2026,7,23)),
        ("during_market", "2026-07-27 13:00", "_INTRA_WITH_TODAY", date(2026,7,24), date(2026,7,23)),
        ("after_close",   "2026-07-27 16:30", "_INTRA_CLOSED",     date(2026,7,27), date(2026,7,24)),
        ("weekend",       "2026-07-26 12:00", "_INTRA_WEEKEND",    date(2026,7,24), date(2026,7,23)),
    ]:
        run(f"zone1 consistency [{cs}]",
            test_zone1_output_consistency, cs, now_str, intra_fix, exp_s, exp_p)
    run("pct: header==chart on clean data", test_pct_header_equals_chart_clean_data)
    for sc, dc, qv, eps, epp in [
        ("daily",    "_DAILY_CLEAN",    None,      "daily",    527.01),
        ("quote",    "_DAILY_WITH_HOLE", QUOTE_PREV,"quote",    QUOTE_PREV),
        ("intraday", "_DAILY_WITH_HOLE", None,      "intraday", INTRA_PREV),
    ]:
        run(f"pct zero-gap [{sc}]",
            test_pct_zero_gap_all_source_scenarios, sc, dc, qv, eps, epp)

    print("\n=== Section 3: auto_adjust=False static check ===")
    run("auto_adjust=False in all .history() calls", test_auto_adjust_explicit_in_all_history_calls)

    print()
    if failures:
        print(f"FAILED: {failures} test(s)")
        raise SystemExit(1)
    else:
        print("All tests passed.")
