import streamlit as st
import yfinance as yf
import statistics
import math
import os
import json
import hashlib
import pandas as pd
import altair as alt
import plotly.graph_objects as go
from datetime import datetime, timezone

st.set_page_config(page_title="דשבורד שבבים", page_icon="💹", layout="wide")

# ---------- יישור מימין לשמאל ----------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { direction: rtl; }
.block-container { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
h1, h2, h3, h4, h5, h6 { text-align: right; }
[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] { direction: ltr; }
/* כיתובי st.caption (הסברים מתחת לכותרות) — יישור לימין בכל הדשבורד */
[data-testid="stCaptionContainer"], [data-testid="stCaption"], .stCaption {
    direction: rtl;
    text-align: right;
}
[data-testid="stCaptionContainer"] p, [data-testid="stCaption"] p, .stCaption p {
    text-align: right;
}
/* כפתור ניתוח החדשות — בולט וקשור לאזור החדשות */
div[data-testid="stButton"] button {
    background: rgba(59,130,246,0.18);
    border: 1px solid #3b82f6;
    color: #93c5fd;
    font-weight: 700;
    border-radius: 8px;
}
div[data-testid="stButton"] button:hover {
    background: rgba(59,130,246,0.30);
    border-color: #60a5fa;
    color: #ffffff;
}
/* מתג "פרטים, מניות וחדשות" — עיצוב בולט וברור, כמו כפתור-פס */
div[data-testid="stToggle"] {
    background: rgba(124,58,237,0.10);
    border: 1px solid rgba(124,58,237,0.55);
    border-radius: 10px;
    padding: 8px 14px;
    margin: 4px 0 6px 0;
    transition: background 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stToggle"]:hover {
    background: rgba(124,58,237,0.20);
    border-color: #a78bfa;
}
div[data-testid="stToggle"] label p {
    font-weight: 700 !important;
    font-size: 15px !important;
    color: #c4b5fd !important;
}
/* כפתור "פתח" קטן ואפור בטבלת התחומים — דיסקרטי, לא מושך תשומת לב */
div[data-testid="stButton"] button[kind="tertiary"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    color: #9ca3af;
    font-weight: 500;
    padding: 4px 10px;
    min-height: 0;
    transition: background 0.12s ease, color 0.12s ease;
}
div[data-testid="stButton"] button[kind="tertiary"]:hover {
    background: rgba(255,255,255,0.10);
    border-color: rgba(255,255,255,0.30);
    color: #e5e7eb;
}
div[data-testid="stButton"] button[kind="tertiary"] p {
    font-size: 13px !important;
}
/* לשוניות (tabs) — בולטות עם רקע, גבול וצבע פעיל ברור */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: rgba(15,17,26,0.85);
    border-radius: 10px 10px 0 0;
    padding: 6px 8px 0;
    border-bottom: 2px solid rgba(255,255,255,0.10);
}
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.04);
    border-radius: 8px 8px 0 0;
    padding: 10px 22px;
    font-size: 15px;
    font-weight: 600;
    color: rgba(255,255,255,0.45);
    border: 1px solid rgba(255,255,255,0.08);
    border-bottom: none;
    margin-bottom: -2px;
    transition: background 0.15s, color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.09);
    color: rgba(255,255,255,0.80);
}
.stTabs [aria-selected="true"] {
    background: rgba(96,165,250,0.13) !important;
    color: #93c5fd !important;
    border-color: rgba(96,165,250,0.35) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #60a5fa !important;
    height: 3px;
    border-radius: 2px 2px 0 0;
}
.stTabs [data-baseweb="tab-panel"] {
    background: rgba(15,17,26,0.50);
    border: 1px solid rgba(255,255,255,0.08);
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 16px 12px 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------- שרשרת הערך ----------
value_chain = {
    "0. Raw Materials & Wafers (חומרי גלם ופרוסות סיליקון)": ["SHECY", "SUOPY"],
    "1. EDA & IP (תוכנות תכנון וקניין רוחני)": ["SNPS", "CDNS", "ARM"],
    "2. Fabless - Compute & AI (מעבדים ומאיצי בינה מלאכותית)": ["NVDA", "AMD", "AAPL", "QCOM", "MRVL"],
    "3. Fabless - Networking (תקשורת, סיבים וקישוריות)": ["AVGO", "ANET", "COHR", "LITE"],
    "4. IDM - Logic, Analog & Power (יצרנים משולבים)": ["INTC", "TXN", "ADI", "NXPI", "STM", "ON", "IFNNY", "RNECY", "MCHP"],
    "5. Memory & Storage (זיכרון ואחסון)": ["MU", "WDC", "STX", "005930.KS", "000660.KS"],
    "6. WFE - Front-End Equipment (ציוד ייצור מרכזי)": ["ASML", "AMAT", "LRCX", "TOELY", "ASMIY"],
    "7. Process Control & Metrology (בקרת תהליכים ומדידות)": ["KLAC", "ONTO", "NVMI", "CAMT"],
    "8. Foundries (קבלני ייצור)": ["TSM", "GFS", "UMC", "TSEM", "005930.KS"],
    "9. Back-End - OSAT, Advanced Packaging & Testing (הרכבה, מארזים ובדיקות)": ["AMKR", "TER", "ATEYY", "BESIY", "AEIS"],
    "10. AI Physical Infra & Cooling (תשתיות AI וקירור)": ["SMCI", "DELL", "HPE", "VRT", "ETN"],
}

BENCHMARK = "SOXX"

SOXX_HOLDINGS = ["NVDA", "AVGO", "AMD", "TXN", "QCOM", "INTC", "MU", "ADI",
                 "MRVL", "NXPI", "MCHP", "ON", "TSM", "ASML", "AMAT", "LRCX", "KLAC"]

# ======================================================
# פילוח טכנולוגי — ליבה ומעטפת
# ======================================================
# כל תחום = מילון עם שני חלקים:
#   "core" (ליבה)   — חברות שהתחום הוא עיקר העסק שלהן. מכפיל שכבה 1.0.
#   "env"  (מעטפת)  — מעגל שני שנהנה עקיפות מהמגמה. מכפיל שכבה 0.4.
# הערך ליד כל מניה = ציון חשיפה 0.0–1.0: אומדן לחלק מהעסק שקשור לתחום,
# על בסיס דוחות הסגמנטים (למשל NVDA ב-GPU/AI: דאטה סנטר ~90% מההכנסות).
# משקל אפקטיבי = חשיפה × מכפיל שכבה, מנורמל בתוך התחום.
# בהתאם להחלטה המתודולוגית: שווי שוק לא נכנס לחישוב.
# התחומים מחולקים לשני צירים חופפים בכוונה (חברה יכולה להופיע בשניהם):
# ציר טכנולוגיה (מה מוכרים) וציר שוקי קצה (למי מוכרים). אין לסכום בין צירים.

TIER_CORE = 1.0
TIER_ENV = 0.4

TECH_GROUPS = {
    "ציר טכנולוגיה": {
        "GPU / מאיצי AI": {
            "core": {"NVDA": 0.95, "AMD": 0.30, "AVGO": 0.20},
            "env": {"TSM": 0.40, "000660.KS": 0.50, "MU": 0.40, "MRVL": 0.30,
                    "MPWR": 0.30, "IFNNY": 0.20, "BESIY": 0.30, "CAMT": 0.30,
                    "ALAB": 0.40, "CRDO": 0.40, "COHR": 0.30, "LITE": 0.30, "FN": 0.25},
        },
        "CPU / מחשוב": {
            "core": {"INTC": 0.75, "AMD": 0.60},
            "env": {"QCOM": 0.40, "ARM": 0.50, "2454.TW": 0.20},
        },
        "DRAM": {
            "core": {"MU": 0.55, "000660.KS": 0.45, "005930.KS": 0.13},
            "env": {"RMBS": 0.10},
        },
        "HBM": {
            "core": {"000660.KS": 0.40, "MU": 0.25, "005930.KS": 0.04},
            "env": {"BESIY": 0.30, "CAMT": 0.30, "RMBS": 0.20},
        },
        "NAND": {
            "core": {"SNDK": 0.90, "285A.T": 0.90, "MU": 0.15, "000660.KS": 0.15, "005930.KS": 0.08},
            "env": {},
        },
        "ייצור (Foundry)": {
            "core": {"TSM": 0.95, "GFS": 0.90, "UMC": 0.90, "TSEM": 0.90},
            "env": {"INTC": 0.15, "005930.KS": 0.05},
        },
        "ציוד ייצור (Semicap)": {
            "core": {"ASML": 0.95, "AMAT": 0.90, "LRCX": 0.90, "KLAC": 0.90,
                     "TOELY": 0.90, "TER": 0.70, "BESIY": 0.80, "NVMI": 0.85,
                     "CAMT": 0.85, "ONTO": 0.70},
            "env": {},
        },
        "אריזה מתקדמת": {
            "core": {"BESIY": 0.90, "AMKR": 0.85, "ASX": 0.80, "CAMT": 0.50,
                     "ONTO": 0.40, "TSM": 0.15},
            "env": {"AMAT": 0.15, "KLAC": 0.10, "NVMI": 0.20},
        },
        "פוטוניקה ואופטיקה": {
            "core": {"FN": 0.80, "LITE": 0.70, "COHR": 0.60, "MRVL": 0.25, "TSEM": 0.20},
            "env": {"AVGO": 0.10},
        },
        "אנלוגי וכוח": {
            "core": {"TXN": 0.90, "ADI": 0.90, "NXPI": 0.85, "IFNNY": 0.85,
                     "STM": 0.85, "ON": 0.85, "MCHP": 0.85, "MPWR": 0.70, "RNECY": 0.70},
            "env": {"SWKS": 0.20, "QRVO": 0.20},
        },
        "תקשורת ורשתות": {
            "core": {"ALAB": 0.80, "CRDO": 0.80, "MRVL": 0.60, "QCOM": 0.40, "AVGO": 0.35},
            "env": {},
        },
        "EDA ו-IP": {
            "core": {"SNPS": 0.85, "CDNS": 0.85, "RMBS": 0.60, "ARM": 0.50},
            "env": {},
        },
    },
    "ציר שוקי קצה": {
        "Data Center (דאטה סנטר)": {
            # ליבה: מוכרות רכיבים שהדאטה סנטר הוא שוק הקצה העיקרי שלהן
            "core": {"NVDA": 0.90, "MRVL": 0.70, "000660.KS": 0.55, "MU": 0.50,
                     "AMD": 0.45, "AVGO": 0.40, "ALAB": 0.80, "CRDO": 0.80, "INTC": 0.25},
            # מעטפת: ייצור, כוח, אופטיקה ואחסון שנהנים מביקושי הדאטה סנטר
            "env": {"TSM": 0.45, "COHR": 0.40, "LITE": 0.40, "FN": 0.35,
                    "MPWR": 0.30, "SNDK": 0.25, "285A.T": 0.30, "005930.KS": 0.15},
        },
        "Edge AI (בינה מלאכותית בקצה)": {
            # ליבה: מריצות AI על המכשיר עצמו — טלפון, רכב, מכשור קצה
            "core": {"QCOM": 0.50, "2454.TW": 0.40, "ARM": 0.40, "MBLY": 0.40,
                     "NXPI": 0.25, "STM": 0.20},
            # מעטפת: AI PC ובקרי קצה — חשיפה חלקית ועקיפה למגמה
            "env": {"AMD": 0.15, "INTC": 0.15, "RNECY": 0.15, "MCHP": 0.15},
        },
        "צרכני מסורתי (PC ומובייל)": {
            # איחוד PC + מובייל: החברות המסורתיות של מחשוב וסלולר צרכני
            "core": {"2454.TW": 0.75, "SWKS": 0.70, "QRVO": 0.70, "QCOM": 0.55,
                     "INTC": 0.50, "005930.KS": 0.35, "AMD": 0.30, "NVDA": 0.07},
            "env": {"ARM": 0.50, "TSM": 0.30, "MU": 0.30, "SNDK": 0.30, "285A.T": 0.30},
        },
        "רכב": {
            "core": {"MBLY": 0.90, "NXPI": 0.55, "ON": 0.50, "RNECY": 0.50,
                     "IFNNY": 0.45, "STM": 0.40, "TXN": 0.35, "ADI": 0.30, "MCHP": 0.20},
            "env": {"QCOM": 0.10},
        },
        "תעשייה": {
            "core": {"ADI": 0.50, "TXN": 0.40, "MCHP": 0.40, "RNECY": 0.35,
                     "IFNNY": 0.25, "STM": 0.25, "ON": 0.25, "TER": 0.25, "NXPI": 0.20},
            "env": {"AMD": 0.10},
        },
    },
}

# ======================================================
# CapEx — ענקיות הענן
# ======================================================
# ההשקעות ההוניות של ענקיות הענן הן מנוע הביקוש של סקטור השבבים.
CAPEX_COMPANIES = {
    "MSFT": "מיקרוסופט",
    "GOOGL": "אלפאבית (גוגל)",
    "AMZN": "אמזון",
    "META": "מטא",
}

CAPEX_COLORS = {
    "MSFT": "#60a5fa",
    "GOOGL": "#34d399",
    "AMZN": "#fbbf24",
    "META": "#a78bfa",
}

# תחזית CapEx שנתית לשנה הפיסקלית הנוכחית — מוזן ידנית!
# אין מקור API לתחזיות; הן נאמרות בשיחות הוועידה. מעדכנים פעם ברבעון.
# כל עדכון = (תווית: מתי ניתנה התחזית, ערך במיליארדי דולרים).
# ערך None = טרם הוזן, ולא יוצג. השתמש בכפתור "חפש תחזיות עדכניות"
# בתחתית האזור כדי ש-Gemini ימצא לך את המספרים העדכניים.
# שים לב: מיקרוסופט = שנה פיסקלית עד סוף יוני,
# גוגל/אמזון/מטא = שנה קלנדרית רגילה.
CAPEX_GUIDANCE = {
    "MSFT": {
        "year_label": "FY2026 (יולי 2025 – יוני 2026)",
        "updates": [
            ("תחזית אחרי Q1 FY26", None),
            ("תחזית אחרי Q2 FY26", 154),
            ("תחזית אחרי Q3 FY26", 190),
        ],
    },
    "GOOGL": {
        "year_label": "2026",
        "updates": [
            ("תחזית אחרי Q4 2025", 180),
            ("תחזית אחרי Q1 2026", 185),
        ],
    },
    "AMZN": {
        "year_label": "2026",
        "updates": [
            ("תחזית אחרי Q4 2025", 200),
            ("תחזית אחרי Q1 2026", 200),
        ],
    },
    "META": {
        "year_label": "2026",
        "updates": [
            ("תחזית אחרי Q4 2025", 125),
            ("תחזית אחרי Q1 2026", 135),
        ],
    },
}

HOT_THRESHOLD = 10
BROAD_THRESHOLD = 0.6
GAP_THRESHOLD = 15
MOVE_ALERT = 2.0
STOCK_VS_SOXX_ALERT = 3.0  # סף מרחק של מניה בודדת מ-SOXX (נקודות %) לחריגה

# סף מרחק מהמדד לכל תקופה — כמה החציון צריך להכות/לפגר אחרי SOXX
# כדי שהתחום ייחשב "חם" או "חלש". מטפס עם אורך התקופה.
RELATIVE_THRESHOLD = {
    "online": 2.0,
    "lastclose": 2.0,
    "5d": 5.0,
    "1mo": 10.0,
    "3mo": 13.0,
    "6mo": 15.0,
    "ytd": 15.0,
    "1y": 20.0,
    "5y": 50.0,
}

AI_CACHE_TTL = {
    "online": 3600,
    "lastclose": 43200,
    "5d": 86400,
    "1mo": 259200,
    "3mo": 432000,
    "6mo": 604800,
    "ytd": 604800,
    "1y": 1209600,
    "5y": 1209600,
}

PERIOD_OPTIONS = {
    "Online": "online",
    "Last close": "lastclose",
    "5D": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "YTD": "ytd",
    "1Y": "1y",
    "5Y": "5y",
}
DAILY_PERIODS = ["online", "lastclose"]

# ---------- מצב מפתח ----------
# DEV_MODE=True: כלי הזנה ידנית גלויים (ניתוח Gemini, שמירה לקובץ, חיפוש CapEx).
# DEV_MODE=False (ברירת מחדל): מוצג רק תוכן שכבר הוזן — מצב צפייה.
# ניתן להפעיל דרך st.secrets["DEV_MODE"]=true או URL ?dev=1.
def _resolve_dev_mode():
    flag = False
    try:
        flag = bool(st.secrets.get("DEV_MODE", False))
    except Exception:
        pass
    if st.query_params.get("dev") == "1":
        flag = True
    return flag

DEV_MODE = _resolve_dev_mode()


# ---------- מפתח Gemini ----------
def get_gemini_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")


def period_stamp(period_code):
    now = datetime.now(timezone.utc)
    if period_code in ("online",):
        return now.strftime("%Y-%m-%d-%H")
    if period_code in ("lastclose", "5d"):
        return now.strftime("%Y-%m-%d")
    if period_code in ("1mo",):
        return now.strftime("%Y-%W")
    return now.strftime("%Y-%m")


# ---------- פונקציות נתונים ----------
@st.cache_data(ttl=300)
def get_history(symbol, period):
    try:
        if period == "online":
            data = yf.Ticker(symbol).history(period="2d", interval="5m")
        elif period == "lastclose":
            data = yf.Ticker(symbol).history(period="7d")
        else:
            data = yf.Ticker(symbol).history(period=period)
        close = data["Close"].dropna()
        if len(close) < 2:
            return None
        return close
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_prev_close(symbol):
    try:
        data = yf.Ticker(symbol).history(period="5d")
        close = data["Close"].dropna()
        today = datetime.now(timezone.utc).date()
        full = close[[d.date() != today for d in close.index]]
        if len(full) >= 1:
            return float(full.iloc[-1])
        return None
    except Exception:
        return None


@st.cache_data(ttl=300)
def _get_intraday_session(symbol, skip_current_day=True):
    """סדרה תוך-יומית נקייה (5 דק') של יום המסחר הנבחר, ללא נקודת עוגן.
    מחזיר (session_series, prev_close) או (None, None).
    משמש גם את get_last_session_intraday (שמוסיפה עוגן) וגם את build_chart."""
    try:
        data = yf.Ticker(symbol).history(period="7d", interval="5m")
        close = data["Close"].dropna()
        if len(close) < 2:
            return None, None
        idx = close.index
        dates = sorted({ts.date() for ts in idx})
        if not dates:
            return None, None
        tz = idx.tz
        now_exch = datetime.now(tz) if tz is not None else datetime.now(timezone.utc)
        last_date = dates[-1]
        if skip_current_day and last_date == now_exch.date() and now_exch.hour < 16 and len(dates) >= 2:
            last_date = dates[-2]
        session = close[[ts.date() == last_date for ts in idx]]
        if len(session) < 2:
            return None, None
        before = close[[ts.date() < last_date for ts in idx]]
        prev_close = float(before.iloc[-1]) if len(before) >= 1 else None
        return session, prev_close
    except Exception:
        return None, None


@st.cache_data(ttl=300)
def get_last_session_intraday(symbol, skip_current_day=True):
    """יום המסחר תוך-יומי (5 דק'), עם נקודת עוגן אלכסונית לפני הפתיחה.
    מחזיר (session_series, prev_close) או (None, None).

    skip_current_day=True  (ברירת מחדל / lastclose):
        אם היום האחרון הוא היום הנוכחי והשוק פתוח (לפני 16:00 NY) — מדלג עליו.
    skip_current_day=False (online):
        תמיד לוקח את היום האחרון הזמין, גם אם חלקי."""
    from datetime import timedelta
    session, prev_close = _get_intraday_session(symbol, skip_current_day)
    if session is None:
        return None, None
    if prev_close is not None:
        anchor_ts = session.index[0] - timedelta(minutes=15)
        anchor = pd.Series([prev_close], index=[anchor_ts])
        session = pd.concat([anchor, session])
    return session, prev_close


def get_change(symbol, period):
    close = get_history(symbol, period)
    if close is None:
        return None
    if period == "online":
        prev = get_prev_close(symbol)
        last = close.iloc[-1]
        if prev is None or prev == 0:
            return None
        change = last / prev * 100 - 100
    elif period == "lastclose":
        today = datetime.now(timezone.utc).date()
        full_closes = close[[d.date() != today for d in close.index]]
        if len(full_closes) >= 2:
            change = full_closes.iloc[-1] / full_closes.iloc[-2] * 100 - 100
        elif len(close) >= 2:
            change = close.iloc[-1] / close.iloc[-2] * 100 - 100
        else:
            return None
    else:
        change = close.iloc[-1] / close.iloc[0] * 100 - 100
    if math.isnan(change):
        return None
    return change


def get_changes(stocks, period):
    pairs = []
    for symbol in stocks:
        change = get_change(symbol, period)
        if change is not None:
            pairs.append((symbol, change))
    return pairs


def compute_tech_group_index(group_def, period):
    """מדד תחום טכנולוגי: תשואה משוקללת של ליבה (1.0) ומעטפת (0.4).

    משקל מניה = ציון חשיפה × מכפיל שכבה. מניה בלי נתונים לא נספרת.
    מחזיר גם את המשקל האפקטיבי (המנורמל) של כל מניה בתוך התחום,
    ואת תרומת כל שכבה לתשואה (שתיהן יחד = התשואה הכוללת).
    """
    weighted_sum = 0.0
    weight_total = 0.0
    core_rows = []
    env_rows = []

    for symbol, exposure in group_def.get("core", {}).items():
        change = get_change(symbol, period)
        if change is None:
            continue
        w = exposure * TIER_CORE
        weighted_sum += change * w
        weight_total += w
        core_rows.append([symbol, change, w])

    for symbol, exposure in group_def.get("env", {}).items():
        change = get_change(symbol, period)
        if change is None:
            continue
        w = exposure * TIER_ENV
        weighted_sum += change * w
        weight_total += w
        env_rows.append([symbol, change, w])

    if weight_total == 0:
        return None

    # נרמול המשקלים לתצוגה: חלקה של כל מניה מתוך 100% של התחום
    for row in core_rows:
        row[2] = row[2] / weight_total
    for row in env_rows:
        row[2] = row[2] / weight_total

    core_contrib = sum(c * w for s, c, w in core_rows)
    env_contrib = sum(c * w for s, c, w in env_rows)

    all_changes = [c for s, c, w in core_rows] + [c for s, c, w in env_rows]
    up = len([c for c in all_changes if c > 0])
    down = len([c for c in all_changes if c < 0])

    return {
        "weighted_return": weighted_sum / weight_total,
        "core": sorted(core_rows, key=lambda x: x[1], reverse=True),
        "env": sorted(env_rows, key=lambda x: x[1], reverse=True),
        "core_contrib": core_contrib,
        "env_contrib": env_contrib,
        "core_weight": sum(w for s, c, w in core_rows),
        "env_weight": sum(w for s, c, w in env_rows),
        "up": up,
        "down": down,
    }


@st.cache_data(ttl=1800)
def get_news(symbol, limit=3):
    items = []
    try:
        raw = yf.Ticker(symbol).news
        for entry in raw:
            content = entry.get("content", {})
            title = content.get("title")
            if not title:
                continue
            provider = content.get("provider", {}).get("displayName", "")
            link = ""
            canon = content.get("canonicalUrl")
            if canon:
                link = canon.get("url", "")
            date_str = ""
            pub = content.get("pubDate") or content.get("displayTime")
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    date_str = dt.strftime("%d/%m/%Y")
                except Exception:
                    date_str = ""
            items.append({"title": title, "provider": provider, "link": link, "date": date_str})
            if len(items) >= limit:
                break
    except Exception:
        pass
    return items


# ---------- פונקציות Gemini ----------
def _gemini_call(prompt):
    key = get_gemini_key()
    if not key:
        return None, []
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[tool])
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt, config=config,
        )
        sources = []
        cand = response.candidates[0]
        if cand.grounding_metadata and cand.grounding_metadata.grounding_chunks:
            for chunk in cand.grounding_metadata.grounding_chunks:
                if chunk.web:
                    sources.append((chunk.web.title, chunk.web.uri))
        return response.text, sources
    except Exception as e:
        return "שגיאה בקבלת תשובה מ-Gemini: " + str(e), []


@st.cache_data
def _cached_gemini(cache_key, prompt, ttl):
    return _gemini_call(prompt)


def gemini_explain_move(change, period_label, period_code, movers_text):
    direction = "עלה" if change >= 0 else "ירד"
    prompt = (
        "מדד SOXX (מדד מניות השבבים) " + direction + " ב-" +
        str(round(abs(change), 2)) + " אחוז ביום המסחר האחרון. "
        "המניות שזזו הכי הרבה במדד היום: " + movers_text + ". "
        "חפש ברשת והסבר בקצרה, בעברית, מה הסיבות העיקריות לתנועה של המדד. "
        "אם מניה אחת או כמה מניות ספציפיות הניעו את התנועה (למשל דוח חזק או חלש), ציין אותן בשמן. "
        "ענה ב-3 עד 5 משפטים."
    )
    ttl = AI_CACHE_TTL.get(period_code, 3600)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "move|" + period_code + "|" + day + "|" + str(round(change, 2))
    return _cached_gemini(cache_key, prompt, ttl)


