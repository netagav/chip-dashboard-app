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

HOT_THRESHOLD = 10
BROAD_THRESHOLD = 0.6
GAP_THRESHOLD = 15
MOVE_ALERT = 2.0

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


def build_chart(stocks, period):
    series_list = []
    for symbol in stocks:
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


def build_spread_chart(stocks, period):
    # גרף פער מצטבר: חציון התחום (מנורמל ל-100) פחות SOXX (מנורמל ל-100), לאורך התקופה
    # אזור צבוע: ירוק כשהתחום מכה את המדד, אדום כשמפגר
    chart_data = build_chart(stocks, period)
    if chart_data.empty:
        return None
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

    base = alt.Chart(df).encode(
        x=alt.X("תאריך:T", title=None, axis=alt.Axis(labelFontSize=12, labelPadding=8, tickCount=6))
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


def section_banner(number, total, icon, title, color, subtitle=""):
    """באנר גדול ובולט לתחילת אזור ראשי בדשבורד (SOXX, מפת חום, צלילה, פילוח).
    שונה מ-section_header (שמיועד לתת-אזורים קטנים בתוך כרטיס) — זה עבור
    ארבעת האזורים הגדולים של הדשבורד עצמו, עם מספור, רקע מלא ומרווח נדיב."""
    sub_html = ""
    if subtitle:
        sub_html = ("<div style='font-size:14px; color:rgba(255,255,255,0.75); "
                    "margin-top:4px; font-weight:400;'>" + subtitle + "</div>")
    st.markdown(
        "<div style='height:36px;'></div>"
        "<div dir='rtl' style='text-align:right; background:linear-gradient(90deg, " + color + "22, transparent); "
        "border-right:8px solid " + color + "; border-radius:10px; "
        "padding:16px 20px; margin-bottom:18px;'>"
        "<div style='display:flex; align-items:center; justify-content:space-between;'>"
        "<span style='font-size:24px; font-weight:800; color:#ffffff;'>" + icon + "&nbsp; " + title + "</span>"
        "<span style='font-size:13px; color:rgba(255,255,255,0.45); font-weight:600; "
        "background:rgba(255,255,255,0.06); padding:3px 10px; border-radius:20px;'>"
        "אזור " + str(number) + "/" + str(total) + "</span>"
        "</div>" + sub_html + "</div>",
        unsafe_allow_html=True,
    )


def section_header(title, accent):
    # כותרת אזור מובלטת עם פס צבעוני ורקע עדין, להפרדה ברורה בתוך הכרטיס
    return ("<div dir='rtl' style='text-align:right; font-weight:800; font-size:18px; "
            "background:rgba(120,120,120,0.10); border-right:5px solid " + accent +
            "; border-radius:6px; padding:8px 12px; margin:20px 0 10px 0;'>"
            + title + "</div>")


def returns_table_html(pairs, descending=True):
    sortable = []
    for symbol, change in pairs:
        sortable.append((change, symbol))
    sortable.sort(reverse=descending)
    rows = ""
    for change, symbol in sortable:
        c = "#22c55e" if change >= 0 else "#ef4444"
        rows += ("<tr><td style='text-align:right; padding:4px 10px;'>" + symbol +
                 "</td><td style='text-align:right; padding:4px 10px; color:" + c +
                 "; font-weight:600;'>" + str(round(change, 1)) + "%</td></tr>")
    return ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
            "<tr><th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
            "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th></tr>"
            + rows + "</table>")


def tech_table_html(rows):
    # טבלת מניות לתחום טכנולוגי: מניה, תשואה, ומשקל אפקטיבי בתוך התחום
    # rows = רשימה של [סימבול, תשואה, משקל מנורמל], כבר ממוינת מהגבוה לנמוך
    body = ""
    for symbol, change, weight in rows:
        c = "#22c55e" if change >= 0 else "#ef4444"
        body += ("<tr><td style='text-align:right; padding:4px 10px;'>" + symbol +
                 "</td><td style='text-align:right; padding:4px 10px; color:" + c +
                 "; font-weight:600;'>" + str(round(change, 1)) + "%</td>"
                 "<td style='text-align:right; padding:4px 10px; color:#9ca3af;'>" +
                 str(round(weight * 100, 1)) + "%</td></tr>")
    return ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
            "<tr><th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
            "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th>"
            "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>משקל בתחום</th></tr>"
            + body + "</table>")


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

period_label = st.sidebar.selectbox("Period:", list(PERIOD_OPTIONS.keys()), index=3)
period = PERIOD_OPTIONS[period_label]
st.sidebar.caption("בחרי תקופה — כל הדשבורד יתעדכן")