def gemini_explain_outliers(soxx_change, outliers_text, period_code, period_label):
    direction = "עלה" if soxx_change >= 0 else "ירד"
    prompt = (
        "מדד SOXX " + direction + " ב-" + str(round(abs(soxx_change), 2)) +
        " אחוז ביום המסחר האחרון. "
        "אלו המניות במדד שסטו באופן חריג מתנועת המדד (עלו או ירדו לפחות " +
        str(STOCK_VS_SOXX_ALERT) + " נקודות מעל/מתחת ל-SOXX): " + outliers_text + ". "
        "חפש ברשת והסבר בקצרה, בעברית, את הסיבות הספציפיות לתנועה החריגה של כל מניה בולטת — "
        "כגון דוח רבעוני, שדרוג או הורדת דירוג אנליסטים, חדשות מוצר, רגולציה, או רוטציה סקטוריאלית. "
        "התמקד בסיבות הייחודיות לכל מניה בנפרד, לא בתנועת המדד הכללי. ענה ב-4 עד 6 משפטים."
    )
    ttl = AI_CACHE_TTL.get(period_code, 3600)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = (
        "outliers|" + period_code + "|" + day + "|" +
        str(round(soxx_change, 2)) + "|" +
        hashlib.md5(outliers_text.encode("utf-8")).hexdigest()[:8]
    )
    return _cached_gemini(cache_key, prompt, ttl)


def gemini_trend_summary(period_label, period_code, soxx_change, sector_lines):
    prompt = (
        "מדד SOXX (מניות השבבים) השתנה ב-" + str(round(soxx_change, 1)) +
        " אחוז בתקופה של " + period_label + ". "
        "ביצועי התחומים בשרשרת הערך בתקופה זו: " + sector_lines + ". "
        "חפש ברשת וכתוב בעברית סיכום של המגמה המרכזית שתמכה בתנועה בתקופה הזו. "
        "התייחס לנושאים מובילים (כמו ביקושי AI, דאטה סנטרים, זיכרון, ציוד ייצור) "
        "ואילו תחומים הובילו ואילו פיגרו. ענה ב-4 עד 6 משפטים."
    )
    ttl = AI_CACHE_TTL.get(period_code, 604800)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "trend|" + period_code + "|" + day
    return _cached_gemini(cache_key, prompt, ttl)


@st.cache_data(ttl=43200)
def gemini_analyze_news(sector_name, titles_sig, titles_block):
    key = get_gemini_key()
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        config = types.GenerateContentConfig(response_mime_type="application/json")
        prompt = (
            "אלה כותרות חדשות אחרונות על מניות בתחום '" + sector_name + "' בסקטור השבבים:\n"
            + titles_block + "\n\n"
            "החזר JSON בלבד, בלי טקסט נוסף, במבנה הבא:\n"
            '{ "overall": "positive|negative|neutral", '
            '"overall_note": "משפט אחד בעברית שמסכם את סנטימנט החדשות בתחום", '
            '"items": [ { "title": "הכותרת המקורית", '
            '"sentiment": "positive|negative|neutral", '
            '"summary": "סיכום קצר בעברית, משפט עד שניים" } ] }\n'
            "דרג כל כותרת לפי ההשפעה הצפויה על המניה, וכתוב את הסיכומים בעברית."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt, config=config,
        )
        return json.loads(response.text)
    except Exception:
        return None


# ---------- פונקציות CapEx ----------
@st.cache_data(ttl=86400)
def get_capex_quarterly(symbol):
    """CapEx רבעוני במיליארדי דולרים, מהישן לחדש. None אם אין נתונים."""
    try:
        cf = yf.Ticker(symbol).quarterly_cashflow
        row = None
        for name in ("Capital Expenditure", "Capital Expenditures"):
            if name in cf.index:
                row = cf.loc[name]
                break
        if row is None:
            return None
        row = row.dropna().abs() / 1e9
        row = row.sort_index()
        if len(row) == 0:
            return None
        return row
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_capex_annual(symbol):
    """CapEx שנתי (לפי השנה הפיסקלית של החברה) במיליארדי דולרים, מהישן לחדש."""
    try:
        cf = yf.Ticker(symbol).cashflow
        row = None
        for name in ("Capital Expenditure", "Capital Expenditures"):
            if name in cf.index:
                row = cf.loc[name]
                break
        if row is None:
            return None
        row = row.dropna().abs() / 1e9
        row = row.sort_index()
        if len(row) == 0:
            return None
        return row
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_earnings_history(symbol):
    """היסטוריית EPS מ-earnings_dates: רק רבעונים שדווחו (Reported EPS לא ריק), עד 8 אחורה."""
    try:
        df = yf.Ticker(symbol).earnings_dates
        if df is None or df.empty:
            return None
        reported = df[df["Reported EPS"].notna()].copy()
        if reported.empty:
            return None
        return reported.sort_index(ascending=False).head(8)
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_quarterly_revenue(symbol):
    """הכנסות רבעוניות מ-quarterly_financials. מחזיר (Series ב-1e9, שם_שורה) או (None, None)."""
    try:
        qf = yf.Ticker(symbol).quarterly_financials
        if qf is None or qf.empty:
            return None, None
        for name in ("Total Revenue", "TotalRevenue", "Revenue"):
            if name in qf.index:
                row = qf.loc[name].dropna() / 1e9
                return row.sort_index(), name
        return None, None
    except Exception:
        return None, None


@st.cache_data(ttl=86400)
def get_financial_currency(symbol):
    """קוד המטבע הפיננסי (financialCurrency) מ-ticker.info."""
    try:
        return yf.Ticker(symbol).info.get("financialCurrency", "USD") or "USD"
    except Exception:
        return "USD"


@st.cache_data(ttl=86400)
def get_forward_estimates(symbol):
    """תחזיות אנליסטים לרבעון הקרוב: eps_est, revenue_est_b, revenue_growth_pct."""
    try:
        t = yf.Ticker(symbol)
        result = {}
        ee = t.earnings_estimate
        if ee is not None and not ee.empty and "0q" in ee.index:
            avg = ee.loc["0q"].get("avg")
            if avg is not None and not (isinstance(avg, float) and math.isnan(avg)):
                result["eps_est"] = float(avg)
        re_ = t.revenue_estimate
        if re_ is not None and not re_.empty and "0q" in re_.index:
            row = re_.loc["0q"]
            avg = row.get("avg")
            growth = row.get("growth")
            if avg is not None and not (isinstance(avg, float) and math.isnan(avg)):
                result["revenue_est_b"] = float(avg) / 1e9
            if growth is not None and not (isinstance(growth, float) and math.isnan(growth)):
                result["revenue_growth_pct"] = float(growth) * 100
        return result if result else None
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_stock_reaction(symbol, report_date_str):
    """% שינוי של המניה מסגירת יום הדוח לסגירת יום המסחר הבא.
    מחזיר (reaction_pct, next_date) או (None, None) בשגיאה."""
    from datetime import timedelta
    try:
        report_date = datetime.fromisoformat(report_date_str[:10]).date()
        start = report_date - timedelta(days=2)
        end = report_date + timedelta(days=6)
        df = yf.Ticker(symbol).history(start=str(start), end=str(end))["Close"].dropna()
        if len(df) < 2:
            return None, None
        date_prices = [(dt.date(), float(p)) for dt, p in zip(df.index, df.values)]
        after = [(d, p) for d, p in date_prices if d >= report_date]
        if len(after) < 2:
            return None, None
        _, p0 = after[0]
        d1, p1 = after[1]
        if p0 == 0:
            return None, None
        return p1 / p0 * 100 - 100, d1
    except Exception:
        return None, None


def get_symbol_cal_status(sym, d, has_report, sentiment_data):
    """מחזיר 'future' / 'analyzed' / 'unanalyzed' לצביעת לוח השנה.
    has_report=True אם yfinance מדווח EPS בפועל (הדוח יצא)."""
    today = datetime.now(timezone.utc).date()
    if not has_report or d > today:
        return "future"
    rec = get_record(sentiment_data, sym, season_from_date(d))
    if rec and rec.get("sentiment_score") is not None:
        return "analyzed"
    return "unanalyzed"


@st.cache_data(ttl=3600)
def get_earnings_calendar(symbols, days_back=120, days_fwd=120):
    """לכל חברה: כל הדוחות בחלון [היום - days_back, היום + days_fwd].
    מחזיר רשימת dicts: date, symbol, eps_est, eps_actual, surprise, is_future.
    משתמש ב-.get() על ה-Series (עמיד לשינויי שמות עמודות ב-yfinance)."""
    from datetime import timedelta
    import math
    today = datetime.now(timezone.utc).date()
    lo = today - timedelta(days=days_back)
    hi = today + timedelta(days=days_fwd)

    def _clean(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    out = []
    for sym in symbols:
        try:
            df = yf.Ticker(sym).earnings_dates
            if df is None or df.empty:
                continue
            for dt in df.index:
                d = dt.date() if hasattr(dt, "date") else dt
                if not (lo <= d <= hi):
                    continue
                row = df.loc[dt]
                eps_act = _clean(row.get("Reported EPS"))
                eps_est = _clean(row.get("EPS Estimate"))
                surp = _clean(row.get("Surprise(%)"))
                # עתידי = אין EPS בפועל
                is_future = eps_act is None
                out.append({
                    "date": d, "symbol": sym,
                    "eps_est": eps_est, "eps_actual": eps_act,
                    "surprise": surp, "is_future": is_future,
                })
        except Exception:
            continue
    out.sort(key=lambda x: x["date"])
    return out


def gemini_capex_trend(capex_lines):
    """סיכום מגמת ה-CapEx הרבעוני עם חיפוש ברשת."""
    prompt = (
        "אלה נתוני ה-CapEx הרבעוניים האחרונים של ענקיות הענן, במיליארדי דולרים: "
        + capex_lines + ". "
        "חפש ברשת וכתוב בעברית סיכום קצר: האם הכיוון הוא האצה או האטה בהשקעות, "
        "מה החברות אמרו בשיחות הוועידה האחרונות, "
        "ומה המשמעות לספקיות השבבים והציוד (NVDA, AVGO, TSM, ציוד ייצור). "
        "ענה ב-4 עד 6 משפטים."
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "capex_trend|" + day
    return _cached_gemini(cache_key, prompt, 604800)


def gemini_capex_guidance():
    """חיפוש התחזיות השנתיות העדכניות — עוזר למלא את CAPEX_GUIDANCE ידנית."""
    prompt = (
        "חפש ברשת את תחזית ה-CapEx השנתית (Capital Expenditure Guidance) "
        "העדכנית ביותר שכל אחת מהחברות הבאות נתנה בשיחת הוועידה האחרונה שלה: "
        "Microsoft (שנה פיסקלית עד יוני), Alphabet/Google, Amazon, Meta, "
        "Oracle (שנה פיסקלית עד מאי). "
        "כתוב בעברית, לכל חברה שורה אחת: שם החברה, לאיזו שנה פיסקלית התחזית, "
        "מה הסכום במיליארדי דולרים, ומתי התחזית ניתנה (איזה דוח רבעוני). "
        "אם חברה עדכנה את התחזית במהלך השנה, ציין גם את המספר הקודם."
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "capex_guidance|" + day
    return _cached_gemini(cache_key, prompt, 259200)

def gemini_summarize_capex_guidance(guidance_lines):
    """מסכם את עדכוני תחזית ה-CapEx השנתיות והמשמעות לסקטור השבבים — גלוי ליוזר."""
    prompt = (
        "אלה תחזיות ה-CapEx השנתיות של ענקיות הענן, כפי שדווחו בשיחות הוועידה:\n"
        + guidance_lines + "\n\n"
        "חפש ברשת הקשר ועדכונים נוספים, ולאחר מכן כתוב בעברית סיכום של 4-5 משפטים:\n"
        "1. מה כיוון עדכוני התחזית (עולות, יורדות, יציבות)?\n"
        "2. מה אמרו המנכ\"לים בנוגע להצדקת ההשקעות (AI, תשתיות, תחרות)?\n"
        "3. מה המשמעות לספקיות השבבים והציוד (NVDA, ASML, AMAT, TSM)?"
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "capex_guid_summary|" + day
    return _cached_gemini(cache_key, prompt, 86400)


def gemini_analyze_earnings(symbol, season):
    """מנתח דוח ושיחת ועידה של חברה לפי עונה, עם חיפוש רשת.
    season = מחרוזת כמו '2026Q2'. מחזיר dict מובנה, או None בשגיאה.
    לא ממוטמן — נקרא רק על ידי לחיצת משתמש."""
    # בניית רשימת התחומים הסגורה מ-TECH_GROUPS
    valid_domains = set()
    for axis in TECH_GROUPS.values():
        for gname in axis.keys():
            valid_domains.add(gname)
    domains_list = "\n".join("- " + d for d in sorted(valid_domains))

    # המרת עונה לטקסט קריא
    year, q = season[:4], season[5]
    q_months = {"1": "ינואר–מרץ", "2": "אפריל–יוני", "3": "יולי–ספטמבר", "4": "אוקטובר–דצמבר"}
    season_label = "Q" + q + " " + year + " (" + q_months.get(q, "") + ")"

    prompt = (
        "חפש ברשת שני מקורות לגבי " + symbol + " לתקופת " + season_label + ":\n"
        "1. הדוח הרבעוני (10-Q / press release) — תוצאות EPS, הכנסות, מול ציפיות האנליסטים.\n"
        "2. תמליל או סיכום שיחת הוועידה (earnings call transcript) — הערות ההנהלה, "
        "תחזיות, ושוקי הקצה שהוזכרו (data center, auto, industrial, mobile, PC וכד').\n"
        "שלב את שני המקורות לניתוח אחד מקיף.\n\n"
        "לאחר מכן, החזר JSON בלבד (ללא טקסט נוסף לפניו או אחריו) במבנה הבא:\n"
        "{\n"
        '  "report_date": "YYYY-MM-DD",\n'
        '  "sentiment_score": <מספר בין -1.0 לבין 1.0: שלילי=ציפיות מאכזבות/הנחיה יורדת, '
        'חיובי=תוצאות טובות/הנחיה עולה, 0=ניטרלי>,\n'
        '  "results_vs_expectations": "beat|meet|miss",\n'
        '  "guidance_direction": "raised|maintained|lowered|none",\n'
        '  "summary": "<סיכום קצר בעברית, 2-3 משפטים: תוצאות, מה הפתיע, לאן כיוון ההנחיה>",\n'
        '  "domain_signals": [\n'
        '    {"domain": "<שם מהרשימה הסגורה בלבד>", "direction": "improving|stable|deteriorating", '
        '"note": "<משפט קצר בעברית מה אמרה ההנהלה על שוק הקצה הזה>"}\n'
        "  ],\n"
        '  "revenue_actual_b": <הכנסות בפועל במיליארדי דולרים, מספר עשרוני, או null>,\n'
        '  "revenue_estimate_b": <קונצנזוס האנליסטים להכנסות לפני הדוח, במיליארדי דולרים, או null>,\n'
        '  "eps_actual": <EPS בפועל, מספר עשרוני, או null>,\n'
        '  "eps_estimate": <קונצנזוס האנליסטים ל-EPS לפני הדוח, מספר עשרוני, או null>,\n'
        '  "next_q_guidance": {\n'
        '    "revenue_b": <אמצע טווח תחזית ההכנסות שהחברה נתנה לרבעון הבא, או null>,\n'
        '    "eps": <אמצע טווח תחזית ה-EPS של החברה לרבעון הבא, או null>,\n'
        '    "analyst_revenue_b": <קונצנזוס האנליסטים להכנסות הרבעון הבא, או null>,\n'
        '    "vs_consensus": "above|inline|below|none"\n'
        "  }\n"
        "}\n\n"
        "חוקי חובה:\n"
        "1. sentiment_score: הציון משקף אך ורק את התוצאות מול הציפיות ואת כיוון ההנחיה — "
        "לא את תגובת המניה בשוק ולא את סנטימנט המשקיעים. "
        "גם אם המניה ירדה אחרי דוח חזק (או עלתה אחרי דוח חלש), התעלם מכך בציון. "
        "השתמש בסולם רציף: beat+raised = \u200F0.8 עד \u200F1.0, "
        "beat+maintained = \u200F0.5 עד \u200F0.7, "
        "meet+maintained = \u200F-0.1 עד \u200F0.2, "
        "miss+lowered = \u200F-0.8 עד \u200F-1.0. "
        "חששות או סיכונים שההנהלה עצמה ציינה (למשל אילוצי אספקה, הגבלות יצוא) "
        "יכולים להוריד את הציון במעט בתוך הטווח, אך לא לשנות את המדרגה.\n"
        "2. domain: חובה לבחור אך ורק מהרשימה הסגורה הבאה. אין להמציא שמות:\n"
        + domains_list + "\n"
        "3. כלול ב-domain_signals רק תחומים שהוזכרו בצורה מפורשת בשיחה. אם אין — השאר רשימה ריקה.\n"
        "4. אם לא מצאת דוח לתקופה זו, החזר: {\"error\": \"לא נמצא דוח לתקופה זו\"}\n"
        "5. כל שדה מספרי שלא נמצא במקורות — החזר null, אל תנחש. "
        "vs_consensus = השוואת תחזית ההכנסות של החברה מול קונצנזוס האנליסטים לרבעון הבא."
    )

    text, _ = _gemini_call(prompt)
    if not text:
        return None
    # מחלץ JSON מהתשובה (Gemini עלול להוסיף טקסט לפני/אחרי)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def gemini_israeli_impact(il_symbol, season, context_text):
    """ניתוח השפעת דוחות שפורסמו בעונה על חברה ישראלית ספציפית."""
    _desc = {
        "TSEM": "Tower Semiconductor — foundry ישראלי לשבבים אנלוגיים, RF ומיוחדים",
        "NVMI": "Nova — ציוד מדידה ובקרת תהליכים (process control & metrology)",
        "CAMT": "Camtek — ציוד בדיקה ומדידה לאריזה מתקדמת",
        "MBLY": "Mobileye — מערכות ראייה ממוחשבת לרכב אוטונומי",
        "MSFT": "Microsoft — ענקית תוכנה וענן (Azure), לקוחה מרכזית של NVDA ו-AMD לתשתיות AI",
        "META": "Meta Platforms — רשתות חברתיות, משקיעה עצומה בתשתיות AI ומרכזי נתונים",
        "GOOGL": "Alphabet/Google — מנוע חיפוש, ענן (GCP) ו-AI; מפתחת שבבי TPU מקוריים",
        "AMZN": "Amazon — ענן AWS ומסחר אלקטרוני; הלקוחה הגדולה ביותר של תשתיות GPU",
        "ORCL": "Oracle — תוכנה ארגונית ותשתיות ענן (OCI); צומחת מהר בהשכרת תשתיות AI",
        "005930.KS": "Samsung Electronics — יצרן זיכרון DRAM/NAND/HBM וגם מפעילה foundry לייצור לוגיקה",
        "000660.KS": "SK Hynix — יצרן זיכרון DRAM/NAND/HBM; ספק HBM מרכזי ל-NVDA",
    }
    desc = _desc.get(il_symbol, il_symbol)
    prompt = (
        "עונת הדוחות " + season + ".\n"
        "הדוחות הבאים פורסמו עד כה בסקטור השבבים:\n"
        + context_text + "\n\n"
        "בהתבסס על הסיגנלים שעלו מהדוחות לעיל, וחיפוש ברשת למידע עדכני נוסף, "
        "נתח את ההשפעה הצפויה על " + il_symbol + " (" + desc + ").\n"
        "ענה בעברית, 4-5 משפטים: אילו סיגנלים מהדוחות רלוונטיים ל-" + il_symbol + ", "
        "מה חיובי ומה שלילי, ומה הציפיות לדוח של " + il_symbol + " בעונה זו."
    )
    return _gemini_call(prompt)


# ======================================================
# סנטימנט דוחות ושיחות ועידה — שכבת נתונים
# ======================================================
SENTIMENT_FILE = "earnings_sentiment.json"


def season_from_date(d):
    """ממפה תאריך דיווח לעונת דוחות = הרבעון הקלנדרי שבו פורסם הדוח."""
    if isinstance(d, str):
        d = datetime.fromisoformat(d[:10])
    q = (d.month - 1) // 3 + 1
    return str(d.year) + "Q" + str(q)


def current_season():
    return season_from_date(datetime.now(timezone.utc))


def latest_season_with_data(sentiment):
    """העונה האחרונה שיש בה לפחות רשומה אחת. אם הקובץ ריק — current_season().
    מיון לקסיקוגרפי עובד כי הפורמט YYYYQN שומר על סדר כרונולוגי."""
    all_seasons = set()
    for sym_data in sentiment.values():
        all_seasons.update(sym_data.keys())
    if not all_seasons:
        return current_season()
    return sorted(all_seasons)[-1]


def load_sentiment():
    """טוען את קובץ הסנטימנט. מבנה: {symbol: {season: record}}. אין קובץ -> {}.
    לא ממוטמן בכוונה, כדי שכתיבה חדשה תשתקף מיד."""
    try:
        with open(SENTIMENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_sentiment_record(sym, season, record):
    """כותב/מעדכן רשומה אחת. עובד מקומית; ב-Streamlit Cloud לא ישרוד restart,
    ואז מעתיקים ידנית ודוחפים ל-git (בדיוק כמו CAPEX_GUIDANCE)."""
    data = load_sentiment()
    data.setdefault(sym, {})[season] = record
    with open(SENTIMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_record(sentiment, sym, season):
    return sentiment.get(sym, {}).get(season)


def aggregate_sentiment(weighted_symbols, season, sentiment=None):
    """סנטימנט משוקלל של תחום בעונה נתונה.
    weighted_symbols = {symbol: weight}. מחזיר ציון משוקלל, כיסוי ופירוט,
    או None אם אף חברה בתחום לא דיווחה בעונה הזו.
    כיסוי = כמה מתוך חברות התחום כבר יש להן רשומה בעונה."""
    if sentiment is None:
        sentiment = load_sentiment()
    rows = []
    wsum = 0.0
    wtot = 0.0
    for sym, w in weighted_symbols.items():
        rec = get_record(sentiment, sym, season)
        if rec is None or rec.get("sentiment_score") is None:
            continue
        score = float(rec["sentiment_score"])
        wsum += score * w
        wtot += w
        rows.append((sym, score, rec.get("guidance_direction"),
                     rec.get("results_vs_expectations")))
    if wtot == 0:
        return None
    return {
        "score": wsum / wtot,
        "reported": len(rows),
        "total": len(weighted_symbols),
        "rows": sorted(rows, key=lambda x: x[1], reverse=True),
    }


def value_chain_sentiment(sector, season, sentiment=None):
    # שרשרת הערך: ממוצע פשוט, כל מניה במשקל שווה
    symbols = {s: 1.0 for s in value_chain[sector]}
    return aggregate_sentiment(symbols, season, sentiment)


def tech_group_sentiment(group_def, season, sentiment=None):
    # פילוח טכנולוגי: אותו משקל כמו התשואה — חשיפה × מכפיל שכבה
    symbols = {}
    for s, exp in group_def.get("core", {}).items():
        symbols[s] = exp * TIER_CORE
    for s, exp in group_def.get("env", {}).items():
        symbols[s] = symbols.get(s, 0.0) + exp * TIER_ENV
    return aggregate_sentiment(symbols, season, sentiment)


def domain_signal_score(group_name, season, sentiment_data):
    """ציון סיגנלים תחומיים: ממוצע improving(+1)/stable(0)/deteriorating(-1)
    מכל החברות שציינו את group_name בעונה. מחזיר (score, count) או (None, 0)."""
    _dir_val = {"improving": 1.0, "stable": 0.0, "deteriorating": -1.0}
    vals = []
    for sym_data in sentiment_data.values():
        rec = sym_data.get(season)
        if not rec:
            continue
        for sig in rec.get("domain_signals", []):
            if sig.get("domain") == group_name:
                vals.append(_dir_val.get(sig.get("direction", "stable"), 0.0))
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def weighted_tech_score(group_name, group_def, season, sentiment_data):
    """ציון משוקלל סופי לתחום טכנולוגי: 70% סנטימנט חברות + 30% סיגנלים תחומיים.
    מחזיר dict עם score ורכיביו, או None אם אין נתונים כלל."""
    comp_agg = tech_group_sentiment(group_def, season, sentiment_data)
    sig_score, sig_count = domain_signal_score(group_name, season, sentiment_data)
    if comp_agg is None and sig_score is None:
        return None
    comp_score = comp_agg["score"] if comp_agg else None
    if comp_score is not None and sig_score is not None:
        final = 0.7 * comp_score + 0.3 * sig_score
    elif comp_score is not None:
        final = comp_score
    else:
        final = sig_score
    return {
        "score": final,
        "comp_score": comp_score,
        "comp_reported": comp_agg["reported"] if comp_agg else 0,
        "comp_total": comp_agg["total"] if comp_agg else 0,
        "sig_score": sig_score,
        "sig_count": sig_count,
    }


def titles_signature(titles):
    joined = "||".join(titles)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def label_info(median, breadth, soxx_change, period):
    # דירוג יחסי: כמה החציון מכה או מפגר אחרי SOXX, מול הסף לתקופה
    threshold = RELATIVE_THRESHOLD.get(period, 10.0)
    if soxx_change is None:
        rel = median  # נפילה אחורה: בלי מדד, משווים מול אפס
    else:
        rel = median - soxx_change
    if rel >= threshold and breadth >= BROAD_THRESHOLD:
        return "🔥 חם", "#22c55e", "rgba(34,197,94,0.12)"
    if rel <= -threshold:
        return "⚠️ חלש", "#ef4444", "rgba(239,68,68,0.12)"
    return "🟡 ניטרלי", "#eab308", "rgba(234,179,8,0.12)"


def zone_bg(rel, threshold, max_abs):
    # צבע רקע לפי המרחק מ-SOXX: ירוק (מכה מעל הסף), צהוב (קרוב למדד), אדום (מפגר מעבר לסף)
    # rel = חציון פחות SOXX · threshold = סף התקופה · max_abs = המרחק הקיצוני בדירוג
    if threshold <= 0:
        threshold = 1.0
    if rel >= threshold:
        # ירוק: בהיר בסף -> כהה בקיצון
        span = max(max_abs - threshold, 1.0)
        f = min((rel - threshold) / span, 1.0)
        r = int(134 + (21 - 134) * f)
        g = int(239 + (128 - 239) * f)
        b = int(134 + (61 - 134) * f)
    elif rel <= -threshold:
        # אדום: בהיר בסף -> כהה בקיצון
        span = max(max_abs - threshold, 1.0)
        f = min((-rel - threshold) / span, 1.0)
        r = int(248 + (153 - 248) * f)
        g = int(113 + (27 - 113) * f)
        b = int(113 + (27 - 113) * f)
    else:
        # צהוב: בהיר ליד המדד -> חזק ליד הסף
        f = min(abs(rel) / threshold, 1.0)
        r = int(250 + (234 - 250) * f)
        g = int(240 + (179 - 240) * f)
        b = int(150 + (8 - 150) * f)
    return "rgba(" + str(r) + "," + str(g) + "," + str(b) + ",0.22)"


def build_chart(stocks, period, intraday=False, skip_current_day=True):
    series_list = []
    for symbol in stocks:
        if intraday:
            close, _ = _get_intraday_session(symbol, skip_current_day)
        else:
            close = get_history(symbol, period)
        if close is None:
            continue
        clean = close.dropna()
        if len(clean) < 2:
            continue  # אין מספיק נתונים — לא נכניס עמודה ריקה למקרא
        # נרמול לפי הערך התקין הראשון של אותה מניה
        normalized = clean / clean.iloc[0] * 100
        normalized.name = symbol
        series_list.append(normalized)

    if len(series_list) == 0:
        return pd.DataFrame()

    # איחוד לפי תאריכים (outer join), מילוי קדימה ואחורה ליישור בורסות שונות
    chart_data = pd.concat(series_list, axis=1).sort_index()
    chart_data = chart_data.ffill().bfill()
    # השמטת עמודות שעדיין ריקות לגמרי, שלא יופיעו במקרא בלי קו
    chart_data = chart_data.dropna(axis=1, how="all")
    return chart_data


def build_spread_chart(stocks, period, intraday=False, skip_current_day=True):
    # גרף פער מצטבר: חציון התחום (מנורמל ל-100) פחות SOXX (מנורמל ל-100), לאורך התקופה
    # אזור צבוע: ירוק כשהתחום מכה את המדד, אדום כשמפגר
    chart_data = build_chart(stocks, period, intraday=intraday, skip_current_day=skip_current_day)
    if chart_data.empty:
        return None
    if intraday:
        soxx_close, _ = _get_intraday_session(BENCHMARK, skip_current_day)
    else:
        soxx_close = get_history(BENCHMARK, period)
    if soxx_close is None:
        return None

    median_series = chart_data.median(axis=1)
    soxx_norm = soxx_close / soxx_close.iloc[0] * 100
    # מיישרים את שני האינדקסים לאותם תאריכים
    df = pd.DataFrame({"median": median_series, "soxx": soxx_norm}).dropna()
    if len(df) < 2:
        return None
    df["spread"] = df["median"] - df["soxx"]
    df = df.reset_index()
    date_col = df.columns[0]
    df = df.rename(columns={date_col: "תאריך"})

    # --- החדרת נקודות חצייה של האפס ---
    # בכל מקום שבו הפער עובר מחיובי לשלילי (או להפך) בין שתי נקודות,
    # מחשבים את התאריך המדויק שבו הוא שווה 0 ומכניסים שם נקודת ביניים.
    # כך המילוי הירוק/אדום נחתך בדיוק על קו האפס, בלי משולשים בצבע הלא נכון.
    rows = []
    for i in range(len(df)):
        rows.append({"תאריך": df["תאריך"].iloc[i], "spread": df["spread"].iloc[i]})
        if i < len(df) - 1:
            y1 = df["spread"].iloc[i]
            y2 = df["spread"].iloc[i + 1]
            if (y1 > 0 and y2 < 0) or (y1 < 0 and y2 > 0):
                t1 = df["תאריך"].iloc[i]
                t2 = df["תאריך"].iloc[i + 1]
                # אינטרפולציה ליניארית של רגע החצייה
                frac = abs(y1) / (abs(y1) + abs(y2))
                t_cross = t1 + (t2 - t1) * frac
                rows.append({"תאריך": t_cross, "spread": 0.0})
    df = pd.DataFrame(rows)

    # שתי עמודות נפרדות: אחת רק לערכים החיוביים, אחת רק לשליליים.
    # מחוץ לתחום כל אחת מקבלת 0, כך שהמילוי לא "גולש" מעבר לקו האפס.
    df["pos"] = df["spread"].clip(lower=0)
    df["neg"] = df["spread"].clip(upper=0)

    _x_axis_kw = dict(labelFontSize=12, labelPadding=8, tickCount=6)
    if intraday:
        _x_axis_kw["format"] = "%H:%M"
    base = alt.Chart(df).encode(
        x=alt.X("תאריך:T", title=None, axis=alt.Axis(**_x_axis_kw))
    )
    area_pos = base.mark_area(color="rgba(34,197,94,0.35)").encode(
        y=alt.Y("pos:Q", title="פער מ-SOXX (נק')",
                axis=alt.Axis(labelFontSize=12, titleFontSize=13, titlePadding=10)))
    area_neg = base.mark_area(color="rgba(239,68,68,0.35)").encode(y="neg:Q")
    line = base.mark_line(strokeWidth=2.5, color="#e5e7eb").encode(y="spread:Q")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        strokeDash=[3, 3], color="#888", strokeWidth=1.5
    ).encode(y="y:Q")
    return (area_pos + area_neg + line + zero).properties(
        height=260, padding={"top": 10, "bottom": 10, "left": 10, "right": 20}
    )


def clean_name(sector):
    if ". " in sector:
        return sector.split(". ", 1)[1]
    return sector


def sector_key(sector_name):
    # מזהה יציב וקצר לכל תחום, לפי שמו (לא לפי מיקומו בדירוג).
    # משמש למפתחות widgets ו-session_state כדי שהמצב יישאר צמוד לתחום
    # גם כשהדירוג משתנה בעקבות החלפת תקופה.
    return hashlib.md5(sector_name.encode("utf-8")).hexdigest()[:8]


def ranking_bar_chart(items, chart_key, soxx_marker=None, debug=False):
    """גרף עמודות אופקי לחיץ לדירוג תחומים, בכיוון RTL.

    items = רשימה של (label, value) כבר ממוינת מהגבוה לנמוך.
    value = התשואה של התחום באחוזים.
    soxx_marker = ערך תשואת SOXX; אם ניתן, מצויר קו כתום בולט במיקומו.
    debug = אם True, מדפיס את מבנה אירוע הבחירה (לאבחון קליק).
    לחיצה על עמודה מחזירה את ה-label שלה (או None אם לא נלחץ כלום).

    RTL: לא הופכים את ציר ה-X (שובר on_select). העמודות יוצאות שמאלה
    מקו האפס הימני, ושמות התחומים בצד ימין. האורך = שורש הערך המוחלט.
    """
    if not items:
        return None

    def transform(v):
        # אותה טרנספורמציה כמו העמודות: שורש עם שמירת כיוון-שמאל
        return -math.sqrt(abs(v))

    labels = [lbl for lbl, val in items]
    values = [val for lbl, val in items]
    bar_widths = [transform(v) for v in values]
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in values]
    text_labels = [("+" if v >= 0 else "") + str(round(v, 1)) + "%" for v in values]

    # סדר: הגבוה למעלה. Plotly מצייר מלמטה למעלה, אז הופכים.
    labels_r = list(reversed(labels))
    widths_r = list(reversed(bar_widths))
    colors_r = list(reversed(colors))
    texts_r = list(reversed(text_labels))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=widths_r, y=labels_r, orientation="h",
        marker=dict(color=colors_r, line=dict(width=0)),
        text=texts_r, textposition="outside",
        textfont=dict(size=13, color="#e5e7eb"),
        hoverinfo="skip", hovertemplate=None,
        cliponaxis=False,
    ))
    # קו אפס בצד ימין (x=0)
    fig.add_vline(x=0, line_width=1.5, line_color="rgba(255,255,255,0.30)")

    max_w = max((abs(w) for w in widths_r), default=1.0)

    # קו SOXX בולט: כתום עבה ומקווקו במיקום תשואת המדד, עם תווית מודגשת בתיבה
    if soxx_marker is not None:
        soxx_x = transform(soxx_marker)
        max_w = max(max_w, abs(soxx_x))
        fig.add_vline(
            x=soxx_x, line_width=4, line_color="#f59e0b", line_dash="dash",
        )
        fig.add_annotation(
            x=soxx_x, y=1.0, yref="paper", yanchor="bottom",
            text="<b>SOXX " + ("+" if soxx_marker >= 0 else "") + str(round(soxx_marker, 1)) + "%</b>",
            showarrow=False, font=dict(size=15, color="#000000"),
            bgcolor="#f59e0b", bordercolor="#f59e0b", borderpad=4,
            xanchor="center", yshift=6,
        )

    pad = max_w * 0.28
    row_h = 40
    top_margin = 34 if soxx_marker is not None else 8
    chart_h = max(len(labels) * row_h + 30 + top_margin, 120)
    fig.update_layout(
        height=chart_h, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=top_margin, b=12, l=20, r=20),
        showlegend=False, bargap=0.42,
        hovermode=False,
        xaxis=dict(visible=False, showgrid=False, zeroline=False,
                   range=[-max_w - pad, pad]),
        yaxis=dict(showgrid=False, side="right", automargin=True,
                   tickfont=dict(size=13, color="#d1d5db")),
    )

    event = st.plotly_chart(
        fig, use_container_width=True, key=chart_key,
        on_select="rerun", selection_mode="points",
    )

    # בלוק דיבאג זמני: מציג את מבנה אירוע הבחירה כדי לאבחן את הקליק
    if debug:
        st.caption("🔧 דיבאג — מבנה אירוע הבחירה (זמני):")
        st.write({"type": str(type(event)), "event": event})

    # חילוץ התחום שנלחץ — חסין למספר מבנים אפשריים של האירוע
    try:
        sel = None
        if isinstance(event, dict):
            sel = event.get("selection")
        else:
            sel = getattr(event, "selection", None)
        if sel is not None:
            points = sel["points"] if isinstance(sel, dict) else getattr(sel, "points", None)
            if points:
                p0 = points[0]
                # התווית יכולה לחזור תחת 'y' (קטגוריה) או 'label'
                if isinstance(p0, dict):
                    return p0.get("y") or p0.get("label")
                return getattr(p0, "y", None)
    except (KeyError, TypeError, IndexError, AttributeError):
        pass
    return None


def section_banner(number, total, icon, title, color, subtitle="", period_dependent=None, period_label=""):
    """באנר גדול ובולט לתחילת אזור ראשי בדשבורד.
    period_dependent=True  → תגית 🕐 מגיב לתקופה
    period_dependent=False → תגית 📌 נתונים עצמאיים
    period_dependent=None  → ללא תגית (תאימות לאחור)"""
    sub_html = ""
    if subtitle:
        sub_html = ("<div style='font-size:14px; color:rgba(255,255,255,0.75); "
                    "margin-top:4px; font-weight:400;'>" + subtitle + "</div>")
    if period_dependent is True:
        period_tag = ("<span style='font-size:11px; color:#fbbf24; font-weight:600; "
                      "background:rgba(251,191,36,0.12); padding:2px 8px; border-radius:20px; "
                      "border:1px solid rgba(251,191,36,0.3);'>"
                      "🕐 מגיב לתקופה: " + period_label + "</span>")
    elif period_dependent is False:
        period_tag = ("<span style='font-size:11px; color:#6b7280; font-weight:600; "
                      "background:rgba(107,114,128,0.12); padding:2px 8px; border-radius:20px; "
                      "border:1px solid rgba(107,114,128,0.3);'>"
                      "📌 נתונים עצמאיים</span>")
    else:
        period_tag = ""
    st.markdown(
        "<div id='zone-" + str(number) + "' style='height:36px;'></div>"
        "<div dir='rtl' style='text-align:right; background:linear-gradient(90deg, " + color + "22, transparent); "
        "border-right:8px solid " + color + "; border-radius:10px; "
        "padding:16px 20px; margin-bottom:18px;'>"
        "<div style='display:flex; align-items:center; justify-content:space-between;'>"
        "<span style='font-size:24px; font-weight:800; color:#ffffff;'>" + icon + "&nbsp; " + title + "</span>"
        "<span style='font-size:13px; color:rgba(255,255,255,0.45); font-weight:600; "
        "background:rgba(255,255,255,0.06); padding:3px 10px; border-radius:20px;'>"
        "אזור " + str(number) + "/" + str(total) + "</span>"
        "</div>"
        + sub_html
        + (("<div style='margin-top:6px;'>" + period_tag + "</div>") if period_tag else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def section_header(title, accent):
    # כותרת אזור מובלטת עם פס צבעוני ורקע עדין, להפרדה ברורה בתוך הכרטיס
    return ("<div dir='rtl' style='text-align:right; font-weight:800; font-size:18px; "
            "background:rgba(120,120,120,0.10); border-right:5px solid " + accent +
            "; border-radius:6px; padding:8px 12px; margin:20px 0 10px 0;'>"
            + title + "</div>")


def render_sentiment_trend(seasons, scores, chart_key):
    """גרף קו של סנטימנט לאורך עונות. seasons/scores = רשימות מסונכרנות, לפחות 2 פריטים."""
    colors = ["#22c55e" if s >= 0.15 else ("#ef4444" if s <= -0.15 else "#9ca3af") for s in scores]
    labels = [("+" if int(round(s * 100)) >= 0 else "") + str(int(round(s * 100))) + "%" for s in scores]

    # ציר Y דינמי: ריפוד פרופורציונלי עם רצפה מינימלית, מוגבל לתחום [-1, 1]
    _s_min = min(scores)
    _s_max = max(scores)
    _pad = max((_s_max - _s_min) * 0.18, 0.15)
    _y_low  = max(_s_min - _pad, -1.0)
    _y_high = min(_s_max + _pad + 0.08, 1.0)  # +0.08 מרווח לתוויות מעל הנקודות

    # tickvals מתוך רשת קבועה של 25%; מסננים לטווח הגלוי בלבד
    _candidates = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
    _tick_vals  = [t for t in _candidates if _y_low - 0.01 <= t <= _y_high + 0.01]
    _tick_text  = [("+" if t > 0 else "") + str(int(round(t * 100))) + "%" for t in _tick_vals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=seasons, y=scores, mode="lines+markers+text",
        line=dict(color="#60a5fa", width=2.5),
        marker=dict(size=14, color=colors, line=dict(color="#1e2533", width=2)),
        text=labels, textposition="top center",
        textfont=dict(size=13, color="#e5e7eb"),
        hovertemplate="<b>%{x}</b><br>ציון: %{y:.2f}<extra></extra>",
    ))
    if _y_low <= 0 <= _y_high:
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.25)", line_width=1)
    fig.update_layout(
        height=240, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,18,30,0.7)",
        margin=dict(t=28, b=36, l=60, r=70),
        yaxis=dict(
            range=[_y_low, _y_high],
            gridcolor="rgba(255,255,255,0.08)",
            tickvals=_tick_vals, ticktext=_tick_text,
            tickfont=dict(size=12, color="#9ca3af"),
            showline=True, linecolor="rgba(255,255,255,0.18)", linewidth=1,
            zeroline=False,
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=12, color="#9ca3af"),
            showline=True, linecolor="rgba(255,255,255,0.18)", linewidth=1,
            ticks="outside", ticklen=4, tickcolor="rgba(255,255,255,0.18)",
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def returns_table_html(pairs, descending=True, sentiment_data=None, season=None, outlier_map=None):
    sortable = [(change, symbol) for symbol, change in pairs]
    sortable.sort(reverse=descending)
    show_sent = sentiment_data is not None and season is not None
    rows = ""
    for change, symbol in sortable:
        c = "#22c55e" if change >= 0 else "#ef4444"
        is_outlier = outlier_map is not None and symbol in outlier_map
        row_style = " style='background:rgba(245,158,11,0.12);'" if is_outlier else ""
        if is_outlier:
            rel = outlier_map[symbol]
            rel_col = "#22c55e" if rel >= 0 else "#ef4444"
            rel_label = ("מכה " if rel >= 0 else "מפגר ") + str(round(abs(rel), 1)) + " נק'"
            sym_html = (
                "🎯 " + symbol +
                " <span style='font-size:11px; color:" + rel_col + ";'>" + rel_label + "</span>"
            )
            td_sym = (
                "<td style='text-align:right; padding:4px 10px; border-right:3px solid #f59e0b;'>"
                + sym_html + "</td>"
            )
        else:
            td_sym = "<td style='text-align:right; padding:4px 10px;'>" + symbol + "</td>"
        row = ("<tr" + row_style + ">"
               + td_sym
               + "<td style='text-align:right; padding:4px 10px; color:" + c +
               "; font-weight:600;'>" + str(round(change, 1)) + "%</td>")
        if show_sent:
            rec = get_record(sentiment_data, symbol, season)
            if rec and rec.get("sentiment_score") is not None:
                score = float(rec["sentiment_score"])
                pct = int(round(score * 100))
                sign = "+" if pct >= 0 else ""
                emoji = "🟢" if score >= 0.15 else ("🔴" if score <= -0.15 else "⚪")
                col = "#22c55e" if score >= 0.15 else ("#ef4444" if score <= -0.15 else "#9ca3af")
                sent_html = (emoji + " <span style='color:" + col +
                             "; font-weight:700;'>" + sign + str(pct) + "%</span>")
                report_date = rec.get("report_date", "—")
            else:
                sent_html = "<span style='color:#6b7280;'>—</span>"
                report_date = "—"
            row += ("<td style='text-align:center; padding:4px 10px; white-space:nowrap;'>"
                    + sent_html + "</td>"
                    "<td style='text-align:center; padding:4px 10px; color:#9ca3af; font-size:12px;'>"
                    + report_date + "</td>")
        rows += row + "</tr>"
    hdr = ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
           "<tr>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th>")
    if show_sent:
        hdr += ("<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>סנטימנט הדוח האחרון</th>"
                "<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>תאריך דוח</th>")
    return hdr + "</tr>" + rows + "</table>"


def tech_table_html(rows, sentiment_data=None, season=None):
    # טבלת מניות לתחום טכנולוגי: מניה, תשואה, משקל אפקטיבי, וסנטימנט דוח (אופציונלי)
    # rows = רשימה של [סימבול, תשואה, משקל מנורמל], כבר ממוינת מהגבוה לנמוך
    show_sent = sentiment_data is not None and season is not None
    body = ""
    for symbol, change, weight in rows:
        c = "#22c55e" if change >= 0 else "#ef4444"
        row = ("<tr><td style='text-align:right; padding:4px 10px;'>" + symbol +
               "</td><td style='text-align:right; padding:4px 10px; color:" + c +
               "; font-weight:600;'>" + str(round(change, 1)) + "%</td>"
               "<td style='text-align:right; padding:4px 10px; color:#9ca3af;'>" +
               str(round(weight * 100, 1)) + "%</td>")
        if show_sent:
            rec = get_record(sentiment_data, symbol, season)
            if rec and rec.get("sentiment_score") is not None:
                score = float(rec["sentiment_score"])
                pct = int(round(score * 100))
                sign = "+" if pct >= 0 else ""
                emoji = "🟢" if score >= 0.15 else ("🔴" if score <= -0.15 else "⚪")
                col = "#22c55e" if score >= 0.15 else ("#ef4444" if score <= -0.15 else "#9ca3af")
                sent_html = (emoji + " <span style='color:" + col +
                             "; font-weight:700;'>" + sign + str(pct) + "%</span>")
            else:
                sent_html = "<span style='color:#6b7280;'>—</span>"
            row += "<td style='text-align:center; padding:4px 10px; white-space:nowrap;'>" + sent_html + "</td>"
        body += row + "</tr>"
    hdr = ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
           "<tr><th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>משקל בתחום</th>")
    if show_sent:
        hdr += "<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>סנטימנט הדוח האחרון</th>"
    return hdr + "</tr>" + body + "</table>"


def sentiment_cell_html(agg, wrapper="td", width="110px"):
    """תא HTML לסנטימנט דוחות. agg = תוצאת aggregate_sentiment, או None.
    wrapper='td' לטבלאות HTML, wrapper='span' לשורות flexbox (מפת החום)."""
    if agg is None:
        empty_style = "text-align:center; padding:6px 8px; color:#6b7280; font-size:12px;"
        if wrapper == "span":
            return f"<span style='width:{width}; {empty_style}'>—</span>"
        return f"<td style='{empty_style}'>—</td>"
    score = agg["score"]
    reported = agg["reported"]
    total = agg["total"]
    pct = int(round(score * 100))
    sign = "+" if pct >= 0 else ""
    if score >= 0.15:
        emoji = "🟢"
        color = "#22c55e"
    elif score <= -0.15:
        emoji = "🔴"
        color = "#ef4444"
    else:
        emoji = "⚪"
        color = "#9ca3af"
    cov_color = "#9ca3af" if reported <= 1 else "#6b7280"
    cov = f"<span style='color:{cov_color}; font-size:10px;'>({reported}/{total})</span>"
    inner = f"{emoji} <span style='color:{color}; font-weight:700;'>{sign}{pct}%</span> {cov}"
    if wrapper == "span":
        return (f"<span style='width:{width}; text-align:center; white-space:nowrap; display:inline-block;'>"
                f"{inner}</span>")
    return f"<td style='text-align:center; padding:6px 8px; white-space:nowrap;'>{inner}</td>"


def weighted_score_html(ws, wrapper="span"):
    """תא/span HTML לציון המשוקלל (weighted_tech_score). wrapper='span' לשורות flex."""
    width = "140px"
    empty_style = "text-align:center; padding:6px 8px; color:#6b7280; font-size:12px;"
    if ws is None:
        if wrapper == "span":
            return "<span style='width:" + width + "; " + empty_style + "'>—</span>"
        return "<td style='" + empty_style + "'>—</td>"
    score = ws["score"]
    pct = int(round(score * 100))
    sign = "+" if pct >= 0 else ""
    if score >= 0.15:
        emoji, color = "🟢", "#22c55e"
    elif score <= -0.15:
        emoji, color = "🔴", "#ef4444"
    else:
        emoji, color = "⚪", "#9ca3af"
    cov_parts = []
    if ws["comp_reported"]:
        cov_parts.append(str(ws["comp_reported"]) + "/" + str(ws["comp_total"]) + " חב׳")
    if ws["sig_count"]:
        cov_parts.append(str(ws["sig_count"]) + " סיג׳")
    cov = ("<span style='color:#6b7280; font-size:10px;'>" +
           ("(" + " · ".join(cov_parts) + ")" if cov_parts else "") + "</span>")
    inner = (emoji + " <span style='color:" + color + "; font-weight:700;'>" +
             sign + str(pct) + "%</span> " + cov)
    if wrapper == "span":
        return ("<span style='width:" + width + "; text-align:center; "
                "white-space:nowrap; display:inline-block;'>" + inner + "</span>")
    return "<td style='text-align:center; padding:6px 8px; white-space:nowrap;'>" + inner + "</td>"