# ======================================================
# אזור SOXX
# ======================================================
section_banner(1, 4, "🏆", "מדד סקטור השבבים — SOXX", "#f59e0b",
                "התנהגות המדד הכללי, עם התראות AI על תנועות חריגות")
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

    soxx_price = soxx_close.reset_index()
    soxx_price.columns = ["תאריך", "מחיר"]
    if period == "lastclose":
        soxx_price = soxx_price.tail(3)
    base_price = soxx_price["מחיר"].iloc[0]
    soxx_price["תשואה"] = soxx_price["מחיר"] / base_price * 100 - 100
    # תשואה צבועה לבועה: ירוק לחיובי, אדום לשלילי, שתי ספרות
    ret_cells = []
    for v in soxx_price["תשואה"]:
        col = "#22c55e" if v >= 0 else "#ef4444"
        sg = "+" if v >= 0 else ""
        ret_cells.append("<span style='color:" + col + "'>" + sg + format(v, ".2f") + "%</span>")

    mini = go.Figure()
    mini.add_trace(go.Scatter(
        x=soxx_price["תאריך"], y=soxx_price["מחיר"], mode="lines",
        line=dict(color="#f59e0b", width=2.5), fill="tozeroy",
        fillcolor="rgba(245,158,11,0.15)",
        customdata=ret_cells,
        hovertemplate="%{x|%d/%m/%Y}<br>מחיר: $%{y:.2f}<br>תשואה: %{customdata}<extra></extra>",
    ))
    # ציר Y דינמי: לא מתחילים מאפס, אלא מרווח קטן סביב טווח המחירים בפועל,
    # כדי שתנועת המחיר תיראה נכון (בעיקר בתקופות קצרות). מילוי עדין עד תחתית הציר.
    price_min = float(soxx_price["מחיר"].min())
    price_max = float(soxx_price["מחיר"].max())
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
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(mini, use_container_width=True)

    if len(holdings_pairs) >= 2:
        top5 = holdings_pairs[:5]
        bottom5 = list(reversed(holdings_pairs[-5:]))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📈 העליות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(top5, descending=True), unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📉 הירידות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(bottom5, descending=False), unsafe_allow_html=True)


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
def render_domain_detail(sector, pairs, period):
    """מרנדר את תוכן הפרטים של תחום: מניות, גרף מגמת הפער, וחדשות + ניתוח AI.
    משמש גם במפת החום (שרשרת ערך). נקרא רק כשהשורה של התחום פתוחה."""
    # --- אזור טבלת המניות ---
    st.markdown(section_header("📊 מניות בתחום", "#3b82f6"), unsafe_allow_html=True)
    st.markdown(returns_table_html(pairs), unsafe_allow_html=True)

    # --- גרף מגמת הפער מ-SOXX לאורך התקופה ---
    st.markdown(section_header("📈 מגמת הפער מ-SOXX לאורך התקופה", "#22c55e"), unsafe_allow_html=True)
    spread_chart = build_spread_chart(value_chain[sector], period)
    if spread_chart is not None:
        st.altair_chart(spread_chart, use_container_width=True)
        st.caption("🟢 מעל הקו = התחום מכה את SOXX · 🔴 מתחת = מפגר · הנקודה האחרונה = הפער הנוכחי")
    else:
        st.caption("אין מספיק נתונים לגרף המגמה")

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


section_banner(2, 4, "🗺️", "מפת חום — דירוג שרשרת הערך", "#3b82f6",
                "11 חוליות שרשרת הערך, מדורגות לפי המרחק מ-SOXX")
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
section_banner(3, 4, "🔍", "צלילה לתחום — השוואת מניות", "#22c55e",
                "בחרי תחום כדי להשוות בין המניות שבו, מול חציון התחום ומול SOXX")

sector_names = []
for r in results:
    sector_names.append(r[6])

chosen = st.selectbox("בחרי תחום:", sector_names, format_func=clean_name)

chart_data = build_chart(value_chain[chosen], period)
if chart_data.empty:
    st.warning("אין מספיק נתונים לתחום הזה")
else:
    st.caption("ביצועי המניות מול חציון התחום ומול מדד SOXX — הכל מנורמל ל-100 בתחילת התקופה. לחצי על מניה במקרא כדי להסתיר/להציג אותה.")

    date_index = chart_data.index
    median_series = chart_data.median(axis=1)
    soxx_close2 = get_history(BENCHMARK, period)

    # פלטת צבעים ברורה ועקבית בין המקרא לקווים
    palette = ["#60a5fa", "#f472b6", "#34d399", "#fbbf24", "#a78bfa",
               "#fb7185", "#22d3ee", "#a3e635", "#fb923c", "#e879f9",
               "#4ade80", "#38bdf8", "#facc15", "#f87171", "#c084fc"]

    def ret_html(ret_series):
        # תשואה צבועה: ירוק לחיובי, אדום לשלילי, שתי ספרות אחרי הנקודה
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
            hovertemplate="<b>" + symbol + "</b><br>%{x|%d/%m/%Y}<br>"
                          "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
        ))

    median_ret = median_series - 100
    fig.add_trace(go.Scatter(
        x=date_index, y=median_series, name="חציון התחום", mode="lines",
        line=dict(color="#ffffff", width=4),
        customdata=ret_html(median_ret),
        hovertemplate="<b>חציון התחום</b><br>%{x|%d/%m/%Y}<br>"
                      "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
    ))

    if soxx_close2 is not None:
        soxx_norm2 = soxx_close2 / soxx_close2.iloc[0] * 100
        soxx_ret = soxx_norm2 - 100
        fig.add_trace(go.Scatter(
            x=soxx_norm2.index, y=soxx_norm2, name="SOXX", mode="lines",
            line=dict(color="#f59e0b", width=4, dash="dash"),
            customdata=ret_html(soxx_ret),
            hovertemplate="<b>SOXX</b><br>%{x|%d/%m/%Y}<br>"
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
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
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

# ======================================================
# פילוח טכנולוגי — ליבה ומעטפת
# ======================================================
section_banner(4, 4, "🧬", "פילוח טכנולוגי — ליבה ומעטפת", "#a78bfa")
st.caption("כל תחום מדורג לפי תשואה משוקללת: ליבה (חשיפה × 1.0) ומעטפת (חשיפה × 0.4). "
           "שני צירים חופפים בכוונה — טכנולוגיה (מה מוכרים) ושוקי קצה (למי מוכרים) — אין להשוות ביניהם כסכום.")


def render_tech_detail(idx):
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
            st.markdown(tech_table_html(idx["core"]), unsafe_allow_html=True)
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
            st.markdown(tech_table_html(idx["env"]), unsafe_allow_html=True)
        else:
            st.caption("אין מניות מעטפת בתחום זה")


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
                        render_tech_detail(idx)
                rankn = rankn + 1