def capex_guidance_table_html(rows):
    # טבלה מסכמת של התחזיות: חברה, תחזית אחרונה, תחזית קודמת, שינוי ביניהן,
    # ושינוי התחזית מול ה-CapEx בפועל של השנה הקודמת.
    # rows = רשימת מילונים עם המפתחות: name, last, prev, chg_prev, chg_actual
    def pct_cell(v):
        if v is None:
            return "<td style='text-align:center; padding:6px 10px; color:#6b7280;'>—</td>"
        c = "#22c55e" if v >= 0 else "#ef4444"
        sg = "+" if v >= 0 else ""
        return ("<td style='text-align:center; padding:6px 10px; color:" + c +
                "; font-weight:700;'>" + sg + str(round(v, 1)) + "%</td>")

    def usd_cell(v):
        if v is None:
            return "<td style='text-align:center; padding:6px 10px; color:#6b7280;'>—</td>"
        return ("<td style='text-align:center; padding:6px 10px;'>$" +
                str(round(v, 1)) + "B</td>")

    body = ""
    for r in rows:
        body += ("<tr>"
                 "<td style='text-align:right; padding:6px 10px; font-weight:600;'>" + r["name"] + "</td>"
                 + usd_cell(r["last"])
                 + usd_cell(r["prev"])
                 + pct_cell(r["chg_prev"])
                 + usd_cell(r["actual_prev"])
                 + pct_cell(r["chg_actual"])
                 + "</tr>")
    return ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px; font-size:14px;'>"
            "<tr style='border-bottom:1px solid #666;'>"
            "<th style='text-align:right; padding:6px 10px;'>חברה</th>"
            "<th style='text-align:center; padding:6px 10px;'>תחזית אחרונה</th>"
            "<th style='text-align:center; padding:6px 10px;'>תחזית קודמת</th>"
            "<th style='text-align:center; padding:6px 10px;'>שינוי בתחזית</th>"
            "<th style='text-align:center; padding:6px 10px;'>שנה קודמת בפועל</th>"
            "<th style='text-align:center; padding:6px 10px;'>תחזית מול בפועל</th>"
            "</tr>" + body + "</table>")


def render_ai_alert(soxx_change, holdings_pairs, period, period_label):
    if soxx_change is None:
        return
    if period in DAILY_PERIODS:
        if abs(soxx_change) >= MOVE_ALERT:
            alert_color = "#22c55e" if soxx_change >= 0 else "#ef4444"
            arrow = "▲" if soxx_change >= 0 else "▼"
            pct_html = "<span style='color:" + alert_color + ";'>" + arrow + " " + str(round(soxx_change, 2)) + "%</span>"
            st.markdown(
                "<div dir='rtl' style='background:rgba(120,120,120,0.12); border:2px solid " + alert_color +
                "; border-radius:10px; padding:12px 16px; margin:10px 0; text-align:right; font-size:17px; font-weight:700;'>"
                "🚨 התראת תנועה חריגה — SOXX " + pct_html + " ביום המסחר האחרון</div>",
                unsafe_allow_html=True,
            )
            movers = []
            for sym, ch in holdings_pairs[:3]:
                movers.append(sym + " " + str(round(ch, 1)) + "%")
            for sym, ch in holdings_pairs[-3:]:
                movers.append(sym + " " + str(round(ch, 1)) + "%")
            movers_text = ", ".join(movers)

            with st.spinner("מבקש הסבר מ-Gemini עם חיפוש ברשת..."):
                text, sources = gemini_explain_move(round(soxx_change, 2), period_label, period, movers_text)
            if text:
                st.markdown("<div dir='rtl' style='text-align:right; font-weight:700; margin-top:8px;'>🧠 הסבר לתנועה:</div>", unsafe_allow_html=True)
                st.markdown("<div dir='rtl' style='text-align:right;'>" + text + "</div>", unsafe_allow_html=True)
                if sources:
                    with st.expander("מקורות"):
                        for title, uri in sources:
                            st.markdown("• [" + (title or uri) + "](" + uri + ")")
            else:
                st.caption("הסבר AI לא זמין כרגע (חסר מפתח Gemini).")
    else:
        stamp = period_stamp(period)
        trend_key = "trend_" + period + "_" + stamp
        if st.button("🧠 סכם לי את המגמה בתקופה הזו"):
            lines = []
            for sector in value_chain:
                pr = get_changes(value_chain[sector], period)
                if len(pr) == 0:
                    continue
                nums = [c for s, c in pr]
                med = statistics.median(nums)
                lines.append(clean_name(sector) + " " + str(round(med, 1)) + "%")
            sector_lines = ", ".join(lines)
            with st.spinner("מבקש סיכום מגמה מ-Gemini..."):
                text, sources = gemini_trend_summary(period_label, period, soxx_change, sector_lines)
            st.session_state[trend_key] = {"text": text, "sources": sources}

        saved = st.session_state.get(trend_key)
        if saved and saved.get("text"):
            st.markdown("<div dir='rtl' style='text-align:right; font-weight:700; margin-top:8px;'>🧠 סיכום המגמה:</div>", unsafe_allow_html=True)
            st.markdown("<div dir='rtl' style='text-align:right;'>" + saved["text"] + "</div>", unsafe_allow_html=True)
            if saved.get("sources"):
                with st.expander("מקורות"):
                    for title, uri in saved["sources"]:
                        st.markdown("• [" + (title or uri) + "](" + uri + ")")


# ---------- ממשק ----------
st.title("💹 דשבורד שרשרת הערך של השבבים")
if DEV_MODE:
    st.markdown(
        "<div style='background:rgba(234,179,8,0.15); border:1px solid #ca8a04; "
        "border-radius:8px; padding:6px 14px; margin-bottom:6px; "
        "font-size:13px; font-weight:700; color:#fbbf24; direction:rtl; text-align:right;'>"
        "🔧 מצב מפתח פעיל</div>",
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    "<div dir='rtl' style='text-align:right; margin-bottom:10px;'>"
    "<div style='font-size:12px; font-weight:700; color:#9ca3af; "
    "margin-bottom:8px; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1);'>"
    "📑 ניווט מהיר</div>"
    "<div style='display:flex; flex-direction:column; gap:4px;'>"
    "<a href='#zone-1' style='color:#f59e0b; text-decoration:none; font-size:13px;'>🏆 SOXX — מדד השבבים</a>"
    "<a href='#zone-2' style='color:#3b82f6; text-decoration:none; font-size:13px;'>🗺️ מפת חום — שרשרת הערך</a>"
    "<a href='#zone-3' style='color:#22c55e; text-decoration:none; font-size:13px;'>🔍 צלילה לתחום</a>"
    "<a href='#zone-4' style='color:#a78bfa; text-decoration:none; font-size:13px;'>🧬 פילוח טכנולוגי</a>"
    "<a href='#zone-5' style='color:#22d3ee; text-decoration:none; font-size:13px;'>🏗️ CapEx — ענקיות הענן</a>"
    "<a href='#zone-6' style='color:#f59e0b; text-decoration:none; font-size:13px;'>📋 דוחות — עונת הדוחות</a>"
    "</div></div>",
    unsafe_allow_html=True,
)
st.sidebar.divider()

period_label = st.sidebar.selectbox("Period:", list(PERIOD_OPTIONS.keys()), index=3)
period = PERIOD_OPTIONS[period_label]
st.sidebar.caption("משפיע על אזורים 1–4 בלבד")

# ======================================================
# אזור SOXX
# ======================================================
section_banner(1, 6, "🏆", "מדד סקטור השבבים — SOXX", "#f59e0b",
               subtitle="התנהגות המדד הכללי, עם התראות AI על תנועות חריגות",
               period_dependent=True, period_label=period_label)
soxx_close = get_history(BENCHMARK, period)

if soxx_close is None:
    st.warning("לא הצלחנו למשוך נתוני SOXX כרגע")
    soxx_change = None
    holdings_pairs = []
else:
    soxx_change = get_change(BENCHMARK, period)
    if soxx_change is None:
        soxx_change = 0.0
    soxx_color = "#22c55e" if soxx_change >= 0 else "#ef4444"
    sign = "+" if soxx_change >= 0 else ""

    st.markdown(
        "<h3>🏆 SOXX — מדד סקטור השבבים "
        "(<span style='color:" + soxx_color + ";'>" + sign + str(round(soxx_change, 1)) + "%</span>)</h3>",
        unsafe_allow_html=True,
    )
    st.caption("תקופה: " + period_label)

    holdings_pairs = get_changes(SOXX_HOLDINGS, period)
    holdings_pairs.sort(key=lambda x: x[1], reverse=True)

    render_ai_alert(soxx_change, holdings_pairs, period, period_label)

    # לגרף הקטן בלבד: בתקופות יומיות (online / lastclose) מציגים את יום המסחר
    # המלא האחרון שהסתיים — שעות פתיחה עד סגירה — במקום סדרת ימים.
    # שאר התקופות (1M, 3M וכו') ללא שינוי. אם משיכת התוך-יומי נכשלת — נפילה
    # בחזרה למקור המקורי.
    mini_source = soxx_close
    _mini_prev_close = None
    if period in DAILY_PERIODS:
        # lastclose: מדלג על היום הנוכחי אם השוק פתוח → יום מלא אחרון שהסתיים
        # online: תמיד לוקח את היום האחרון הזמין, גם אם חלקי (שוק פתוח עכשיו)
        _skip = (period == "lastclose")
        _session, _mini_prev_close = get_last_session_intraday(BENCHMARK, skip_current_day=_skip)
        if _session is not None:
            mini_source = _session
        else:
            _mini_prev_close = None
    soxx_price = mini_source.reset_index()
    soxx_price.columns = ["תאריך", "מחיר"]
    base_price = soxx_price["מחיר"].iloc[0]
    soxx_price["תשואה"] = soxx_price["מחיר"] / base_price * 100 - 100
    # תשואה צבועה לבועה: ירוק לחיובי, אדום לשלילי, שתי ספרות
    ret_cells = []
    for v in soxx_price["תשואה"]:
        col = "#22c55e" if v >= 0 else "#ef4444"
        sg = "+" if v >= 0 else ""
        ret_cells.append("<span style='color:" + col + "'>" + sg + format(v, ".2f") + "%</span>")

    # בתקופות יומיות ציר הזמן הוא שעות; בשאר — תאריכים
    _mini_xfmt = "%H:%M" if period in DAILY_PERIODS else "%d/%m/%Y"
    # צבע דינמי: ירוק אם התקופה עלתה, אדום אם ירדה.
    # בתקופות יומיות — ייחוס מול סגירה קודמת; בשאר — ייחוס מול נקודת פתיחת הסדרה.
    _mini_ref = _mini_prev_close if _mini_prev_close is not None else base_price
    _mini_last_price = float(soxx_price["מחיר"].iloc[-1])
    if _mini_last_price >= _mini_ref:
        _mini_line_color = "#22c55e"
        _mini_fill_color = "rgba(34,197,94,0.15)"
    else:
        _mini_line_color = "#ef4444"
        _mini_fill_color = "rgba(239,68,68,0.15)"
    mini = go.Figure()
    mini.add_trace(go.Scatter(
        x=soxx_price["תאריך"], y=soxx_price["מחיר"], mode="lines",
        line=dict(color=_mini_line_color, width=2.5), fill="tozeroy",
        fillcolor=_mini_fill_color,
        customdata=ret_cells,
        hovertemplate="%{x|" + _mini_xfmt + "}<br>מחיר: $%{y:.2f}<br>תשואה: %{customdata}<extra></extra>",
    ))
    # ציר Y דינמי: לא מתחילים מאפס, אלא מרווח קטן סביב טווח המחירים בפועל,
    # כדי שתנועת המחיר תיראה נכון (בעיקר בתקופות קצרות). מילוי עדין עד תחתית הציר.
    price_min = float(soxx_price["מחיר"].min())
    price_max = float(soxx_price["מחיר"].max())
    # אם יש קו סגירה קודמת מעל/מתחת לטווח היום — מרחיבים את הטווח שיכלול אותו
    if _mini_prev_close is not None:
        price_min = min(price_min, _mini_prev_close)
        price_max = max(price_max, _mini_prev_close)
    price_pad = (price_max - price_min) * 0.15
    if price_pad == 0:
        price_pad = price_max * 0.01 if price_max else 1.0
    y_low = price_min - price_pad
    y_high = price_max + price_pad
    mini.update_layout(
        height=240, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=30, l=50, r=20),
        yaxis=dict(title="מחיר ($)", gridcolor="rgba(255,255,255,0.08)",
                   range=[y_low, y_high]),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                   tickformat=("%H:%M" if period in DAILY_PERIODS else None)),
        showlegend=False,
    )
    st.plotly_chart(mini, use_container_width=True)
    st.markdown(
        "<div style='margin:8px 0 20px; border-top:1px solid rgba(255,255,255,0.08);'></div>",
        unsafe_allow_html=True,
    )

    if len(holdings_pairs) >= 2:
        top5 = holdings_pairs[:5]
        bottom5 = list(reversed(holdings_pairs[-5:]))

        # חריגות — מחושבות לפני הטבלאות (מזינות סימון) ומשמשות גם לכפתור אחרי הטבלאות
        if soxx_change is not None and period in DAILY_PERIODS:
            _outliers = sorted(
                [(sym, ch, ch - soxx_change) for sym, ch in holdings_pairs
                 if abs(ch - soxx_change) >= STOCK_VS_SOXX_ALERT],
                key=lambda x: -abs(x[2]),
            )
        else:
            _outliers = []
        _outlier_map = {sym: rel for sym, ch, rel in _outliers}

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📈 העליות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(top5, descending=True, outlier_map=_outlier_map), unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📉 הירידות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(bottom5, descending=False, outlier_map=_outlier_map), unsafe_allow_html=True)

        if _outliers:
            st.caption(
                "🎯 מניות המסומנות סטו ≥" + str(int(STOCK_VS_SOXX_ALERT)) +
                " נק' מ-SOXX ביום המסחר האחרון — תנועה שאינה מוסברת על ידי המדד הכללי."
            )
            _out_stamp = period_stamp(period)
            _out_key = "outliers_" + period + "_" + _out_stamp
            if st.button("🧠 הסבר את התנועות החריגות", key="outliersbtn_" + period):
                _otxt = ", ".join(
                    sym + " " + ("+" if ch >= 0 else "") + str(round(ch, 1)) + "%" +
                    " (מרחק " + ("+" if rel >= 0 else "") + str(round(rel, 1)) + " נק' מ-SOXX)"
                    for sym, ch, rel in _outliers
                )
                with st.spinner("מבקש הסבר חריגות מ-Gemini עם חיפוש ברשת..."):
                    _out_text, _out_sources = gemini_explain_outliers(
                        soxx_change, _otxt, period, period_label
                    )
                st.session_state[_out_key] = {"text": _out_text, "sources": _out_sources}
            _saved_out = st.session_state.get(_out_key)
            if _saved_out and _saved_out.get("text"):
                st.markdown(
                    "<div dir='rtl' style='text-align:right; font-weight:700; margin-top:8px;'>🧠 הסבר החריגות:</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div dir='rtl' style='text-align:right;'>" + _saved_out["text"] + "</div>",
                    unsafe_allow_html=True,
                )
                if _saved_out.get("sources"):
                    with st.expander("מקורות"):
                        for title, uri in _saved_out["sources"]:
                            st.markdown("• [" + (title or uri) + "](" + uri + ")")


# ---------- חישוב הדירוג ----------
with st.spinner("סורק את כל התחומים..."):
    results = []
    for sector in value_chain:
        pairs = get_changes(value_chain[sector], period)
        if len(pairs) == 0:
            continue
        numbers = []
        for s, c in pairs:
            numbers.append(c)
        median = statistics.median(numbers)
        average = sum(numbers) / len(numbers)
        up = 0
        down = 0
        for c in numbers:
            if c > 0:
                up = up + 1
            elif c < 0:
                down = down + 1
        breadth = up / len(numbers)
        results.append((median, average, up, down, len(numbers), breadth, sector, pairs))
    # דירוג לפי המרחק מהמדד: חציון פחות תשואת SOXX, מהגבוה לנמוך
    soxx_ref = soxx_change if soxx_change is not None else 0.0
    results.sort(key=lambda r: r[0] - soxx_ref, reverse=True)
    # המרחק הקיצוני ביותר מהמדד בדירוג — לנרמול עוצמת הצבע
    if len(results) > 0:
        max_abs_dist = max(abs(r[0] - soxx_ref) for r in results)
    else:
        max_abs_dist = 1.0


# ---------- מפת חום ----------
def render_earnings_analysis_ui(sector, symbols, season):
    """כלי ניתוח דוח: selectbox + Gemini + תצוגת תוצאה + שמירה לקובץ."""
    st.markdown(section_header("🧠 ניתוח דוח ושיחת ועידה", "#f59e0b"), unsafe_allow_html=True)
    col_sel, col_btn = st.columns([3, 1])
    sk = sector_key(sector)
    with col_sel:
        chosen_sym = st.selectbox("בחרי חברה לניתוח:", symbols, key="earningsym_" + sk)
    result_key = "earnings_result_" + chosen_sym + "_" + season
    with col_btn:
        st.markdown("<div style='height:27px;'></div>", unsafe_allow_html=True)
        if st.button("🧠 נתח דוח", key="analyzebtn_" + chosen_sym + "_" + sk,
                     use_container_width=True):
            with st.spinner("מחפש דוח ושיחת ועידה ב-Gemini..."):
                st.session_state[result_key] = gemini_analyze_earnings(chosen_sym, season)

    result = st.session_state.get(result_key)
    if result is None:
        return

    if "error" in result:
        st.warning(result["error"])
        return

    score = result.get("sentiment_score", 0) or 0
    pct = int(round(score * 100))
    sign = "+" if pct >= 0 else ""
    sent_emoji = "🟢" if score >= 0.15 else ("🔴" if score <= -0.15 else "⚪")
    sent_color = "#22c55e" if score >= 0.15 else ("#ef4444" if score <= -0.15 else "#9ca3af")
    res_map = {"beat": "🟢 הכה ציפיות", "meet": "⚪ עמד בציפיות", "miss": "🔴 פספס ציפיות"}
    guid_map = {"raised": "📈 הועלתה", "maintained": "➡️ נשמרה", "lowered": "📉 הורדה", "none": "—"}
    res_txt = res_map.get(result.get("results_vs_expectations", ""), "—")
    guid_txt = guid_map.get(result.get("guidance_direction", ""), "—")
    report_date = result.get("report_date", "—")

    with st.container(border=True):
        st.markdown(
            "<div dir='rtl' style='text-align:right;'>"
            "<span style='font-size:18px; font-weight:800;'>" + chosen_sym + "</span>"
            "<span style='color:#9ca3af; font-size:13px; margin-right:10px;'>" + season + " · " + report_date + "</span>"
            "</div>"
            "<div dir='rtl' style='display:flex; gap:24px; margin:10px 0; flex-wrap:wrap;'>"
            "<span>סנטימנט: " + sent_emoji + " <b style='color:" + sent_color + ";'>" + sign + str(pct) + "%</b></span>"
            "<span>תוצאות: " + res_txt + "</span>"
            "<span>הנחיה: " + guid_txt + "</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        summary = result.get("summary", "")
        if summary:
            st.markdown(
                "<div dir='rtl' style='text-align:right; color:#d1d5db; font-size:14px; "
                "margin:8px 0; line-height:1.6;'>" + summary + "</div>",
                unsafe_allow_html=True,
            )
        signals = result.get("domain_signals", [])
        if signals:
            dir_map = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
            rows_html = ""
            for sig in signals:
                icon = dir_map.get(sig.get("direction", ""), "")
                rows_html += (
                    "<tr>"
                    "<td style='text-align:right; padding:3px 8px; font-size:13px;'>" + sig.get("domain", "") + "</td>"
                    "<td style='text-align:center; padding:3px 8px;'>" + icon + "</td>"
                    "<td style='text-align:right; padding:3px 8px; color:#9ca3af; font-size:12px;'>" + sig.get("note", "") + "</td>"
                    "</tr>"
                )
            st.markdown(
                "<div dir='rtl'><b style='font-size:13px;'>סיגנלים תחומיים:</b>"
                "<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:4px;'>"
                "<tr><th style='text-align:right; padding:3px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>תחום</th>"
                "<th style='text-align:center; padding:3px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>כיוון</th>"
                "<th style='text-align:right; padding:3px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>הערה</th></tr>"
                + rows_html + "</table></div>",
                unsafe_allow_html=True,
            )

        save_col, discard_col = st.columns([1, 1])
        with save_col:
            if st.button("✅ שמור לקובץ", key="savebtn_" + chosen_sym + "_" + sk,
                         use_container_width=True, type="primary"):
                record = {
                    "report_date": report_date,
                    "sentiment_score": result.get("sentiment_score"),
                    "results_vs_expectations": result.get("results_vs_expectations", ""),
                    "guidance_direction": result.get("guidance_direction", ""),
                    "summary": summary,
                    "domain_signals": signals,
                    "revenue_actual_b": result.get("revenue_actual_b"),
                    "revenue_estimate_b": result.get("revenue_estimate_b"),
                    "eps_actual": result.get("eps_actual"),
                    "eps_estimate": result.get("eps_estimate"),
                    "next_q_guidance": result.get("next_q_guidance"),
                    "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
                save_sentiment_record(chosen_sym, season, record)
                del st.session_state[result_key]
                st.success("נשמר: " + chosen_sym + " / " + season)
                st.rerun()
        with discard_col:
            if st.button("🗑️ בטל", key="discardbtn_" + chosen_sym + "_" + sk,
                         use_container_width=True):
                del st.session_state[result_key]
                st.rerun()


def render_domain_detail(sector, pairs, period):
    """מרנדר את תוכן הפרטים של תחום: מניות, גרף מגמת הפער, וחדשות + ניתוח AI.
    משמש גם במפת החום (שרשרת ערך). נקרא רק כשהשורה של התחום פתוחה."""
    # --- אזור טבלת המניות ---
    st.markdown(section_header("📊 מניות בתחום", "#3b82f6"), unsafe_allow_html=True)
    _det_sent = load_sentiment()
    _det_season = latest_season_with_data(_det_sent)
    st.markdown(returns_table_html(pairs, sentiment_data=_det_sent, season=_det_season), unsafe_allow_html=True)

    # --- גרף מגמת הפער מ-SOXX לאורך התקופה ---
    st.markdown(section_header("📈 מגמת הפער מ-SOXX לאורך התקופה", "#22c55e"), unsafe_allow_html=True)
    spread_chart = build_spread_chart(value_chain[sector], period,
                                      intraday=(period in DAILY_PERIODS),
                                      skip_current_day=(period == "lastclose"))
    if spread_chart is not None:
        st.altair_chart(spread_chart, use_container_width=True)
        st.caption("🟢 מעל הקו = התחום מכה את SOXX · 🔴 מתחת = מפגר · הנקודה האחרונה = הפער הנוכחי")
    else:
        st.caption("אין מספיק נתונים לגרף המגמה")

    # --- מגמת סנטימנט לאורך עונות ---
    _vc_all_s = sorted({s for _sd in _det_sent.values() for s in _sd})
    _vc_tx, _vc_ty = [], []
    for _s in _vc_all_s:
        _agg_vc = value_chain_sentiment(sector, _s, _det_sent)
        if _agg_vc is not None:
            _vc_tx.append(_s)
            _vc_ty.append(_agg_vc["score"])
    if len(_vc_tx) >= 2:
        st.markdown(section_header("📈 מגמת סנטימנט לאורך עונות", "#22d3ee"), unsafe_allow_html=True)
        render_sentiment_trend(_vc_tx, _vc_ty, "trend_vc_" + sector_key(sector))
    elif len(_vc_tx) == 1:
        st.caption("עונה אחת שמורה לתחום זה — הגרף יופיע לאחר עונה נוספת.")

    # --- אזור החדשות ---
    sector_news = []
    for symbol, change in pairs:
        for item in get_news(symbol, limit=2):
            sector_news.append((symbol, item))

    st.markdown(section_header("📰 חדשות אחרונות בתחום", "#a78bfa"), unsafe_allow_html=True)
    if len(sector_news) == 0:
        st.caption("אין חדשות זמינות כרגע לתחום הזה")
        return

    st.caption("לחצי לניתוח סנטימנט החדשות עם AI")
    titles_list = [item["title"] for sym, item in sector_news]
    sig = titles_signature(titles_list)
    news_key = "news_analysis_" + sector_key(sector) + "_" + sig
    do_analyze = st.button("🧠 נתח חדשות", key="newsbtn_" + sector_key(sector))

    if do_analyze:
        titles_block = ""
        for t in titles_list:
            titles_block += "- " + t + "\n"
        with st.spinner("מנתח חדשות עם Gemini..."):
            st.session_state[news_key] = gemini_analyze_news(clean_name(sector), sig, titles_block)

    analysis = st.session_state.get(news_key)

    if analysis and "overall" in analysis:
        ov = analysis["overall"]
        ov_color = {"positive": "#22c55e", "negative": "#ef4444"}.get(ov, "#eab308")
        ov_label = {"positive": "🟢 חיובי", "negative": "🔴 שלילי"}.get(ov, "⚪ ניטרלי")
        st.markdown(
            "<div dir='rtl' style='text-align:right; color:" + ov_color +
            "; font-weight:700; margin:8px 0;'>סנטימנט חדשות בתחום: " + ov_label +
            " — " + analysis.get("overall_note", "") + "</div>",
            unsafe_allow_html=True,
        )
        if ov == "negative":
            st.markdown(
                "<div dir='rtl' style='text-align:right; color:#ef4444; font-weight:700;'>⚠️ הערת אזהרה: יש חדשות שליליות בתחום הזה</div>",
                unsafe_allow_html=True,
            )

    item_map = {}
    if analysis and "items" in analysis:
        for it in analysis["items"]:
            item_map[it.get("title", "")] = it

    for sym, item in sector_news:
        date_part = ""
        if item["date"]:
            date_part = " (" + item["date"] + ")"
        info = item_map.get(item["title"])
        badge = ""
        if info:
            s = info.get("sentiment", "neutral")
            emoji = {"positive": "🟢", "negative": "🔴"}.get(s, "⚪")
            risk = " ⚠️ סיכון" if s == "negative" else ""
            badge = emoji + risk + " "
        if item["link"]:
            title_html = "<a href='" + item["link"] + "' target='_blank'>" + item["title"] + "</a>"
        else:
            title_html = item["title"]
        summary_html = ""
        if info and info.get("summary"):
            summary_html = "<div style='color:#aaa; font-size:13px; margin-top:3px;'>" + info["summary"] + "</div>"
        st.markdown(
            "<div dir='rtl' style='text-align:right; background:rgba(255,255,255,0.03); "
            "border:1px solid #333; border-radius:8px; padding:8px 10px; margin-top:6px;'>"
            "<b>" + sym + "</b> · " + badge + title_html + date_part + summary_html + "</div>",
            unsafe_allow_html=True,
        )



st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(2, 6, "🗺️", "מפת חום — דירוג שרשרת הערך", "#3b82f6",
               subtitle="11 חוליות שרשרת הערך, מדורגות לפי המרחק מ-SOXX",
               period_dependent=True, period_label=period_label)
st.caption("מדורג לפי המרחק מ-SOXX — מי מכה את המדד הכי הרבה. הגרף מציג את התמונה; לחצי על שורה בטבלה למטה כדי לפתוח פרטים.")

# גרף עמודות אופקי לתצוגה: כל תחום לפי החציון שלו, ממוין מהגבוה לנמוך,
# עם קו SOXX בולט. הגרף הוא תצוגה בלבד; האינטראקציה בטבלה שמתחתיו.
heat_items = [(clean_name(r[6]), r[0]) for r in results]   # (שם נקי, חציון)
all_sectors = [r[6] for r in results]

with st.container(border=True):
    ranking_bar_chart(heat_items, "heat_bar_" + period, soxx_marker=soxx_change)

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# ---------- טבלת התחומים — טבלה צבעונית במסגרת + כפתור "פתח" אפור קטן ----------
# כל שורה מוצגת כ-HTML צבעוני, ולצידה (משמאל) כפתור "פתח/סגור" אפור קטן.
# מצב הפתיחה נשמר לפי זהות התחום (sector_key) — יציב בין תקופות.
soxx_hdr = ""
if soxx_change is not None:
    soxx_hdr = "SOXX " + ("+" if soxx_change >= 0 else "") + str(round(soxx_change, 1)) + "%"

_sentiment_data = load_sentiment()
_sent_season = latest_season_with_data(_sentiment_data)

with st.container(border=True):
    # כותרת עמודות
    h1, h2 = st.columns([9, 1.3])
    with h1:
        st.markdown(
            "<div dir='rtl' style='display:flex; align-items:center; padding:4px 10px; "
            "font-size:12px; color:#9ca3af; font-weight:600;'>"
            "<span style='width:32px; text-align:right;'>#</span>"
            "<span style='flex:1; text-align:right;'>תחום</span>"
            "<span style='width:80px; text-align:center;'>חציון</span>"
            "<span style='width:170px; text-align:center;'>מול המדד " + soxx_hdr + "</span>"
            "<span style='width:90px; text-align:center;'>רוחב</span>"
            "<span style='width:110px; text-align:center;'>סנטימנט הדוח האחרון</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

    rank = 1
    for median, average, up, down, total, breadth, sector, pairs in results:
        med_color = "#22c55e" if median >= 0 else "#ef4444"
        med_txt = ("+" if median >= 0 else "") + str(round(median, 1)) + "%"
        if soxx_change is not None:
            rel = median - soxx_change
            if rel >= 0:
                vs_color = "#22c55e"
                vs_txt = "▲ מכה ב-" + str(round(rel, 1)) + " נק'"
            else:
                vs_color = "#ef4444"
                vs_txt = "▼ מפגר ב-" + str(round(abs(rel), 1)) + " נק'"
        else:
            vs_color = "#9ca3af"
            vs_txt = "—"
        bcolor = "#22c55e" if breadth >= BROAD_THRESHOLD else ("#eab308" if breadth >= 0.4 else "#ef4444")

        open_key = "open_heat_" + sector_key(sector)
        is_open = st.session_state.get(open_key, False)
        row_bg = "rgba(96,165,250,0.12)" if is_open else "transparent"

        _agg = value_chain_sentiment(sector, _sent_season, _sentiment_data)
        _sent_span = sentiment_cell_html(_agg, wrapper="span")

        row_col, btn_col = st.columns([9, 1.3])
        with row_col:
            st.markdown(
                "<div dir='rtl' style='display:flex; align-items:center; padding:8px 10px; "
                "background:" + row_bg + "; border-top:1px solid rgba(255,255,255,0.06); "
                "border-radius:6px; min-height:34px;'>"
                "<span style='width:32px; text-align:right; color:#9ca3af;'>" + str(rank) + "</span>"
                "<span style='flex:1; text-align:right; font-weight:600;'>" + clean_name(sector) + "</span>"
                "<span style='width:80px; text-align:center; color:" + med_color + "; font-weight:700;'>" + med_txt + "</span>"
                "<span style='width:170px; text-align:center; color:" + vs_color + "; font-weight:600; font-size:14px;'>" + vs_txt + "</span>"
                "<span style='width:90px; text-align:center; color:" + bcolor + "; font-size:14px;'>" + str(up) + "/" + str(total) + " עלו</span>"
                + _sent_span +
                "</div>",
                unsafe_allow_html=True,
            )
        with btn_col:
            btn_txt = "סגור" if is_open else "פתח"
            if st.button(btn_txt, key="heatrow_" + sector_key(sector),
                         use_container_width=True, type="tertiary"):
                st.session_state[open_key] = not is_open
                st.rerun()

        if is_open:
            with st.container(border=True):
                render_domain_detail(sector, pairs, period)

        rank = rank + 1

# ---------- צלילה לתחום ----------
st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(3, 6, "🔍", "צלילה לתחום — השוואת מניות", "#22c55e",
               subtitle="בחרי תחום כדי להשוות בין המניות שבו, מול חציון התחום ומול SOXX",
               period_dependent=True, period_label=period_label)

sector_names = []
for r in results:
    sector_names.append(r[6])

chosen = st.selectbox("בחרי תחום:", sector_names, format_func=clean_name)

_z3_intraday = period in DAILY_PERIODS
_z3_skip = period == "lastclose"
_z3_xfmt = "%H:%M" if _z3_intraday else "%d/%m/%Y"
chart_data = build_chart(value_chain[chosen], period, intraday=_z3_intraday, skip_current_day=_z3_skip)
if chart_data.empty:
    st.warning("אין מספיק נתונים לתחום הזה")
else:
    # פלטת צבעים משותפת לשני הטאבים לעקביות ויזואלית
    palette = ["#60a5fa", "#f472b6", "#34d399", "#fbbf24", "#a78bfa",
               "#fb7185", "#22d3ee", "#a3e635", "#fb923c", "#e879f9",
               "#4ade80", "#38bdf8", "#facc15", "#f87171", "#c084fc"]

    _z3_tab_perf, _z3_tab_sent = st.tabs(["📈 ביצועי מניות", "🧠 סנטימנט התחום"])

    with _z3_tab_perf:
        st.caption("ביצועי המניות מול חציון התחום ומול מדד SOXX — הכל מנורמל ל-100 בתחילת התקופה. לחצי על מניה במקרא כדי להסתיר/להציג אותה.")

        date_index = chart_data.index
        median_series = chart_data.median(axis=1)
        if _z3_intraday:
            soxx_close2, _ = _get_intraday_session(BENCHMARK, _z3_skip)
        else:
            soxx_close2 = get_history(BENCHMARK, period)

        def ret_html(ret_series):
            out = []
            for v in ret_series:
                color = "#22c55e" if v >= 0 else "#ef4444"
                sign = "+" if v >= 0 else ""
                out.append("<span style='color:" + color + "'>" + sign + format(v, ".2f") + "%</span>")
            return out

        fig = go.Figure()
        fig.add_hline(y=100, line_dash="dot", line_color="#888", line_width=1)

        for i, symbol in enumerate(chart_data.columns):
            col_color = palette[i % len(palette)]
            series = chart_data[symbol]
            ret = series - 100
            fig.add_trace(go.Scatter(
                x=date_index, y=series, name=symbol, mode="lines",
                line=dict(color=col_color, width=1.6), opacity=0.85,
                customdata=ret_html(ret),
                hovertemplate="<b>" + symbol + "</b><br>%{x|" + _z3_xfmt + "}<br>"
                              "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
            ))

        median_ret = median_series - 100
        fig.add_trace(go.Scatter(
            x=date_index, y=median_series, name="חציון התחום", mode="lines",
            line=dict(color="#ffffff", width=4),
            customdata=ret_html(median_ret),
            hovertemplate="<b>חציון התחום</b><br>%{x|" + _z3_xfmt + "}<br>"
                          "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
        ))

        if soxx_close2 is not None:
            soxx_norm2 = soxx_close2 / soxx_close2.iloc[0] * 100
            soxx_ret = soxx_norm2 - 100
            fig.add_trace(go.Scatter(
                x=soxx_norm2.index, y=soxx_norm2, name="SOXX", mode="lines",
                line=dict(color="#f59e0b", width=4, dash="dash"),
                customdata=ret_html(soxx_ret),
                hovertemplate="<b>SOXX</b><br>%{x|" + _z3_xfmt + "}<br>"
                              "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
            ))

        fig.update_layout(
            height=460,
            hovermode="closest",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=40, l=50, r=40),
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.08,
                        title="מניה", font=dict(size=12),
                        bgcolor="rgba(255,255,255,0.04)",
                        bordercolor="rgba(255,255,255,0.20)", borderwidth=1),
            yaxis=dict(title="מנורמל ל-100", gridcolor="rgba(255,255,255,0.08)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                       tickformat=(_z3_xfmt if _z3_intraday else None)),
        )
        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("טבלת תשואות")
        chosen_pairs = get_changes(value_chain[chosen], period)
        st.markdown(returns_table_html(chosen_pairs), unsafe_allow_html=True)

        soxx_change2 = get_change(BENCHMARK, period)
        if soxx_change2 is not None and len(chosen_pairs) > 0:
            sector_median = statistics.median([c for s, c in chosen_pairs])
            diff = sector_median - soxx_change2
            better = "📈 התחום מכה את המדד" if diff >= 0 else "📉 התחום מפגר אחרי המדד"
            st.info("חציון התחום: " + str(round(sector_median, 1)) + "%  |  SOXX: " +
                    str(round(soxx_change2, 1)) + "%  →  " + better + " (" + str(round(diff, 1)) + " נק')")

    with _z3_tab_sent:
        # אגרגט התחום לאורך עונות — value_chain_sentiment (ממוצע פשוט, זהה לכרטיסיות)
        _z3_all_s = sorted({s for sd in _sentiment_data.values() for s in sd})
        _z3_tx, _z3_ty = [], []
        for _s in _z3_all_s:
            _agg = value_chain_sentiment(chosen, _s, _sentiment_data)
            if _agg is not None:
                _z3_tx.append(_s)
                _z3_ty.append(_agg["score"])

        # קו לכל מניה בתחום עם ≥2 עונות מנותחות
        _z3_syms = list(value_chain[chosen])
        _z3_sym_series: dict[str, tuple[list, list]] = {}
        for _sym in _z3_syms:
            _sx, _sy = [], []
            for _s in _z3_all_s:
                _r = (_sentiment_data.get(_sym) or {}).get(_s)
                if _r and _r.get("sentiment_score") is not None:
                    _sx.append(_s)
                    _sy.append(float(_r["sentiment_score"]))
            if len(_sx) >= 2:
                _z3_sym_series[_sym] = (_sx, _sy)

        if len(_z3_tx) < 2 and not _z3_sym_series:
            st.caption("אין מספיק נתוני סנטימנט להצגת מגמה (נדרשות ≥2 עונות).")
        else:
            # ציר Y דינמי — בדיוק כמו render_sentiment_trend
            _z3_all_scores = [v for (_, _sy) in _z3_sym_series.values() for v in _sy] + list(_z3_ty)
            if _z3_all_scores:
                _z3_s_min = min(_z3_all_scores); _z3_s_max = max(_z3_all_scores)
                _z3_pad = max((_z3_s_max - _z3_s_min) * 0.18, 0.15)
                _z3_y_low = max(_z3_s_min - _z3_pad, -1.0)
                _z3_y_high = min(_z3_s_max + _z3_pad + 0.08, 1.0)
            else:
                _z3_y_low, _z3_y_high = -1.0, 1.0
            _z3_cands = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
            _z3_tick_vals = [t for t in _z3_cands if _z3_y_low - 0.01 <= t <= _z3_y_high + 0.01]
            _z3_tick_text = [("+" if t > 0 else "") + str(int(round(t * 100))) + "%" for t in _z3_tick_vals]

            _z3_fig = go.Figure()
            if _z3_y_low <= 0 <= _z3_y_high:
                _z3_fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.25)", line_width=1)

            # קווי מניות דקים — אותה פלטה כמו טאב הביצועים
            for _ci, (_sym, (_sx, _sy)) in enumerate(_z3_sym_series.items()):
                _clr = palette[_ci % len(palette)]
                _z3_fig.add_trace(go.Scatter(
                    x=_sx, y=_sy, name=_sym, mode="lines+markers",
                    line=dict(color=_clr, width=1.5),
                    marker=dict(size=7, color=_clr, line=dict(color="#1e2533", width=1)),
                    hovertemplate="<b>" + _sym + "</b><br>%{x}: %{y:.2f}<extra></extra>",
                ))

            # קו התחום — לבן ועבה ומקווקו
            if len(_z3_tx) >= 2:
                _z3_fig.add_trace(go.Scatter(
                    x=_z3_tx, y=_z3_ty, name=chosen + " (תחום)", mode="lines+markers",
                    line=dict(color="#ffffff", width=3, dash="dash"),
                    marker=dict(size=10, color="#ffffff", line=dict(color="#1e2533", width=2)),
                    hovertemplate="<b>" + chosen + " (אגרגט)</b><br>%{x}: %{y:.2f}<extra></extra>",
                ))

            _z3_fig.update_layout(
                height=380, template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=55, r=10),
                yaxis=dict(range=[_z3_y_low, _z3_y_high], gridcolor="rgba(255,255,255,0.06)",
                           tickvals=_z3_tick_vals, ticktext=_z3_tick_text),
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(size=11)),
            )
            st.plotly_chart(_z3_fig, use_container_width=True, key="z3_sent_" + sector_key(chosen))

# ======================================================
# פילוח טכנולוגי — ליבה ומעטפת
# ======================================================
st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(4, 6, "🧬", "פילוח טכנולוגי — ליבה ומעטפת", "#a78bfa", period_dependent=True, period_label=period_label)
st.caption("כל תחום מדורג לפי תשואה משוקללת: ליבה (חשיפה × 1.0) ומעטפת (חשיפה × 0.4). "
           "שני צירים חופפים בכוונה — טכנולוגיה (מה מוכרים) ושוקי קצה (למי מוכרים) — אין להשוות ביניהם כסכום.")


def render_tech_detail(idx, sentiment_data=None, season=None, group_name=None):
    """מרנדר את פירוק הליבה/מעטפת של תחום טכנולוגי. נקרא כשהשורה פתוחה."""
    wret = idx["weighted_return"]
    sign = "+" if wret >= 0 else ""
    core_sign = "+" if idx["core_contrib"] >= 0 else ""
    env_sign = "+" if idx["env_contrib"] >= 0 else ""
    st.markdown(
        "<div dir='rtl' style='text-align:right; color:#999; font-size:13px; margin-bottom:10px;'>"
        "💡 <b>ליבה</b> = התחום הוא עיקר העסק (מכפיל 1.0) · <b>מעטפת</b> = מעגל שני שנהנה עקיפות (מכפיל 0.4). "
        "המשקל בטבלה = החלק האפקטיבי של המניה בתשואת התחום. "
        "תרומת הליבה: <b>" + core_sign + str(round(idx["core_contrib"], 1)) + " נק'</b> · "
        "תרומת המעטפת: <b>" + env_sign + str(round(idx["env_contrib"], 1)) + " נק'</b> — יחד = התשואה הכוללת.</div>",
        unsafe_allow_html=True,
    )
    right_col, left_col = st.columns(2)
    with right_col:
        st.markdown(
            "<div dir='rtl' style='text-align:center; font-weight:800; color:#22c55e; "
            "border-top:3px solid #22c55e; background:rgba(34,197,94,0.06); "
            "border-radius:6px; padding:6px; margin-bottom:4px;'>🎯 ליבת התחום</div>",
            unsafe_allow_html=True,
        )
        if idx["core"]:
            st.markdown(tech_table_html(idx["core"], sentiment_data=sentiment_data, season=season), unsafe_allow_html=True)
        else:
            st.caption("אין מניות ליבה עם נתונים")
    with left_col:
        st.markdown(
            "<div dir='rtl' style='text-align:center; font-weight:800; color:#f59e0b; "
            "border-top:3px solid #f59e0b; background:rgba(245,158,11,0.06); "
            "border-radius:6px; padding:6px; margin-bottom:4px;'>↪️ מעטפת — נהנות עקיפות</div>",
            unsafe_allow_html=True,
        )
        if idx["env"]:
            st.markdown(tech_table_html(idx["env"], sentiment_data=sentiment_data, season=season), unsafe_allow_html=True)
        else:
            st.caption("אין מניות מעטפת בתחום זה")

    # --- ניתוח סנטימנט בדוחות לתחום זה ---
    if group_name and sentiment_data and season:
        # פירוק הציון המשוקלל — מוצג רק כשיש שני מרכיבים
        _gd_def = None
        for _ax in TECH_GROUPS.values():
            if group_name in _ax:
                _gd_def = _ax[group_name]
                break
        if _gd_def is not None:
            _ws_detail = weighted_tech_score(group_name, _gd_def, season, sentiment_data)
            if _ws_detail and _ws_detail["comp_score"] is not None and _ws_detail["sig_score"] is not None:
                def _fmt(v):
                    p = int(round(v * 100))
                    s = "+" if p >= 0 else ""
                    c = "#22c55e" if v >= 0.15 else ("#ef4444" if v <= -0.15 else "#9ca3af")
                    return "<span style='color:" + c + "; font-weight:700;'>" + s + str(p) + "%</span>"
                st.markdown(
                    "<div dir='rtl' style='background:rgba(255,255,255,0.04); border-radius:8px; "
                    "padding:8px 14px; margin:8px 0; font-size:13px; display:flex; gap:20px; flex-wrap:wrap;'>"
                    "<span>ציון משולב: " + _fmt(_ws_detail["score"]) + "</span>"
                    "<span style='color:#9ca3af;'>│</span>"
                    "<span>סנטימנט חברות (70%): " + _fmt(_ws_detail["comp_score"]) +
                    " <span style='color:#6b7280; font-size:11px;'>(" +
                    str(_ws_detail["comp_reported"]) + "/" + str(_ws_detail["comp_total"]) + " חב׳)</span></span>"
                    "<span style='color:#9ca3af;'>│</span>"
                    "<span>סיגנלים (30%): " + _fmt(_ws_detail["sig_score"]) +
                    " <span style='color:#6b7280; font-size:11px;'>(" +
                    str(_ws_detail["sig_count"]) + " סיג׳)</span></span>"
                    "</div>",
                    unsafe_allow_html=True,
                )

        # רבעון קלנדרי קודם בדיוק (לא "האחרון שדיווח") — YYYYQN
        _td_prev_q = int(season[5]) - 1
        _td_prev_y = int(season[:4])
        if _td_prev_q == 0:
            _td_prev_q, _td_prev_y = 4, _td_prev_y - 1
        _td_prev_season = f"{_td_prev_y}Q{_td_prev_q}"

        _td_dir_emoji = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
        _td_dir_color = {"improving": "#22c55e", "stable": "#9ca3af", "deteriorating": "#ef4444"}
        _td_dir_order = {"improving": 0, "stable": 1, "deteriorating": 2}
        _td_entries = []
        for _sym, _sym_data in sentiment_data.items():
            _rec = _sym_data.get(season)
            if not _rec:
                continue
            for _sig in _rec.get("domain_signals", []):
                if _sig.get("domain") == group_name:
                    _prev_rec = _sym_data.get(_td_prev_season)
                    if _prev_rec is None:
                        # אין רשומה כלל לרבעון הקלנדרי הקודם
                        _prev_dir = None
                    else:
                        _prev_sig = next(
                            (s for s in _prev_rec.get("domain_signals", []) if s.get("domain") == group_name),
                            None,
                        )
                        # False = דיווח קיים אך ללא התייחסות לתחום זה
                        _prev_dir = _prev_sig.get("direction") if _prev_sig else False
                    _td_entries.append({
                        "sym": _sym,
                        "direction": _sig.get("direction", "stable"),
                        "note": _sig.get("note", ""),
                        "prev_dir": _prev_dir,
                    })
        if _td_entries:
            _td_entries.sort(key=lambda e: _td_dir_order.get(e["direction"], 1))
            _td_pos = sum(1 for e in _td_entries if e["direction"] == "improving")
            _td_neg = sum(1 for e in _td_entries if e["direction"] == "deteriorating")
            _td_net = _td_pos - _td_neg
            _td_net_col = "#22c55e" if _td_net > 0 else ("#ef4444" if _td_net < 0 else "#9ca3af")
            _td_net_sign = "+" if _td_net > 0 else ""
            _td_sig_rows = ""
            for e in _td_entries:
                _cur = e["direction"]
                _prev = e["prev_dir"]
                # פיצול להיפוך חיובי/שלילי — מעבר דרך stable אינו היפוך
                _is_pos_flip = isinstance(_prev, str) and _cur == "improving" and _prev == "deteriorating"
                _is_neg_flip = isinstance(_prev, str) and _cur == "deteriorating" and _prev == "improving"
                _is_flip = _is_pos_flip or _is_neg_flip
                _row_bg = (
                    " background:rgba(34,197,94,0.08);" if _is_pos_flip else
                    " background:rgba(239,68,68,0.10);" if _is_neg_flip else ""
                )
                # עמודת "כיוון רבעון קודם"
                if _prev is None:
                    _prev_dir_cell = "<span style='color:#6b7280;'>—</span>"
                elif _prev is False:
                    _prev_dir_cell = "<span style='color:#6b7280; font-style:italic;'>לא היתה התייחסות</span>"
                else:
                    _prev_dir_cell = (
                        "<span style='color:" + _td_dir_color.get(_prev, "#9ca3af") + ";'>"
                        + _td_dir_emoji.get(_prev, "") + "</span>"
                        + " <span style='color:#6b7280; font-size:11px;'>" + _td_prev_season + "</span>"
                    )
                # עמודת "מגמה" — רלוונטית רק כשיש כיוון קודם ממשי
                if not isinstance(_prev, str):
                    _trend_cell = "<span style='color:#6b7280;'>—</span>"
                elif _is_pos_flip:
                    _trend_cell = "<span style='color:#22c55e; font-weight:700;'>✅ שינוי לחיובי</span>"
                elif _is_neg_flip:
                    _trend_cell = "<span style='color:#ef4444; font-weight:700;'>⚠️ שינוי לשלילי</span>"
                else:
                    _trend_cell = "<span style='color:#ca8a04;'>ללא שינוי</span>"
                _td_sig_rows += (
                    "<tr style='border-top:1px solid rgba(255,255,255,0.07);" + _row_bg + "'>"
                    "<td style='text-align:right; padding:6px 10px; font-weight:600; white-space:nowrap;'>" + e["sym"] + "</td>"
                    "<td style='text-align:center; padding:6px 10px;'>"
                    "<span style='color:" + _td_dir_color.get(_cur, "#9ca3af") + "; font-size:16px;'>"
                    + _td_dir_emoji.get(_cur, "") + "</span></td>"
                    "<td style='text-align:right; padding:6px 10px; color:#d1d5db; font-size:12px;'>" + e["note"] + "</td>"
                    "<td style='text-align:center; padding:6px 10px; font-size:12px; white-space:nowrap;'>" + _prev_dir_cell + "</td>"
                    "<td style='text-align:center; padding:6px 10px; font-size:12px; white-space:nowrap;'>" + _trend_cell + "</td>"
                    "</tr>"
                )
            st.markdown(section_header("📡 ניתוח סנטימנט בדוחות — " + season, "#a78bfa"), unsafe_allow_html=True)
            st.markdown(
                "<div dir='rtl' style='margin-bottom:6px; font-size:13px; color:#9ca3af;'>"
                "ציון נטו: <b style='color:" + _td_net_col + ";'>" + _td_net_sign + str(_td_net) + "</b>"
                " · 📈 " + str(_td_pos) + " · 📉 " + str(_td_neg) + "</div>"
                "<div dir='rtl' style='overflow-x:auto;'>"
                "<table dir='rtl' style='width:100%; border-collapse:collapse; font-size:13px;'>"
                "<tr style='border-bottom:1px solid #444;'>"
                "<th style='text-align:right; padding:6px 10px; color:#9ca3af;'>חברה</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>כיוון</th>"
                "<th style='text-align:right; padding:6px 10px; color:#9ca3af;'>מה אמרה ההנהלה</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>כיוון רבעון קודם</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>מגמה</th>"
                "</tr>" + _td_sig_rows + "</table></div>",
                unsafe_allow_html=True,
            )

    # --- מגמת סנטימנט לאורך עונות (ברמת התחום) ---
    if group_name and sentiment_data:
        _gd = None
        for _axis in TECH_GROUPS.values():
            if group_name in _axis:
                _gd = _axis[group_name]
                break
        if _gd is not None:
            _all_s = sorted({s for sym_d in sentiment_data.values() for s in sym_d})
            _tx, _ty = [], []
            for _s in _all_s:
                _agg = tech_group_sentiment(_gd, _s, sentiment_data)
                if _agg is not None:
                    _tx.append(_s)
                    _ty.append(_agg["score"])
            if len(_tx) >= 2:
                st.markdown(section_header("📈 מגמת סנטימנט לאורך עונות", "#22d3ee"), unsafe_allow_html=True)
                render_sentiment_trend(_tx, _ty, "trend_tech_" + sector_key(group_name))
            elif len(_tx) == 1:
                st.caption("עונה אחת שמורה לתחום זה — הגרף יופיע לאחר עונה נוספת.")


_tech_sent_data = load_sentiment()
_tech_sent_season = latest_season_with_data(_tech_sent_data)

with st.spinner("מחשב את הפילוח הטכנולוגי..."):
    for axis_name, axis_groups in TECH_GROUPS.items():
        axis_color = "#3b82f6" if axis_name == "ציר טכנולוגיה" else "#a78bfa"
        st.markdown(
            "<div dir='rtl' style='text-align:right; font-weight:800; font-size:22px; "
            "margin:18px 0 8px 0; padding-bottom:4px; border-bottom:2px solid " + axis_color + ";'>"
            + axis_name + "</div>",
            unsafe_allow_html=True,
        )

        axis_results = []
        for group_name, group_def in axis_groups.items():
            idx = compute_tech_group_index(group_def, period)
            if idx is not None:
                axis_results.append((idx["weighted_return"], group_name, idx))

        # דירוג מהתשואה המשוקללת הגבוהה לנמוכה
        axis_results.sort(key=lambda x: x[0], reverse=True)

        if len(axis_results) == 0:
            st.caption("אין נתונים זמינים לציר זה כרגע")
            continue

        # גרף עמודות אופקי לתצוגה לציר: כל תחום לפי תשואתו המשוקללת.
        # הגרף הוא תצוגה בלבד; האינטראקציה בשורות שמתחתיו.
        axis_items = [(group_name, wret) for wret, group_name, idx in axis_results]
        axis_chart_key = "tech_bar_" + sector_key(axis_name) + "_" + period
        with st.container(border=True):
            ranking_bar_chart(axis_items, axis_chart_key)
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # טבלת התחומים של הציר — במסגרת, עם כפתור "פתח" אפור קטן
        with st.container(border=True):
            th1, th2 = st.columns([9, 1.3])
            with th1:
                st.markdown(
                    "<div dir='rtl' style='display:flex; align-items:center; padding:4px 10px; "
                    "font-size:12px; color:#9ca3af; font-weight:600;'>"
                    "<span style='width:32px; text-align:right;'>#</span>"
                    "<span style='flex:1; text-align:right;'>תחום</span>"
                    "<span style='width:90px; text-align:center;'>תשואה</span>"
                    "<span style='width:190px; text-align:center;'>ליבה / מעטפת</span>"
                    "<span style='width:140px; text-align:center;'>ציון משולב</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
            with th2:
                st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

            rankn = 1
            for wret, group_name, idx in axis_results:
                n_core = len(idx["core"])
                n_env = len(idx["env"])
                core_weight_pct = str(round(idx["core_weight"] * 100)) + "%"
                wret_color = "#22c55e" if wret >= 0 else "#ef4444"
                wret_txt = ("+" if wret >= 0 else "") + str(round(wret, 1)) + "%"
                open_key = "open_tech_" + sector_key(group_name)
                is_open = st.session_state.get(open_key, False)
                row_bg = "rgba(96,165,250,0.12)" if is_open else "transparent"

                _ws = weighted_tech_score(group_name, axis_groups[group_name], _tech_sent_season, _tech_sent_data)
                _tech_sent_span = weighted_score_html(_ws, wrapper="span")

                row_col, btn_col = st.columns([9, 1.3])
                with row_col:
                    st.markdown(
                        "<div dir='rtl' style='display:flex; align-items:center; padding:8px 10px; "
                        "background:" + row_bg + "; border-top:1px solid rgba(255,255,255,0.06); "
                        "border-radius:6px; min-height:34px;'>"
                        "<span style='width:32px; text-align:right; color:#9ca3af;'>" + str(rankn) + "</span>"
                        "<span style='flex:1; text-align:right; font-weight:600;'>" + group_name + "</span>"
                        "<span style='width:90px; text-align:center; color:" + wret_color + "; font-weight:700;'>" + wret_txt + "</span>"
                        "<span style='width:190px; text-align:center; color:#9ca3af; font-size:13px;'>"
                        "ליבה " + str(n_core) + " · מעטפת " + str(n_env) + " · משקל " + core_weight_pct + "</span>"
                        + _tech_sent_span +
                        "</div>",
                        unsafe_allow_html=True,
                    )
                with btn_col:
                    btn_txt = "סגור" if is_open else "פתח"
                    if st.button(btn_txt, key="techrow_" + sector_key(group_name),
                                 use_container_width=True, type="tertiary"):
                        st.session_state[open_key] = not is_open
                        st.rerun()

                if is_open:
                    with st.container(border=True):
                        render_tech_detail(idx, sentiment_data=_tech_sent_data,
                                           season=_tech_sent_season, group_name=group_name)
                rankn = rankn + 1

# ======================================================
# CapEx — השקעות ענקיות הענן
# ======================================================
st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(5, 6, "🏗️", "CapEx — השקעות ענקיות הענן", "#22d3ee",
               subtitle="ההשקעות ההוניות של מיקרוסופט, גוגל, אמזון ומטא — מנוע הביקוש של הסקטור",
               period_dependent=False)
st.caption("נתוני CapEx בפועל מדוחות תזרים המזומנים (yfinance). "
           "תחזיות שנתיות מוזנות ידנית מהשיחות ועידה. "
           "האזור אינו תלוי בתקופה שנבחרה בסרגל הצד.")

with st.spinner("מושך נתוני CapEx..."):
    capex_q = {}
    for sym in CAPEX_COMPANIES:
        s = get_capex_quarterly(sym)
        if s is not None:
            capex_q[sym] = s

if len(capex_q) == 0:
    st.warning("לא הצלחנו למשוך נתוני CapEx כרגע")
else:
    # --- שורת מדדים: הרבעון האחרון + שינוי מהרבעון הקודם ---
    metric_cols = st.columns(len(capex_q))
    for col, (sym, s) in zip(metric_cols, capex_q.items()):
        latest = float(s.iloc[-1])
        delta_txt = None
        if len(s) >= 2 and float(s.iloc[-2]) != 0:
            d = latest / float(s.iloc[-2]) * 100 - 100
            delta_txt = str(round(d, 1)) + "% מרבעון קודם"
        with col:
            st.metric(CAPEX_COMPANIES[sym] + " (" + sym + ")",
                      "$" + str(round(latest, 1)) + "B", delta_txt)

    # --- גרף רבעוני מקובץ: עמודה לכל חברה בכל רבעון ---
    st.markdown(section_header("📊 CapEx רבעוני — חברה מול חברה", "#22d3ee"),
                unsafe_allow_html=True)

    # אוסף את כל הרבעונים מכל החברות, ממיין כרונולוגית: הישן ביותר (Q1 2025) משמאל,
    # מתקדם ימינה עד הרבעון האחרון.
    all_quarters = set()
    for s in capex_q.values():
        for d in s.index:
            all_quarters.add((d.year, d.quarter))
    ordered_q = sorted(all_quarters)  # כרונולוגי: ישן -> חדש
    q_axis = ["Q" + str(q) + " " + str(y) for (y, q) in ordered_q]

    fig_capex = go.Figure()
    for sym, s in capex_q.items():
        # ממפה כל רבעון לערך שלו, כדי ליישר את כל החברות לאותו ציר
        val_by_q = {}
        for d, v in zip(s.index, s.values):
            val_by_q["Q" + str(d.quarter) + " " + str(d.year)] = float(v)
        y_vals = [val_by_q.get(q, None) for q in q_axis]
        fig_capex.add_trace(go.Bar(
            x=q_axis, y=y_vals,
            name=CAPEX_COMPANIES[sym] + " (" + sym + ")",
            marker_color=CAPEX_COLORS.get(sym, "#9ca3af"),
            hovertemplate="<b>" + sym + "</b><br>%{x}<br>CapEx: $%{y:.1f}B<extra></extra>",
        ))
    fig_capex.update_layout(
        barmode="group", height=380, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=40, l=50, r=20),
        yaxis=dict(title="CapEx (מיליארדי $)", gridcolor="rgba(255,255,255,0.08)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                   categoryorder="array", categoryarray=q_axis),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    with st.container(border=True):
        st.plotly_chart(fig_capex, use_container_width=True)

    # --- סה"כ מצרפי ---
    combined = pd.concat(capex_q.values(), axis=1).dropna()
    if len(combined) >= 2:
        total = combined.sum(axis=1)
        growth = float(total.iloc[-1]) / float(total.iloc[0]) * 100 - 100
        g_color = "#22c55e" if growth >= 0 else "#ef4444"
        st.markdown(
            "<div dir='rtl' style='text-align:right; font-weight:700; margin:4px 0 12px 0;'>"
            "סה\"כ CapEx מצרפי ברבעון האחרון (רבעונים חופפים בלבד): "
            "<span style='color:#22d3ee;'>$" + str(round(float(total.iloc[-1]), 1)) + "B</span>"
            " · צמיחה מתחילת החלון: <span style='color:" + g_color + ";'>"
            + ("+" if growth >= 0 else "") + str(round(growth, 1)) + "%</span></div>",
            unsafe_allow_html=True,
        )

    # --- כפתור ניתוח מגמה רבעונית ---
    capex_trend_key = "capex_trend_" + datetime.now(timezone.utc).strftime("%Y-%W")
    if st.button("📊 הסבר את תחזית ה-CapEx", key="capex_trend_btn"):
        lines = []
        for sym, s in capex_q.items():
            vals = ", ".join(str(round(float(v), 1)) for v in s.values[-4:])
            lines.append(sym + ": " + vals)
        with st.spinner("מבקש ניתוח מ-Gemini..."):
            text, sources = gemini_capex_trend(" | ".join(lines))
        st.session_state[capex_trend_key] = {"text": text, "sources": sources}

    saved_trend = st.session_state.get(capex_trend_key)
    if saved_trend and saved_trend.get("text"):
        st.markdown("<div dir='rtl' style='text-align:right;'>" + saved_trend["text"] + "</div>",
                    unsafe_allow_html=True)
        if saved_trend.get("sources"):
            with st.expander("מקורות"):
                for title, uri in saved_trend["sources"]:
                    st.markdown("• [" + (title or uri) + "](" + uri + ")")

    # ==================================================
    # תחזית שנתית מול שנים קודמות — טאב לכל חברה + טאב מצטבר
    # ==================================================
    st.markdown(section_header("📅 CapEx שנתי — בפועל מול התפתחות התחזית", "#f59e0b"),
                unsafe_allow_html=True)
    st.caption("עמודות כחולות-ירקרקות = CapEx בפועל בשנים שהסתיימו (לפי השנה הפיסקלית של כל חברה). "
               "עמודות כתומות = עדכוני התחזית לשנה הנוכחית, משמאל לימין לפי סדר העדכונים — "
               "כך רואים אם התחזית מטפסת או נחתכת במהלך השנה. "
               "הטאב האחרון (מצטבר) מציג את סך כל החברות יחד. "
               "התחזיות מוזנות ידנית (CAPEX_GUIDANCE בקוד); השתמש בכפתור למטה כדי למצוא את המספרים העדכניים.")

    # שורת טאבים אחת: טאב לכל חברה + טאב "מצטבר" בסוף
    tab_labels = [CAPEX_COMPANIES[sym] + " (" + sym + ")" for sym in CAPEX_COMPANIES]
    tab_labels.append("📊 מצטבר — כולן יחד")
    all_tabs = st.tabs(tab_labels)
    company_tabs = all_tabs[:-1]   # טאב לכל חברה
    stacked_tab = all_tabs[-1]     # הטאב המצטבר האחרון

    for tab, sym in zip(company_tabs, CAPEX_COMPANIES):
        with tab:
            annual = get_capex_annual(sym)
            guid = CAPEX_GUIDANCE.get(sym, {})
            guid_updates = [(lbl, v) for lbl, v in guid.get("updates", []) if v is not None]
            year_label = guid.get("year_label", "השנה הנוכחית")

            if annual is None and len(guid_updates) == 0:
                st.caption("אין נתונים זמינים לחברה זו כרגע")
                continue

            fig_a = go.Figure()

            # עמודות בפועל: שנים פיסקליות שהסתיימו
            if annual is not None:
                a_labels = ["FY" + str(d.year) for d in annual.index]
                a_values = [float(v) for v in annual.values]
                fig_a.add_trace(go.Bar(
                    x=a_labels, y=a_values, name="בפועל",
                    marker_color="#22d3ee",
                    text=["$" + str(round(v, 1)) + "B" for v in a_values],
                    textposition="outside", textfont=dict(size=12, color="#e5e7eb"),
                    hovertemplate="<b>%{x}</b><br>בפועל: $%{y:.1f}B<extra></extra>",
                ))

            # עמודות תחזית: התפתחות העדכונים לשנה הנוכחית
            if len(guid_updates) > 0:
                g_labels = [lbl for lbl, v in guid_updates]
                g_values = [float(v) for lbl, v in guid_updates]
                fig_a.add_trace(go.Bar(
                    x=g_labels, y=g_values, name="תחזית " + year_label,
                    marker=dict(color="rgba(245,158,11,0.85)",
                                line=dict(color="#f59e0b", width=1.5)),
                    text=["$" + str(round(v, 1)) + "B" for v in g_values],
                    textposition="outside", textfont=dict(size=12, color="#fcd34d"),
                    hovertemplate="<b>%{x}</b><br>תחזית: $%{y:.1f}B<extra></extra>",
                ))
                # חץ מגמה בין העדכון הראשון לאחרון
                if len(g_values) >= 2:
                    diff = g_values[-1] - g_values[0]
                    d_color = "#22c55e" if diff >= 0 else "#ef4444"
                    d_txt = ("התחזית עלתה ב-" if diff >= 0 else "התחזית ירדה ב-") + \
                            "$" + str(round(abs(diff), 1)) + "B מאז העדכון הראשון"
                    st.markdown(
                        "<div dir='rtl' style='text-align:right; color:" + d_color +
                        "; font-weight:700;'>" + ("📈 " if diff >= 0 else "📉 ") + d_txt + "</div>",
                        unsafe_allow_html=True,
                    )
            else:
                if DEV_MODE:
                    st.markdown(
                        "<div dir='rtl' style='text-align:right; color:#9ca3af; font-size:13px;'>"
                        "⚠️ טרם הוזנו עדכוני תחזית ל-" + year_label +
                        " — עדכן את CAPEX_GUIDANCE בקוד.</div>",
                        unsafe_allow_html=True,
                    )

            fig_a.update_layout(
                barmode="group", height=340, template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=30, b=40, l=50, r=20),
                yaxis=dict(title="CapEx (מיליארדי $)",
                           gridcolor="rgba(255,255,255,0.08)"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1),
                showlegend=True,
            )
            st.plotly_chart(fig_a, use_container_width=True)
            if guid.get("year_label"):
                st.caption("שנה פיסקלית נוכחית: " + year_label)

    # ---------- הטאב המצטבר: סך CapEx שנתי של כל החברות יחד ----------
    with stacked_tab:
        st.caption("עמודות מוערמות לכל שנה: כל צבע = חברה. "
                   "שים לב — השנה הפיסקלית של מיקרוסופט מסתיימת ביוני, של השאר בדצמבר, "
                   "אז זה קירוב לפי שנת הדיווח. "
                   "העמודה האחרונה (במסגרת כתומה) = סכום התחזית העדכנית של כל חברה לשנה הבאה. "
                   "מעל כל עמודה: הסכום ואחוז הצמיחה מהעמודה הקודמת.")

        annual_by_company = {}
        for sym in CAPEX_COMPANIES:
            a = get_capex_annual(sym)
            if a is not None:
                annual_by_company[sym] = {d.year: float(v) for d, v in zip(a.index, a.values)}

        if len(annual_by_company) == 0:
            st.caption("אין נתונים שנתיים זמינים כרגע")
        else:
            all_years = set()
            for ymap in annual_by_company.values():
                all_years.update(ymap.keys())
            years_sorted = sorted(all_years)
            year_labels = [str(y) for y in years_sorted]

            # --- התחזית המצטברת: העדכון האחרון של כל חברה שהוזן ---
            # לכל חברה לוקחים את הערך האחרון (לא None) מרשימת העדכונים.
            latest_guidance = {}   # sym -> ערך התחזית העדכני
            for sym in CAPEX_COMPANIES:
                guid = CAPEX_GUIDANCE.get(sym, {})
                vals = [v for lbl, v in guid.get("updates", []) if v is not None]
                if vals:
                    latest_guidance[sym] = float(vals[-1])
            has_forecast = len(latest_guidance) > 0
            forecast_total = sum(latest_guidance.values()) if has_forecast else 0.0
            # תווית עמודת התחזית (אם חלק מהחברות חסרות — מציינים)
            n_have = len(latest_guidance)
            n_total = len(CAPEX_COMPANIES)
            forecast_label = "תחזית לשנה הבאה"
            if 0 < n_have < n_total:
                forecast_label = "תחזית (" + str(n_have) + "/" + str(n_total) + " חברות)"

            # ציר ה-X: השנים בפועל + עמודת תחזית מצרפית בסוף (אם קיימת)
            x_axis = list(year_labels)
            if has_forecast:
                x_axis = x_axis + [forecast_label]

            fig_stack = go.Figure()
            for sym in CAPEX_COMPANIES:
                if sym not in annual_by_company:
                    continue
                ymap = annual_by_company[sym]
                y_vals = [ymap.get(y, 0.0) for y in years_sorted]
                # ערך התחזית של החברה בעמודה האחרונה (0 אם לא הוזנה)
                if has_forecast:
                    y_vals = y_vals + [latest_guidance.get(sym, 0.0)]
                fig_stack.add_trace(go.Bar(
                    x=x_axis, y=y_vals,
                    name=CAPEX_COMPANIES[sym] + " (" + sym + ")",
                    marker_color=CAPEX_COLORS.get(sym, "#9ca3af"),
                    hovertemplate="<b>" + sym + "</b><br>%{x}<br>$%{y:.1f}B<extra></extra>",
                ))

            # סכומים לכל עמודה — כולל עמודת התחזית בסוף
            totals = []
            for y in years_sorted:
                t = sum(annual_by_company[sym].get(y, 0.0) for sym in annual_by_company)
                totals.append(t)
            if has_forecast:
                totals.append(forecast_total)

            # תוויות מעל כל עמודה: סכום + אחוז שינוי מהעמודה הקודמת
            growth_texts = []
            for i, t in enumerate(totals):
                if i == 0 or totals[i - 1] == 0:
                    growth_texts.append("$" + str(round(t, 1)) + "B")
                else:
                    g = t / totals[i - 1] * 100 - 100
                    sign = "+" if g >= 0 else ""
                    growth_texts.append("$" + str(round(t, 1)) + "B<br>(" + sign + str(round(g, 1)) + "%)")

            # מרווח מעל העמודה הגבוהה ביותר, כדי שהתווית הדו-שורתית (סכום + %)
            # לא תיחתך מלמעלה — במיוחד עמודת התחזית, שבדרך כלל הגבוהה ביותר.
            max_total = max(totals) if totals else 1.0
            y_top = max_total * 1.28

            fig_stack.add_trace(go.Scatter(
                x=x_axis, y=[t * 1.05 for t in totals],
                mode="text", text=growth_texts,
                textposition="top center", textfont=dict(size=13, color="#e5e7eb"),
                showlegend=False, hoverinfo="skip",
            ))

            # מסגרת כתומה סביב עמודת התחזית — כדי שתובחן מהשנים בפועל
            if has_forecast:
                fig_stack.add_shape(
                    type="rect", xref="x", yref="paper",
                    x0=len(year_labels) - 0.5, x1=len(year_labels) + 0.5,
                    y0=0, y1=1,
                    line=dict(color="#f59e0b", width=2, dash="dot"),
                    fillcolor="rgba(245,158,11,0.05)", layer="below",
                )

            fig_stack.update_layout(
                barmode="stack", height=480, template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=30, b=40, l=50, r=20),
                yaxis=dict(title="CapEx מצרפי (מיליארדי $)",
                           gridcolor="rgba(255,255,255,0.08)",
                           range=[0, y_top]),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.08,
                            xanchor="right", x=1),
            )
            st.plotly_chart(fig_stack, use_container_width=True)

            # שורת סיכום: צמיחת ה-CapEx בפועל על פני התקופה
            actual_totals = totals[:-1] if has_forecast else totals
            if len(actual_totals) >= 2 and actual_totals[0] != 0:
                total_growth = actual_totals[-1] / actual_totals[0] * 100 - 100
                tg_color = "#22c55e" if total_growth >= 0 else "#ef4444"
                st.markdown(
                    "<div dir='rtl' style='text-align:right; font-weight:700; margin-top:6px;'>"
                    "סך ה-CapEx המצרפי בפועל גדל מ-<span style='color:#22d3ee;'>$"
                    + str(round(actual_totals[0], 1)) + "B</span> ל-<span style='color:#22d3ee;'>$"
                    + str(round(actual_totals[-1], 1)) + "B</span> — צמיחה של <span style='color:"
                    + tg_color + ";'>" + ("+" if total_growth >= 0 else "")
                    + str(round(total_growth, 1)) + "%</span> על פני התקופה</div>",
                    unsafe_allow_html=True,
                )

            # שורת סיכום נוספת: התחזית המצרפית מול השנה האחרונה בפועל
            if has_forecast and len(actual_totals) >= 1 and actual_totals[-1] != 0:
                fc_growth = forecast_total / actual_totals[-1] * 100 - 100
                fc_color = "#22c55e" if fc_growth >= 0 else "#ef4444"
                miss_note = ""
                if n_have < n_total:
                    miss_note = " (חלקי — טרם הוזנו תחזיות לכל החברות)"
                st.markdown(
                    "<div dir='rtl' style='text-align:right; font-weight:700; margin-top:4px;'>"
                    "התחזית המצרפית לשנה הבאה: <span style='color:#f59e0b;'>$"
                    + str(round(forecast_total, 1)) + "B</span> — "
                    "צמיחה צפויה של <span style='color:" + fc_color + ";'>"
                    + ("+" if fc_growth >= 0 else "") + str(round(fc_growth, 1))
                    + "%</span> מעל השנה האחרונה בפועל" + miss_note + "</div>",
                    unsafe_allow_html=True,
                )
            elif not has_forecast:
                st.caption("💡 עמודת תחזית מצרפית תופיע כאן אחרי שתזין ערכי תחזית ב-CAPEX_GUIDANCE.")

    # ==================================================
    # טבלה מסכמת: התפתחות התחזיות מול השנה הקודמת בפועל
    # ==================================================
    st.markdown(section_header("📋 טבלת סיכום — התחזית האחרונה מול הקודמת ומול בפועל", "#f59e0b"),
                unsafe_allow_html=True)

    # בונים שורה לכל חברה שיש לה לפחות תחזית אחת שהוזנה
    guid_rows = []
    for sym in CAPEX_COMPANIES:
        guid = CAPEX_GUIDANCE.get(sym, {})
        vals = [v for lbl, v in guid.get("updates", []) if v is not None]
        if not vals:
            continue  # אין תחזית שהוזנה לחברה זו — לא נציג שורה

        last = float(vals[-1])
        prev = float(vals[-2]) if len(vals) >= 2 else None

        # שינוי התחזית האחרונה מול הקודמת
        chg_prev = None
        if prev is not None and prev != 0:
            chg_prev = last / prev * 100 - 100

        # ה-CapEx בפועל של השנה הפיסקלית האחרונה שהסתיימה
        annual = get_capex_annual(sym)
        actual_prev = None
        if annual is not None and len(annual) > 0:
            actual_prev = float(annual.values[-1])

        # שינוי התחזית מול השנה הקודמת בפועל
        chg_actual = None
        if actual_prev is not None and actual_prev != 0:
            chg_actual = last / actual_prev * 100 - 100

        guid_rows.append({
            "name": CAPEX_COMPANIES[sym] + " (" + sym + ")",
            "last": last,
            "prev": prev,
            "chg_prev": chg_prev,
            "actual_prev": actual_prev,
            "chg_actual": chg_actual,
        })

    if len(guid_rows) == 0:
        st.caption("טרם הוזנו תחזיות. הזן ערכים ב-CAPEX_GUIDANCE כדי לראות את הטבלה.")
    else:
        st.markdown(capex_guidance_table_html(guid_rows), unsafe_allow_html=True)
        st.caption("«תחזית אחרונה» = העדכון האחרון שהוזן · «תחזית קודמת» = העדכון שלפניו · "
                   "«שינוי בתחזית» = כמה השתנתה התחזית בין העדכונים · "
                   "«תחזית מול בפועל» = כמה התחזית הנוכחית גבוהה/נמוכה מ-CapEx השנה הקודמת שהסתיימה. "
                   "«—» מציין שאין עדיין נתון (למשל רק עדכון תחזית אחד).")

    # --- סיכום עדכוני תחזית — גלוי לכולם ---
    if len(guid_rows) > 0:
        _guid_sum_key = "capex_guid_summary_" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if st.button("📊 סכם את עדכוני תחזית ה-CapEx", key="capex_guid_summary_btn"):
            _guid_lines = []
            for sym in CAPEX_COMPANIES:
                guid = CAPEX_GUIDANCE.get(sym, {})
                updates = [(lbl, v) for lbl, v in guid.get("updates", []) if v is not None]
                if updates:
                    parts = [lbl + ": $" + str(v) + "B" for lbl, v in updates]
                    _guid_lines.append(CAPEX_COMPANIES[sym] + " — " + " → ".join(parts))
            with st.spinner("מסכם עדכוני תחזית עם Gemini..."):
                _gs_text, _gs_sources = gemini_summarize_capex_guidance("\n".join(_guid_lines))
            st.session_state[_guid_sum_key] = {"text": _gs_text, "sources": _gs_sources}

        _gs_saved = st.session_state.get(_guid_sum_key)
        if _gs_saved and _gs_saved.get("text"):
            st.markdown("<div dir='rtl' style='text-align:right;'>" + _gs_saved["text"] + "</div>",
                        unsafe_allow_html=True)
            if _gs_saved.get("sources"):
                with st.expander("מקורות"):
                    for _t, _u in _gs_saved["sources"]:
                        st.markdown("• [" + (_t or _u) + "](" + _u + ")")

    # --- כפתור חיפוש תחזיות עדכניות — מצב מפתח בלבד ---
    if DEV_MODE:
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        capex_guid_key = "capex_guid_" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if st.button("🔎 חפש את תחזיות ה-CapEx העדכניות (לעדכון ידני של המילון)",
                     key="capex_guid_btn"):
            with st.spinner("מחפש תחזיות עדכניות ברשת..."):
                text, sources = gemini_capex_guidance()
            st.session_state[capex_guid_key] = {"text": text, "sources": sources}

        saved_guid = st.session_state.get(capex_guid_key)
        if saved_guid and saved_guid.get("text"):
            st.markdown("<div dir='rtl' style='text-align:right;'>" + saved_guid["text"] + "</div>",
                        unsafe_allow_html=True)
            if saved_guid.get("sources"):
                with st.expander("מקורות"):
                    for title, uri in saved_guid["sources"]:
                        st.markdown("• [" + (title or uri) + "](" + uri + ")")
            st.caption("💡 קח את המספרים מכאן, אמת מול המקורות, והזן אותם ב-CAPEX_GUIDANCE שבראש הקובץ.")

# ======================================================
# אזור 6 — דוחות כספיים וסנטימנט עונת הדוחות
# ======================================================
CORE_COMPANIES = [
    "ASML", "AMAT", "LRCX", "KLAC", "NVDA", "AMD", "TSM", "INTC", "MU",
    "TXN", "ADI", "AVGO", "QCOM", "MRVL", "ARM",
    "TSEM", "NVMI", "CAMT", "MBLY",
    "MSFT", "META", "GOOGL", "AMZN", "ORCL",
    "005930.KS", "000660.KS",
]
ISRAELI_TICKERS = {"TSEM", "NVMI", "CAMT", "MBLY"}

st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(6, 6, "📋", "דוחות כספיים — ניתוח עונת הדוחות", "#f59e0b",
               subtitle="ניתוח דוחות ושיחות ועידה עם AI · סנטימנט מצטבר לפי תחום",
               period_dependent=False)

_z6_sent_data = load_sentiment()


# --- לוח שנה של דוחות ---
st.markdown(section_header("📅 לוח דוחות", "#3b82f6"), unsafe_allow_html=True)

# ניווט חודשי — שמור ב-session_state
_today_nav = datetime.now(timezone.utc)
if "z6_cal_year" not in st.session_state:
    st.session_state["z6_cal_year"] = _today_nav.year
    st.session_state["z6_cal_month"] = _today_nav.month

_month_names_he = ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                   "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
_cy = st.session_state["z6_cal_year"]
_cm = st.session_state["z6_cal_month"]

_nav_prev, _nav_title, _nav_next = st.columns([1, 3, 1])
with _nav_prev:
    if st.button("◄ חודש קודם", key="z6_prev_month", use_container_width=True):
        _nm, _ny = (_cm - 1, _cy) if _cm > 1 else (12, _cy - 1)
        st.session_state["z6_cal_month"] = _nm
        st.session_state["z6_cal_year"] = _ny
        st.rerun()
with _nav_title:
    st.markdown(
        "<div style='text-align:center; font-size:18px; font-weight:700; padding:6px;'>"
        + _month_names_he[_cm] + " " + str(_cy) + "</div>",
        unsafe_allow_html=True,
    )
with _nav_next:
    if st.button("חודש הבא ►", key="z6_next_month", use_container_width=True):
        _nm, _ny = (_cm + 1, _cy) if _cm < 12 else (1, _cy + 1)
        st.session_state["z6_cal_month"] = _nm
        st.session_state["z6_cal_year"] = _ny
        st.rerun()

# טעינת נתוני הלוח (cached, ±120 יום)
with st.spinner("טוען תאריכי דוחות..."):
    _z6_all_entries = get_earnings_calendar(tuple(CORE_COMPANIES))

# המרה ל-dict {date_str: [entries]}
_z6_cal_dict = {}
for _e in _z6_all_entries:
    _z6_cal_dict.setdefault(str(_e["date"]), []).append(_e)

# אוסף תחזיות לחברות עתידיות בחודש המוצג
_z6_fwd_est: dict[str, dict] = {}
for _fe_date, _fe_entries in _z6_cal_dict.items():
    for _fe in _fe_entries:
        if _fe["is_future"] and _fe["symbol"] not in _z6_fwd_est:
            _fe_data = get_forward_estimates(_fe["symbol"])
            if _fe_data:
                _z6_fwd_est[_fe["symbol"]] = _fe_data

# בניית גריד הלוח
import calendar as _cal_mod
_cal_mod.setfirstweekday(6)   # יום ראשון = תחילת שבוע
_weeks = _cal_mod.monthcalendar(_cy, _cm)
_today_date = datetime.now(timezone.utc).date()

_day_headers_he = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"]
_hdr_html = "<tr>" + "".join(
    "<th style='text-align:center; padding:8px 4px; font-size:13px; font-weight:600; "
    "color:#e5e7eb; background:#1e2533; border-bottom:2px solid #374151; width:14.28%;'>" + _h + "</th>"
    for _h in _day_headers_he
) + "</tr>"

_status_bg_fg = {
    "future":     ("rgba(37,99,235,0.30)",  "#bfdbfe"),
    "analyzed":   ("rgba(22,101,52,0.45)",  "#bbf7d0"),
    "unanalyzed": ("rgba(161,98,7,0.45)",   "#fde68a"),
}
_status_border = {
    "future":     "1px solid rgba(96,165,250,0.5)",
    "analyzed":   "1px solid rgba(74,222,128,0.5)",
    "unanalyzed": "1px solid rgba(253,211,77,0.5)",
}

_rows_html = ""
for _week in _weeks:
    _row = "<tr>"
    for _wday in _week:
        if _wday == 0:
            _row += "<td style='padding:3px; width:14.28%; height:80px; background:#0f1117; border-radius:6px;'></td>"
            continue
        from datetime import date as _date_cls
        _d = _date_cls(_cy, _cm, _wday)
        _dstr = str(_d)
        _is_today = (_d == _today_date)
        _cell_bg = "background:#1a2035;" if _is_today else "background:#141824;"
        _border = "border:2px solid #60a5fa; border-radius:8px;" if _is_today else "border:1px solid #2d3748; border-radius:8px;"
        _num_color = "#60a5fa" if _is_today else "#9ca3af"
        _num_size = "14px" if _is_today else "12px"
        _num_weight = "800" if _is_today else "500"
        _cell = (
            "<td style='padding:6px; width:14.28%; vertical-align:top; height:80px; "
            + _cell_bg + _border + "'>"
            "<div style='font-size:" + _num_size + "; color:" + _num_color + "; "
            "font-weight:" + _num_weight + "; margin-bottom:4px; line-height:1;'>" + str(_wday) + "</div>"
        )
        for _entry in _z6_cal_dict.get(_dstr, []):
            _sym = _entry["symbol"]
            _has_report = not _entry["is_future"]
            _status = get_symbol_cal_status(_sym, _d, _has_report, _z6_sent_data)
            _bg, _fg = _status_bg_fg[_status]
            _bd = _status_border[_status]
            if _status == "future":
                _days_left = (_d - _today_date).days
                _days_txt = (
                    "היום" if _days_left == 0
                    else ("מחר" if _days_left == 1
                    else f"{_days_left} ימים")
                )
                _fwd = _z6_fwd_est.get(_sym, {})
                _tip_lines = [f"📅 {_days_txt}"]
                _eps_e = _fwd.get("eps_est")
                if _eps_e is not None:
                    _tip_lines.append(f"EPS צפי: ${_eps_e:.2f}")
                _rev_e = _fwd.get("revenue_est_b")
                if _rev_e is not None:
                    _tip_lines.append(f"הכנסות: ${_rev_e:.1f}B")
                _grw = _fwd.get("revenue_growth_pct")
                if _grw is not None:
                    _grw_sign = "+" if _grw > 0 else ""
                    _tip_lines.append(f"צמיחה: {_grw_sign}{_grw:.1f}%")
                _tip_html = "<br>".join(_tip_lines)
                _cell += (
                    "<div class='chip-future-wrap'>"
                    "<div class='chip-future' style='background:" + _bg + "; color:" + _fg + "; border:" + _bd + "; "
                    "font-size:11px; font-weight:700; padding:3px 6px; "
                    "border-radius:5px; margin:2px 0; white-space:nowrap; "
                    "text-align:center; position:relative; cursor:default;'>"
                    + _sym +
                    "<div class='chip-tip'>" + _tip_html + "</div>"
                    "</div>"
                    "</div>"
                )
            else:
                _cell += (
                    "<div style='background:" + _bg + "; color:" + _fg + "; border:" + _bd + "; "
                    "font-size:11px; font-weight:700; padding:3px 6px; "
                    "border-radius:5px; margin:2px 0; white-space:nowrap; "
                    "text-align:center;'>"
                    + _sym + "</div>"
                )
        _cell += "</td>"
        _row += _cell
    _rows_html += _row + "</tr>"

st.markdown(
    "<style>"
    ".chip-future-wrap { position: relative; display: block; }"
    ".chip-future { position: relative; cursor: default; }"
    ".chip-tip {"
    "  display: none;"
    "  position: absolute;"
    "  top: calc(100% + 4px);"
    "  left: 50%;"
    "  transform: translateX(-50%);"
    "  background: #1e2533;"
    "  color: #e5e7eb;"
    "  font-size: 11px;"
    "  font-weight: 400;"
    "  line-height: 1.7;"
    "  padding: 6px 10px;"
    "  border-radius: 6px;"
    "  border: 1px solid #374151;"
    "  white-space: nowrap;"
    "  z-index: 9999;"
    "  text-align: right;"
    "  direction: rtl;"
    "  pointer-events: none;"
    "  box-shadow: 0 4px 12px rgba(0,0,0,0.5);"
    "}"
    ".chip-future:hover .chip-tip { display: block; }"
    "</style>"
    "<div style='overflow:visible; margin-top:8px;'>"
    "<table style='width:100%; border-collapse:separate; border-spacing:3px; table-layout:fixed; overflow:visible;'>"
    + _hdr_html + _rows_html +
    "</table>"
    "<div dir='rtl' style='font-size:12px; color:#9ca3af; margin-top:10px; display:flex; gap:12px; flex-wrap:wrap;'>"
    "<span style='background:rgba(37,99,235,0.30); color:#bfdbfe; padding:2px 8px; border-radius:4px; border:1px solid rgba(96,165,250,0.5);'>🔵 עתידי</span>"
    "<span style='background:rgba(22,101,52,0.45); color:#bbf7d0; padding:2px 8px; border-radius:4px; border:1px solid rgba(74,222,128,0.5);'>🟢 נותח ✓</span>"
    "<span style='background:rgba(161,98,7,0.45); color:#fde68a; padding:2px 8px; border-radius:4px; border:1px solid rgba(253,211,77,0.5);'>🟡 ממתין לניתוח</span>"
    "<span>🇮🇱 ישראלית</span>"
    "<span style='color:#60a5fa; font-weight:700;'>■ היום</span>"
    "</div></div>",
    unsafe_allow_html=True,
)

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# ======================================================
# חברות ישראליות — מעקב צמוד
# ======================================================
st.markdown(section_header("🇮🇱 חברות ישראליות — מעקב צמוד", "#3b82f6"), unsafe_allow_html=True)
st.caption("מעקב קבוע אחר ארבע החברות הישראליות בסקטור — דוח אחרון, דוח הבא, וניתוח השפעת עונת הדוחות.")

_il_season = latest_season_with_data(_z6_sent_data)

# כל הניתוחים השמורים לעונה — יועברו לפונקציית ה-Gemini
_il_season_analyzed = {
    sym: _z6_sent_data[sym][_il_season]
    for sym in _z6_sent_data
    if _il_season in _z6_sent_data.get(sym, {})
}

# מיפוי: חברה → דוח אחרון (is_future=False) ודוח הבא (is_future=True)
_il_last = {}
_il_next = {}
for _e in _z6_all_entries:
    _esym = _e["symbol"]
    if _esym not in ISRAELI_TICKERS:
        continue
    _ed = _e["date"]
    if not _e["is_future"]:
        if _esym not in _il_last or _ed > _il_last[_esym]["date"]:
            _il_last[_esym] = _e
    else:
        if _esym not in _il_next or _ed < _il_next[_esym]["date"]:
            _il_next[_esym] = _e

_il_descriptions = {
    "TSEM": "Tower Semi · Foundry אנלוגי",
    "NVMI": "Nova · Process Control",
    "CAMT": "Camtek · Inspection",
    "MBLY": "Mobileye · Automotive AI",
}

_il_display = sorted(ISRAELI_TICKERS - {"MBLY"})
_il_cols = st.columns(len(_il_display))
for _il_i, _il_sym in enumerate(_il_display):
    with _il_cols[_il_i]:
        with st.container(border=True):
            _il_rec = get_record(_z6_sent_data, _il_sym, _il_season)
            _il_status_dot = "🟢" if (_il_rec and _il_rec.get("sentiment_score") is not None) else "🟡"
            st.markdown(
                "<div dir='rtl' style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>"
                "<span><span style='font-size:17px; font-weight:800;'>🇮🇱 " + _il_sym + "</span>"
                " <span style='font-size:12px; color:#9ca3af;'>" + _il_descriptions.get(_il_sym, "") + "</span></span>"
                "<span>" + _il_status_dot + "</span></div>",
                unsafe_allow_html=True,
            )

            # דוח אחרון
            _il_le = _il_last.get(_il_sym)
            if _il_le:
                _il_eps_a = _il_le.get("eps_actual")
                _il_eps_e = _il_le.get("eps_est")
                _il_surp = _il_le.get("surprise")
                _il_eps_html = ""
                if _il_eps_a is not None:
                    _il_eps_html = " · EPS: $" + f"{_il_eps_a:.2f}"
                    if _il_eps_e is not None:
                        _il_eps_html += " (צפוי: $" + f"{_il_eps_e:.2f}" + ")"
                _il_surp_html = ""
                if _il_surp is not None:
                    _il_sc = "#22c55e" if _il_surp > 0 else "#ef4444"
                    _il_ss = "+" if _il_surp > 0 else ""
                    _il_surp_html = (" <span style='color:" + _il_sc + ";'>(" +
                                     _il_ss + f"{_il_surp:.1f}%" + ")</span>")
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; margin:3px 0;'>"
                    "📋 <b>דוח אחרון:</b> " + str(_il_le["date"]) + _il_eps_html + _il_surp_html + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#6b7280; margin:3px 0;'>"
                    "📋 דוח אחרון: לא ידוע בחלון הנוכחי</div>",
                    unsafe_allow_html=True,
                )

            # דוח הבא
            _il_ne = _il_next.get(_il_sym)
            if _il_ne:
                _il_days = (_il_ne["date"] - _today_date).days
                _il_days_txt = " (" + str(_il_days) + " ימים)" if _il_days >= 0 else ""
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; margin:3px 0;'>"
                    "📅 <b>דוח הבא:</b> " + str(_il_ne["date"]) + _il_days_txt + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#6b7280; margin:3px 0;'>"
                    "📅 דוח הבא: לא ידוע בחלון הנוכחי</div>",
                    unsafe_allow_html=True,
                )

            # סנטימנט שמור
            if _il_rec and _il_rec.get("sentiment_score") is not None:
                _il_score = float(_il_rec["sentiment_score"])
                _il_pct = int(round(_il_score * 100))
                _il_sign = "+" if _il_pct >= 0 else ""
                _il_emoji = "🟢" if _il_score >= 0.15 else ("🔴" if _il_score <= -0.15 else "⚪")
                _il_col_c = "#22c55e" if _il_score >= 0.15 else ("#ef4444" if _il_score <= -0.15 else "#9ca3af")
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; margin:3px 0 10px;'>"
                    "🧠 <b>סנטימנט " + _il_season + ":</b> " + _il_emoji +
                    " <span style='color:" + _il_col_c + "; font-weight:700;'>" +
                    _il_sign + str(_il_pct) + "%</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#6b7280; margin:3px 0 10px;'>"
                    "🧠 " + _il_season + ": טרם נותח</div>",
                    unsafe_allow_html=True,
                )

            # כפתור ניתוח השפעה
            _il_impact_key = "il_impact_" + _il_sym + "_" + _il_season
            _il_impact_res = st.session_state.get(_il_impact_key)
            if st.button("🔍 נתח השפעת עונת הדוחות", key="il_impact_btn_" + _il_sym,
                         use_container_width=True):
                _il_ctx = []
                for _s, _r in _il_season_analyzed.items():
                    _sc = _r.get("sentiment_score", 0) or 0
                    _sm = _r.get("summary", "")
                    _gd = _r.get("guidance_direction", "")
                    _sc_pct = ("+" if _sc >= 0 else "") + str(int(round(_sc * 100))) + "%"
                    _il_ctx.append(
                        "• " + _s + " (סנטימנט: " + _sc_pct +
                        (", הנחיה: " + _gd if _gd and _gd != "none" else "") +
                        "): " + _sm
                    )
                    for _sig in _r.get("domain_signals", []):
                        _il_ctx.append(
                            "  ↳ " + _sig.get("domain", "") + ": " +
                            _sig.get("direction", "") + " — " + _sig.get("note", "")
                        )
                _il_ctx_text = "\n".join(_il_ctx) if _il_ctx else "אין ניתוחים שמורים לעונה זו עדיין."
                with st.spinner("מנתח השפעת הדוחות על " + _il_sym + "..."):
                    _il_txt, _il_srcs = gemini_israeli_impact(_il_sym, _il_season, _il_ctx_text)
                st.session_state[_il_impact_key] = {"text": _il_txt, "sources": _il_srcs}
                st.rerun()

            if _il_impact_res:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#d1d5db; line-height:1.6; "
                    "background:rgba(255,255,255,0.04); border-radius:6px; padding:8px 10px; margin-top:4px;'>"
                    + (_il_impact_res.get("text") or "") + "</div>",
                    unsafe_allow_html=True,
                )
                if _il_impact_res.get("sources"):
                    with st.expander("מקורות"):
                        for _t, _u in _il_impact_res["sources"]:
                            st.markdown("• [" + (_t or _u) + "](" + _u + ")")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# --- ניתוח השפעת עונה לחברות נוספות ---
with st.expander("🔍 ניתוח השפעת עונת הדוחות — חברות נוספות"):
    st.caption("בחרי חברה לניתוח ההשפעה של הדוחות שפורסמו עד כה בעונה " + _il_season + ".")
    _ext_companies = [c for c in CORE_COMPANIES if c not in ISRAELI_TICKERS]
    _ext_chosen = st.selectbox("חברה:", _ext_companies, key="il_ext_sym")
    _ext_impact_key = "il_impact_" + _ext_chosen + "_" + _il_season
    _ext_impact_res = st.session_state.get(_ext_impact_key)

    if st.button("🔍 נתח השפעת עונת הדוחות", key="il_ext_impact_btn", use_container_width=True):
        _ext_ctx = []
        for _s, _r in _il_season_analyzed.items():
            _sc = _r.get("sentiment_score", 0) or 0
            _sm = _r.get("summary", "")
            _gd = _r.get("guidance_direction", "")
            _sc_pct = ("+" if _sc >= 0 else "") + str(int(round(_sc * 100))) + "%"
            _ext_ctx.append(
                "• " + _s + " (סנטימנט: " + _sc_pct +
                (", הנחיה: " + _gd if _gd and _gd != "none" else "") +
                "): " + _sm
            )
            for _sig in _r.get("domain_signals", []):
                _ext_ctx.append(
                    "  ↳ " + _sig.get("domain", "") + ": " +
                    _sig.get("direction", "") + " — " + _sig.get("note", "")
                )
        _ext_ctx_text = "\n".join(_ext_ctx) if _ext_ctx else "אין ניתוחים שמורים לעונה זו עדיין."
        with st.spinner("מנתח השפעת הדוחות על " + _ext_chosen + "..."):
            _ext_txt, _ext_srcs = gemini_israeli_impact(_ext_chosen, _il_season, _ext_ctx_text)
        st.session_state[_ext_impact_key] = {"text": _ext_txt, "sources": _ext_srcs}
        st.rerun()

    if _ext_impact_res:
        st.markdown(
            "<div dir='rtl' style='font-size:13px; color:#d1d5db; line-height:1.6; "
            "background:rgba(255,255,255,0.04); border-radius:6px; padding:8px 10px; margin-top:4px;'>"
            + (_ext_impact_res.get("text") or "") + "</div>",
            unsafe_allow_html=True,
        )
        if _ext_impact_res.get("sources"):
            with st.expander("מקורות"):
                for _t, _u in _ext_impact_res["sources"]:
                    st.markdown("• [" + (_t or _u) + "](" + _u + ")")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

st.markdown(section_header("🧠 ניתוח דוח ושיחת ועידה", "#f59e0b"), unsafe_allow_html=True)

_z6_chosen = st.selectbox("בחרי חברה לניתוח הדוח:", CORE_COMPANIES, key="z6_sym_select")

_z6_default_season = latest_season_with_data(_z6_sent_data)
if DEV_MODE:
    # בחירה חופשית — כולל עונות שטרם נותחו; לשימוש מפתח בלבד
    _now_z6 = datetime.now(timezone.utc)
    _q, _y = (_now_z6.month - 1) // 3 + 1, _now_z6.year
    _season_opts: list[str] = []
    for _ in range(4):
        _season_opts.append(f"{_y}Q{_q}")
        _q -= 1
        if _q == 0:
            _q, _y = 4, _y - 1
    _default_idx = _season_opts.index(_z6_default_season) if _z6_default_season in _season_opts else 0
    _z6_season: str = st.selectbox("עונה:", _season_opts, index=_default_idx, key="z6_season_select")
else:
    _z6_season = _z6_default_season

_z6_result_key = "earnings_result_" + _z6_chosen + "_" + _z6_season
_z6_saved_rec = get_record(_z6_sent_data, _z6_chosen, _z6_season)
_z6_pending = st.session_state.get(_z6_result_key)


def israeli_exposure_to_signals(domain_signals):
    """מצליב סיגנלים תחומיים של דוח עם חשיפות TSEM/NVMI/CAMT מ-TECH_GROUPS.
    מחזיר {sym: [(domain, direction, eff_exposure), ...]} — רק חברות עם התאמה."""
    ISRAELI_SYMS = {"TSEM", "NVMI", "CAMT"}
    signal_domains = {s.get("domain"): s.get("direction") for s in domain_signals if s.get("domain")}
    result: dict[str, list] = {}
    for axis in TECH_GROUPS.values():
        for domain_name, tiers in axis.items():
            if domain_name not in signal_domains:
                continue
            direction = signal_domains[domain_name]
            for tier_key, tier_mult in (("core", TIER_CORE), ("env", TIER_ENV)):
                for sym, exp in tiers.get(tier_key, {}).items():
                    if sym in ISRAELI_SYMS:
                        result.setdefault(sym, []).append((domain_name, direction, exp * tier_mult))
    for sym in result:
        result[sym].sort(key=lambda x: -x[2])
    return result


def _render_analysis_record(rec, label="", eps_surprise=None, stock_reaction=None):
    """מרנדר רשומת ניתוח (מה-JSON או מ-session_state)."""
    score = float(rec.get("sentiment_score") or 0)
    pct = int(round(score * 100))
    sign = "+" if pct >= 0 else ""
    emoji = "🟢" if score >= 0.15 else ("🔴" if score <= -0.15 else "⚪")
    col = "#22c55e" if score >= 0.15 else ("#ef4444" if score <= -0.15 else "#9ca3af")
    res_map = {"beat": "🟢 הכה ציפיות", "meet": "⚪ עמד בציפיות", "miss": "🔴 פספס ציפיות"}
    guid_map = {"raised": "📈 הועלתה", "maintained": "➡️ נשמרה", "lowered": "📉 הורדה", "none": "—"}
    res_txt = res_map.get(rec.get("results_vs_expectations", ""), "—")
    guid_txt = guid_map.get(rec.get("guidance_direction", ""), "—")
    report_date = rec.get("report_date", "—")
    summary = rec.get("summary", "")
    signals = rec.get("domain_signals", [])

    # שורת תגובת שוק (הפתעת EPS מוצגת ב-rev_row בלבד, כאן רק תגובת השוק)
    mkt_parts = []
    if stock_reaction is not None:
        try:
            rp = float(stock_reaction)
            rp_sign = "+" if rp >= 0 else ""
            rp_col = "#22c55e" if rp > 0 else ("#ef4444" if rp < 0 else "#9ca3af")
            mkt_parts.append(
                "<span>תגובת שוק: <b style='color:" + rp_col + ";'>" + rp_sign + f"{rp:.1f}%" + "</b></span>"
            )
        except (TypeError, ValueError):
            pass
    # אזהרה: הפתעה חיובית + שוק ירד
    alert_html = ""
    if eps_surprise is not None and stock_reaction is not None:
        try:
            if float(eps_surprise) > 0 and float(stock_reaction) < -1:
                alert_html = (
                    "<div dir='rtl' style='background:rgba(234,179,8,0.15); border:1px solid #ca8a04; "
                    "border-radius:6px; padding:5px 10px; font-size:12px; color:#fbbf24; margin-top:4px;'>"
                    "⚠️ הפתעה חיובית אך המניה ירדה — כדאי לבדוק את ההנחיה</div>"
                )
        except (TypeError, ValueError):
            pass

    mkt_row = ""
    if mkt_parts:
        mkt_row = (
            "<div dir='rtl' style='display:flex; gap:16px; margin:0 0 6px; flex-wrap:wrap; "
            "font-size:13px; background:rgba(30,37,51,0.6); padding:5px 10px; border-radius:6px;'>"
            + " · ".join(mkt_parts) + "</div>"
        )

    _gemini_tag = (
        "<span style='font-size:11px; color:#a78bfa; background:rgba(167,139,250,0.12); "
        "padding:1px 6px; border-radius:4px; border:1px solid rgba(167,139,250,0.3);'>"
        "🔮 מוערך (Gemini)</span>"
    )

    # --- שורת EPS + הכנסות מוערכות (מ-Gemini) — EPS ראשון, אחר כך הכנסות, תג אחד בסוף ---
    rev_row = ""
    _combined_parts: list[str] = []

    # חלק EPS — רק אם שני השדות קיימים ואינם null
    _eps_act = rec.get("eps_actual")
    _eps_est = rec.get("eps_estimate")
    if _eps_act is not None and _eps_est is not None:
        try:
            _ea_f = float(_eps_act)
            _ee_f = float(_eps_est)
            _eps_parts = [
                f"EPS: <b>${_ea_f:.2f}</b> בפועל",
                f"<span style='color:#9ca3af;'>${_ee_f:.2f} צפי</span>",
            ]
            if _ee_f != 0:
                _es = _ea_f / _ee_f * 100 - 100
                _es_col = "#22c55e" if _es > 0 else ("#ef4444" if _es < 0 else "#9ca3af")
                _es_sign = "+" if _es > 0 else ""
                _eps_parts.append(
                    f"<span style='color:{_es_col}; font-weight:700;'>{_es_sign}{_es:.1f}% הפתעה</span>"
                )
            _combined_parts.extend(_eps_parts)
        except (TypeError, ValueError):
            pass

    # חלק הכנסות — רק אם שני השדות קיימים ואינם null
    _rev_act = rec.get("revenue_actual_b")
    _rev_est = rec.get("revenue_estimate_b")
    if _rev_act is not None and _rev_est is not None:
        try:
            _rev_act_f = float(_rev_act)
            _rev_est_f = float(_rev_est)
            _rev_parts = [
                f"הכנסות: <b>${_rev_act_f:.2f}B</b> בפועל",
                f"<span style='color:#9ca3af;'>${_rev_est_f:.2f}B צפי</span>",
            ]
            if _rev_est_f != 0:
                _rs = _rev_act_f / _rev_est_f * 100 - 100
                _rs_col = "#22c55e" if _rs > 0 else ("#ef4444" if _rs < 0 else "#9ca3af")
                _rs_sign = "+" if _rs > 0 else ""
                _rev_parts.append(
                    f"<span style='color:{_rs_col}; font-weight:700;'>{_rs_sign}{_rs:.1f}% הפתעה</span>"
                )
            _combined_parts.extend(_rev_parts)
        except (TypeError, ValueError):
            pass

    if _combined_parts:
        rev_row = (
            "<div dir='rtl' style='display:flex; gap:12px; margin:0 0 6px; flex-wrap:wrap; "
            "align-items:center; font-size:13px; background:rgba(30,37,51,0.6); "
            "padding:5px 10px; border-radius:6px;'>"
            + " · ".join(_combined_parts) + " " + _gemini_tag + "</div>"
        )

    # --- שורת תחזית לרבעון הבא (מ-Gemini, מוצגת רק אם יש לפחות ערך אחד שאינו null) ---
    guid_row = ""
    _nqg = rec.get("next_q_guidance")
    if isinstance(_nqg, dict):
        _nq_parts = []
        _nq_rev = _nqg.get("revenue_b")
        _nq_eps = _nqg.get("eps")
        _nq_arv = _nqg.get("analyst_revenue_b")
        _nq_vs = _nqg.get("vs_consensus", "none")
        if _nq_rev is not None:
            try:
                _nq_parts.append(f"צפי הכנסות רבעון הבא: <b>${float(_nq_rev):.2f}B</b>")
            except (TypeError, ValueError):
                pass
        if _nq_eps is not None:
            try:
                _nq_parts.append(f"EPS: <b>${float(_nq_eps):.2f}</b>")
            except (TypeError, ValueError):
                pass
        if _nq_arv is not None:
            try:
                _nq_parts.append(
                    f"<span style='color:#9ca3af;'>קונצנזוס: ${float(_nq_arv):.2f}B</span>"
                )
            except (TypeError, ValueError):
                pass
        if _nq_vs and _nq_vs != "none":
            _vs_map = {
                "above": "🟢 מעל הקונצנזוס",
                "inline": "⚪ בקו עם הקונצנזוס",
                "below": "🔴 מתחת לקונצנזוס",
            }
            _vs_lbl = _vs_map.get(_nq_vs, "")
            if _vs_lbl:
                _nq_parts.append(_vs_lbl)
        if _nq_parts:
            guid_row = (
                "<div dir='rtl' style='display:flex; gap:12px; margin:0 0 6px; flex-wrap:wrap; "
                "align-items:center; font-size:13px; background:rgba(30,37,51,0.6); "
                "padding:5px 10px; border-radius:6px;'>"
                + " · ".join(_nq_parts) + " " + _gemini_tag + "</div>"
            )

    st.markdown(
        "<div dir='rtl' style='text-align:right; margin-bottom:6px;'>"
        "<span style='font-size:17px; font-weight:800;'>" + _z6_chosen + "</span>"
        + (" <span style='font-size:11px; color:#9ca3af; background:#1e2533; padding:1px 6px; border-radius:4px;'>" + label + "</span>" if label else "") +
        "<span style='color:#6b7280; font-size:13px; margin-right:10px;'> " + _z6_season + " · " + report_date + "</span></div>"
        + mkt_row + alert_html + rev_row + guid_row +
        "<div dir='rtl' style='display:flex; gap:20px; margin:6px 0 10px; flex-wrap:wrap; font-size:14px;'>"
        "<span>סנטימנט: " + emoji + " <b style='color:" + col + ";'>" + sign + str(pct) + "%</b></span>"
        "<span>תוצאות: " + res_txt + "</span>"
        "<span>הנחיה: " + guid_txt + "</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    if summary or signals:
        st.markdown(
            "<div dir='rtl' style='margin:10px 0 8px; padding-top:10px; "
            "border-top:1px solid rgba(255,255,255,0.10); "
            "font-size:12px; color:#6b7280; font-weight:700; letter-spacing:0.03em;'>📝 ניתוח</div>",
            unsafe_allow_html=True,
        )
    if summary:
        st.markdown(
            "<div dir='rtl' style='color:#d1d5db; font-size:14px; line-height:1.6; margin-bottom:8px; text-align:right;'>"
            + summary + "</div>",
            unsafe_allow_html=True,
        )
    if signals:
        dir_map = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
        sig_rows = "".join(
            "<tr>"
            "<td style='text-align:right; padding:4px 8px; font-size:13px;'>" + s.get("domain", "") + "</td>"
            "<td style='text-align:center; padding:4px 8px;'>" + dir_map.get(s.get("direction", ""), "") + "</td>"
            "<td style='text-align:right; padding:4px 8px; color:#9ca3af; font-size:12px;'>" + s.get("note", "") + "</td>"
            "</tr>"
            for s in signals
        )
        st.markdown(
            "<div dir='rtl' style='text-align:right;'><b style='font-size:13px;'>סיגנלים תחומיים:</b>"
            "<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:4px;'>"
            "<tr>"
            "<th style='text-align:right; padding:4px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>תחום</th>"
            "<th style='text-align:center; padding:4px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>כיוון</th>"
            "<th style='text-align:right; padding:4px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>הערה</th>"
            "</tr>" + sig_rows + "</table></div>",
            unsafe_allow_html=True,
        )
        # --- נגיעה בחברות הישראליות (הצלבה מקומית, ללא AI) ---
        _il_matches = israeli_exposure_to_signals(signals)
        if _il_matches:
            _il_dir_map = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
            _il_rows_html = []
            for _il_sym in ["TSEM", "NVMI", "CAMT"]:
                _il_hits = _il_matches.get(_il_sym)
                if not _il_hits:
                    continue
                _il_parts = [f"<b>{_il_sym}</b>"]
                for _il_dom, _il_dir, _il_eff in _il_hits:
                    _il_icon = _il_dir_map.get(_il_dir, "")
                    _il_pct = int(round(_il_eff * 100))
                    _il_parts.append(
                        f"{_il_icon} {_il_dom} "
                        f"<span style='color:#6b7280; font-size:11px;'>({_il_pct}%)</span>"
                    )
                _il_rows_html.append(" · ".join(_il_parts))
            if _il_rows_html:
                st.markdown(
                    "<div dir='rtl' style='text-align:right; margin-top:8px; "
                    "background:rgba(20,24,36,0.7); border:1px solid #2d3748; "
                    "border-radius:6px; padding:8px 12px;'>"
                    "<div style='font-size:13px; font-weight:700; color:#e5e7eb; margin-bottom:6px;'>"
                    "🇮🇱 נגיעה בחברות הישראליות:</div>"
                    + "".join(
                        "<div style='font-size:13px; color:#d1d5db; margin-bottom:3px;'>" + r + "</div>"
                        for r in _il_rows_html
                    )
                    + "<div style='font-size:11px; color:#6b7280; margin-top:6px;'>"
                    "הצלבה אוטומטית של סיגנלי הדוח עם חשיפות החברות ב-TECH_GROUPS — לא ניתוח AI"
                    "</div></div>",
                    unsafe_allow_html=True,
                )


with st.container(border=True):
    # --- תוצאה ממתינה לאישור (מ-Gemini, טרם נשמרה) — מצב מפתח בלבד ---
    if DEV_MODE and _z6_pending:
        if "error" in _z6_pending:
            st.warning(_z6_pending["error"])
        else:
            st.info("ניתוח חדש ממתין לאישור שמירה:")
            with st.container(border=True):
                _render_analysis_record(_z6_pending)
                _sc, _dc = st.columns(2)
                with _sc:
                    if st.button("✅ שמור לקובץ", key="z6_savebtn_" + _z6_chosen,
                                 use_container_width=True, type="primary"):
                        save_sentiment_record(_z6_chosen, _z6_season, {
                            "report_date": _z6_pending.get("report_date", ""),
                            "sentiment_score": _z6_pending.get("sentiment_score"),
                            "results_vs_expectations": _z6_pending.get("results_vs_expectations", ""),
                            "guidance_direction": _z6_pending.get("guidance_direction", ""),
                            "summary": _z6_pending.get("summary", ""),
                            "domain_signals": _z6_pending.get("domain_signals", []),
                            "revenue_actual_b": _z6_pending.get("revenue_actual_b"),
                            "revenue_estimate_b": _z6_pending.get("revenue_estimate_b"),
                            "eps_actual": _z6_pending.get("eps_actual"),
                            "eps_estimate": _z6_pending.get("eps_estimate"),
                            "next_q_guidance": _z6_pending.get("next_q_guidance"),
                            "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        })
                        del st.session_state[_z6_result_key]
                        st.success("נשמר: " + _z6_chosen + " / " + _z6_season)
                        st.rerun()
                with _dc:
                    if st.button("🗑️ בטל", key="z6_discardbtn_" + _z6_chosen, use_container_width=True):
                        del st.session_state[_z6_result_key]
                        st.rerun()

    # --- ניתוח שמור בקובץ ---
    elif _z6_saved_rec:
        _z6_eps_surp = None
        _z6_react = None
        _z6_rd = _z6_saved_rec.get("report_date")
        if _z6_rd and _z6_rd != "—":
            for _e in _z6_all_entries:
                if _e["symbol"] == _z6_chosen and str(_e["date"]) == _z6_rd:
                    _z6_eps_surp = _e.get("surprise")
                    break
            _z6_react, _ = get_stock_reaction(_z6_chosen, _z6_rd)
        with st.container(border=True):
            _render_analysis_record(_z6_saved_rec, label="שמור",
                                    eps_surprise=_z6_eps_surp, stock_reaction=_z6_react)
        if DEV_MODE:
            if st.button("🔄 עדכן ניתוח עם Gemini", key="z6_analyzebtn_" + _z6_chosen):
                with st.spinner("מחפש דוח ושיחת ועידה עם Gemini..."):
                    st.session_state[_z6_result_key] = gemini_analyze_earnings(_z6_chosen, _z6_season)
                st.rerun()

    # --- אין ניתוח עדיין ---
    else:
        st.markdown(
            "<div dir='rtl' style='text-align:center; padding:20px 12px; "
            "background:rgba(255,255,255,0.03); border-radius:8px; color:#9ca3af; font-size:14px;'>"
            "ℹ️ אין ניתוח שמור לחברה זו בעונה " + _z6_season + " — טרם נותח."
            "</div>",
            unsafe_allow_html=True,
        )
        if DEV_MODE:
            if st.button("🧠 נתח דוח עם Gemini", key="z6_analyzebtn_" + _z6_chosen, type="primary"):
                with st.spinner("מחפש דוח ושיחת ועידה עם Gemini..."):
                    st.session_state[_z6_result_key] = gemini_analyze_earnings(_z6_chosen, _z6_season)
                st.rerun()

# --- היסטוריית תוצאות מול צפי ---
with st.container(border=True):
    with st.expander("📊 היסטוריית תוצאות מול צפי", expanded=False):
        _hist_eps_df = get_earnings_history(_z6_chosen)
        _hist_rev_s, _hist_rev_name = get_quarterly_revenue(_z6_chosen)
        _hist_ccy = get_financial_currency(_z6_chosen)

        if _hist_eps_df is None:
            st.caption("אין נתוני EPS היסטוריים זמינים לחברה זו.")
        else:
            # מיפוי YYYYQN → נתוני EPS
            _h_eps_by_q: dict[str, dict] = {}
            for _hdt, _hrow in _hist_eps_df.iterrows():
                _hqk = season_from_date(_hdt)
                _h_eps_by_q[_hqk] = {
                    "date": str(_hdt.date()) if hasattr(_hdt, "date") else str(_hdt)[:10],
                    "actual": _hrow.get("Reported EPS"),
                    "est":    _hrow.get("EPS Estimate"),
                    "surp":   _hrow.get("Surprise(%)"),
                }

            # מיפוי YYYYQN → הכנסות
            _h_rev_by_q: dict[str, float] = {}
            if _hist_rev_s is not None:
                for _rdt, _rv in zip(_hist_rev_s.index, _hist_rev_s.values):
                    _h_rev_by_q[season_from_date(_rdt)] = float(_rv)

            _h_has_rev = bool(_h_rev_by_q)

            # מיפוי YYYYQN → רשומת סנטימנט מ-Gemini (_z6_sent_data כבר בסקופ)
            _h_sent_by_q: dict[str, dict] = {
                _sqk: _srec
                for _sqk, _srec in (_z6_sent_data.get(_z6_chosen) or {}).items()
            }

            # רק רבעונים מנותחים ושמורים — הטבלה תצבור כל ניתוח חדש
            _h_quarters = sorted(_h_sent_by_q.keys(), reverse=True)

            def _hfmt(v, dec=2):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    return "<span style='color:#6b7280;'>—</span>"
                return f"{v:.{dec}f}"

            def _hfmt_surp(v):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    return "<span style='color:#6b7280;'>—</span>"
                c = "#22c55e" if v > 0 else ("#ef4444" if v < 0 else "#9ca3af")
                s = "+" if v > 0 else ""
                return f"<span style='color:{c}; font-weight:700;'>{s}{v:.1f}%</span>"

            def _hfmt_sent(score):
                sc = float(score)
                pct = int(round(sc * 100))
                sign = "+" if pct >= 0 else ""
                col = "#22c55e" if sc >= 0.15 else ("#ef4444" if sc <= -0.15 else "#9ca3af")
                emoji = "🟢" if sc >= 0.15 else ("🔴" if sc <= -0.15 else "⚪")
                return f"{emoji} <span style='color:{col}; font-weight:700;'>{sign}{pct}%</span>"

            _rev_hdr_txt = f"הכנסות ({_hist_ccy}, B)" if _h_has_rev else ""
            _h_thdr = (
                "<tr style='border-bottom:1px solid #444;'>"
                "<th style='text-align:right; padding:6px 10px; color:#9ca3af;'>רבעון</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>תאריך</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>EPS בפועל</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>EPS צפי</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>הפתעה %</th>"
                + (f"<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>{_rev_hdr_txt}</th>"
                   if _h_has_rev else "")
                + "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>הכנסות צפי 🔮 ($B)</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>הפתעת הכנסות 🔮</th>"
                "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>סנטימנט</th>"
                "</tr>"
            )
            _h_td_dash = "<td style='text-align:center; padding:6px 10px; color:#6b7280;'>—</td>"
            _h_rows_html = ""
            for _hqk in _h_quarters:
                _hq = _h_eps_by_q.get(_hqk) or {}
                _h_srec = _h_sent_by_q.get(_hqk) or {}
                _rev_cell = ""
                if _h_has_rev:
                    _hrv = _h_rev_by_q.get(_hqk)
                    if _hrv is not None and not (isinstance(_hrv, float) and math.isnan(_hrv)):
                        _rev_cell = f"<td style='text-align:center; padding:6px 10px;'>{_hrv:.2f}B</td>"
                    else:
                        _rev_cell = _h_td_dash

                # --- תאי Gemini: הכנסות צפי / הפתעת הכנסות / סנטימנט ---
                _h_rev_est_gem = _h_srec.get("revenue_estimate_b")
                _h_rev_act_gem = _h_srec.get("revenue_actual_b")
                _h_sent_score  = _h_srec.get("sentiment_score")

                # עמודה 1: הכנסות צפי
                _gem_est_cell = _h_td_dash
                if _h_rev_est_gem is not None:
                    try:
                        _gem_est_cell = f"<td style='text-align:center; padding:6px 10px;'>${float(_h_rev_est_gem):.2f}B</td>"
                    except (TypeError, ValueError):
                        pass

                # עמודה 2: הפתעת הכנסות (מזוג Gemini בלבד, לא מול yfinance)
                _gem_surp_cell = _h_td_dash
                if _h_rev_act_gem is not None and _h_rev_est_gem is not None:
                    try:
                        _ge_f = float(_h_rev_est_gem)
                        _ga_f = float(_h_rev_act_gem)
                        if _ge_f != 0:
                            _gem_surp_cell = f"<td style='text-align:center; padding:6px 10px;'>{_hfmt_surp(_ga_f / _ge_f * 100 - 100)}</td>"
                    except (TypeError, ValueError):
                        pass

                # עמודה 3: סנטימנט
                _gem_sent_cell = _h_td_dash
                if _h_sent_score is not None:
                    try:
                        _gem_sent_cell = f"<td style='text-align:center; padding:6px 10px;'>{_hfmt_sent(_h_sent_score)}</td>"
                    except (TypeError, ValueError):
                        pass

                _h_date_val = _hq.get('date') or _h_srec.get('report_date', '—')
                _h_rows_html += (
                    "<tr style='border-top:1px solid rgba(255,255,255,0.07);'>"
                    f"<td style='text-align:right; padding:6px 10px; font-weight:600;'>{_hqk}</td>"
                    f"<td style='text-align:center; padding:6px 10px; color:#9ca3af; font-size:11px;'>{_h_date_val}</td>"
                    f"<td style='text-align:center; padding:6px 10px;'>{_hfmt(_hq.get('actual'))}</td>"
                    f"<td style='text-align:center; padding:6px 10px; color:#9ca3af;'>{_hfmt(_hq.get('est'))}</td>"
                    f"<td style='text-align:center; padding:6px 10px;'>{_hfmt_surp(_hq.get('surp'))}</td>"
                    + _rev_cell
                    + _gem_est_cell + _gem_surp_cell + _gem_sent_cell
                    + "</tr>"
                )
            st.markdown(
                "<div dir='rtl' style='overflow-x:auto;'>"
                "<table dir='rtl' style='width:100%; border-collapse:collapse; font-size:13px;'>"
                + _h_thdr + _h_rows_html + "</table></div>",
                unsafe_allow_html=True,
            )
            if not _h_has_rev:
                st.caption("אין נתוני הכנסות רבעוניים זמינים לחברה זו.")

# ======================================================
# גרף מגמת סנטימנט לפי חברה ספציפית
# ======================================================
st.markdown(section_header("📊 מגמת סנטימנט לפי חברה", "#60a5fa"), unsafe_allow_html=True)
with st.container(border=True):
    _z6_cmp_sym = st.selectbox("בחרי חברה למגמת הסנטימנט:", CORE_COMPANIES, key="z6_cmp_sym")
    _z6_cmp_seasons = sorted(_z6_sent_data.get(_z6_cmp_sym, {}).keys())
    if len(_z6_cmp_seasons) == 0:
        st.markdown(
            "<div dir='rtl' style='text-align:center; padding:20px 12px; "
            "background:rgba(255,255,255,0.03); border-radius:8px; color:#9ca3af; font-size:14px;'>"
            "ℹ️ אין ניתוחים שמורים לחברה " + _z6_cmp_sym + " עדיין."
            "</div>",
            unsafe_allow_html=True,
        )
    elif len(_z6_cmp_seasons) == 1:
        _cmp_s0 = _z6_cmp_seasons[0]
        _cmp_sc0 = float(_z6_sent_data[_z6_cmp_sym][_cmp_s0].get("sentiment_score", 0) or 0)
        _cmp_pct0 = int(round(_cmp_sc0 * 100))
        _cmp_sign0 = "+" if _cmp_pct0 >= 0 else ""
        st.markdown(
            "<div dir='rtl' style='text-align:center; padding:20px 12px; "
            "background:rgba(255,255,255,0.03); border-radius:8px; color:#9ca3af; font-size:14px;'>"
            "ℹ️ עונה אחת שמורה (" + _cmp_s0 + ": <b style='color:#e5e7eb;'>"
            + _cmp_sign0 + str(_cmp_pct0) + "%</b>). הגרף יופיע לאחר ניתוח עונה נוספת."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        _cmp_scores = [
            float(_z6_sent_data[_z6_cmp_sym][_s].get("sentiment_score", 0) or 0)
            for _s in _z6_cmp_seasons
        ]
        render_sentiment_trend(_z6_cmp_seasons, _cmp_scores, "trend_cmp_" + _z6_cmp_sym)
