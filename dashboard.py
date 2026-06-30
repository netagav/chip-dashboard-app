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

# ---------- מטריצת חשיפה נושאית ----------
# כל נושא = מילון של מניה לציון חשיפה:
# 3 = ליבה (מוכרת את הרכיב, העסק הוא הנושא)
# 2 = מנוע צמיחה (חשיפה משמעותית, מניע צמיחה אמיתי)
# 1 = עקיפה (נהנית רוחבית או בעקיפין)
# מניה שלא מופיעה בנושא = 0, ללא חשיפה
# הנושאים מקובצים בשלוש קבוצות-על, כמו בתעודת הזהות.
THEME_GROUPS = {
    "End-Markets (שווקי קצה)": {
        "AI Compute (מחשוב AI)": {
            "NVDA": 3, "AMD": 3, "AVGO": 3, "MRVL": 3,
            "TSM": 2, "SMCI": 2, "VRT": 2, "MU": 2, "000660.KS": 2, "ANET": 2,
            "DELL": 1, "HPE": 1, "ETN": 1,
        },
        "Edge AI (AI בקצה)": {
            "QCOM": 3, "AAPL": 3, "ARM": 3,
            "NXPI": 2, "STM": 2,
            "AMD": 1, "NVDA": 1,
        },
        "Legacy DC (דאטה-סנטר מסורתי)": {
            "INTC": 3,
            "DELL": 2, "HPE": 2, "MU": 2,
            "TXN": 1, "ADI": 1, "WDC": 1, "STX": 1,
        },
        "Automotive (רכב)": {
            "NXPI": 3, "STM": 3, "IFNNY": 3, "ON": 3, "RNECY": 3,
            "TXN": 2, "MCHP": 2,
            "ADI": 1, "QCOM": 1,
        },
        "Industrial (תעשייה)": {
            "ADI": 3, "TXN": 3, "IFNNY": 3,
            "STM": 2, "ON": 2, "RNECY": 2, "MCHP": 2, "ETN": 2,
            "AEIS": 1,
        },
        "Consumer PC/Mobile (צרכני)": {
            "AAPL": 3, "QCOM": 3,
            "AMD": 2, "INTC": 2, "MU": 2, "005930.KS": 2, "ARM": 2,
            "WDC": 1, "STX": 1,
        },
    },
    "Product / Arch (מוצר וארכיטקטורה)": {
        "HBM (זיכרון רוחב פס גבוה)": {
            "MU": 3, "000660.KS": 3, "005930.KS": 3,
            "ONTO": 2, "CAMT": 2, "BESIY": 2, "NVMI": 2,
            "AMAT": 1, "KLAC": 1, "TER": 1, "AMKR": 1, "NVDA": 1,
        },
        "Commodity Memory (זיכרון סטנדרטי)": {
            "MU": 3, "000660.KS": 3, "005930.KS": 3,
            "LRCX": 2, "WDC": 1, "STX": 1, "AMAT": 1,
        },
        "Custom Silicon / ASIC (סיליקון בהזמנה)": {
            "AVGO": 3, "MRVL": 3,
            "TSM": 2, "SNPS": 2, "CDNS": 2, "ARM": 2,
            "GFS": 1,
        },
        "Power Semi SiC/GaN (מוליכי הספק)": {
            "ON": 3, "STM": 3, "IFNNY": 3,
            "RNECY": 2, "TXN": 2,
            "ADI": 1, "NXPI": 1, "AEIS": 1, "TSEM": 1,
        },
        "Silicon Photonics (פוטוניקת סיליקון)": {
            "COHR": 3, "LITE": 3, "TSEM": 3,
            "AVGO": 2, "MRVL": 2,
            "ANET": 1, "NVDA": 1,
        },
    },
    "Mfg Inflections (נקודות מפנה בייצור)": {
        "GAA & Backside Power (טרנזיסטורים והספק)": {
            "ASML": 3, "AMAT": 3, "LRCX": 3,
            "KLAC": 2, "TOELY": 2, "ASMIY": 2, "INTC": 2, "TSM": 2,
            "005930.KS": 1,
        },
        "Advanced Packaging (אריזה מתקדמת)": {
            "AMKR": 3, "BESIY": 3,
            "TSM": 2, "ASMIY": 2, "CAMT": 2, "ONTO": 2,
            "AMAT": 1, "TER": 1, "ATEYY": 1, "NVDA": 1,
        },
        "High-NA EUV (ליתוגרפיה מתקדמת)": {
            "ASML": 3,
            "TSM": 2, "INTC": 2,
            "KLAC": 1, "005930.KS": 1,
        },
    },
}

# מיפוי שטוח של נושא -> ציונים, נבנה אוטומטית מהקבוצות (לשימוש הפונקציות)
EXPOSURE_MATRIX = {}
for _group_themes in THEME_GROUPS.values():
    for _theme_name, _scores in _group_themes.items():
        EXPOSURE_MATRIX[_theme_name] = _scores

# שמות רמות החשיפה לתצוגה
EXPOSURE_LEVELS = {3: "🎯 ליבה", 2: "🚀 מנוע צמיחה", 1: "↪️ עקיפה"}

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


def compute_theme_index(theme_name, period):
    weights = EXPOSURE_MATRIX.get(theme_name, {})
    weighted_sum = 0.0          # סכום (תשואה × משקל)
    weight_total = 0            # סכום המשקלים שנספרו בפועל
    by_level = {3: [], 2: [], 1: []}   # פירוק לפי רמת חשיפה

    for symbol, score in weights.items():
        if score <= 0:
            continue
        change = get_change(symbol, period)
        if change is None:
            continue            # מדלגים על מניה בלי נתונים, ולא סופרים את משקלה
        weighted_sum += change * score
        weight_total += score
        by_level[score].append((symbol, change))

    if weight_total == 0:
        weighted_return = None
    else:
        weighted_return = weighted_sum / weight_total

    # ממוצע פשוט לכל רמת חשיפה, ותרומת הרמה לתשואה המשוקללת
    # תרומת רמה = סכום(תשואה × משקל) של אותה רמה, חלקי סך כל המשקלים
    # שלוש התרומות יחד מסתכמות בדיוק לתשואה המשוקללת
    level_summary = {}
    for level in (3, 2, 1):
        rows = by_level[level]
        if len(rows) > 0:
            avg = sum(c for s, c in rows) / len(rows)
            contribution = sum(c * level for s, c in rows) / weight_total
        else:
            avg = None
            contribution = 0.0
        level_summary[level] = {
            "avg": avg,
            "contribution": contribution,
            "stocks": sorted(rows, key=lambda x: x[1], reverse=True),
        }

    return {
        "weighted_return": weighted_return,
        "weight_total": weight_total,
        "by_level": level_summary,
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
    chart_data = pd.DataFrame()
    for symbol in stocks:
        close = get_history(symbol, period)
        if close is None:
            continue
        chart_data[symbol] = close / close.iloc[0] * 100
    return chart_data.ffill()


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

    base = alt.Chart(df).encode(
        x=alt.X("תאריך:T", title=None, axis=alt.Axis(labelFontSize=12, labelPadding=8, tickCount=6))
    )
    # אזור ירוק לפער חיובי, אדום לשלילי
    area_pos = base.transform_filter("datum.spread >= 0").mark_area(
        color="rgba(34,197,94,0.35)"
    ).encode(y=alt.Y("spread:Q", title="פער מ-SOXX (נק')",
                     axis=alt.Axis(labelFontSize=12, titleFontSize=13, titlePadding=10)))
    area_neg = base.transform_filter("datum.spread < 0").mark_area(
        color="rgba(239,68,68,0.35)"
    ).encode(y="spread:Q")
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
soxx_close = get_history(BENCHMARK, period)

if soxx_close is None:
    st.markdown("### 🏆 SOXX — מדד סקטור השבבים")
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
    mini.update_layout(
        height=240, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=30, l=50, r=20),
        yaxis=dict(title="מחיר ($)", gridcolor="rgba(255,255,255,0.08)"),
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

st.divider()

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
st.header("🗺️ מפת חום — דירוג התחומים")
st.caption("מדורג לפי המרחק מ-SOXX — מי מכה את המדד הכי הרבה. לחצי על תחום לפרטים.")

rank = 1
for median, average, up, down, total, breadth, sector, pairs in results:
    label, color, bg = label_info(median, breadth, soxx_change, period)
    # רקע לפי המרחק האמיתי מ-SOXX: ירוק (מכה), צהוב (קרוב), אדום (מפגר)
    threshold = RELATIVE_THRESHOLD.get(period, 10.0)
    rel_dist = median - soxx_ref
    grad_bg = zone_bg(rel_dist, threshold, max_abs_dist)

    driver = ""
    if average - median >= GAP_THRESHOLD and breadth < BROAD_THRESHOLD:
        top_symbol = pairs[0][0]
        top_change = pairs[0][1]
        for s, c in pairs:
            if c > top_change:
                top_symbol = s
                top_change = c
        driver = ("<div style='color:#f59e0b; font-size:13px; margin-top:6px;'>📍 מונע בעיקר ע\"י <b>"
                  + top_symbol + "</b> (" + str(round(top_change, 1)) + "%)</div>")

    summary_line = ("<div style='color:" + color + "; font-weight:600; margin-top:6px;'>חציון "
                    + str(round(median, 1)) + "% · ממוצע " + str(round(average, 1))
                    + "% · עלו " + str(up) + " · ירדו " + str(down) + " · מתוך " + str(total) + "</div>")

    # שורת השוואה למדד: כמה התחום מכה או מפגר אחרי SOXX
    soxx_line = ""
    if soxx_change is not None:
        rel = median - soxx_change
        if rel >= 0:
            rel_color = "#22c55e"
            rel_text = "📊 מכה את SOXX ב-+" + str(round(rel, 1)) + " נק'"
        else:
            rel_color = "#ef4444"
            rel_text = "📊 מפגר אחרי SOXX ב-" + str(round(rel, 1)) + " נק'"
        soxx_line = ("<div style='color:" + rel_color + "; font-weight:600; font-size:14px; margin-top:4px;'>"
                     + rel_text + " (SOXX " + str(round(soxx_change, 1)) + "%)</div>")

    card = ("<div dir='rtl' style='background:" + grad_bg + "; border-right:6px solid " + color +
            "; border-radius:10px; padding:10px 14px; margin-bottom:2px; text-align:right;'>"
            "<div style='font-weight:700; font-size:17px;'>"
            + str(rank) + ". " + label + " — " + clean_name(sector) + "</div>"
            + summary_line + soxx_line + driver + "</div>")
    st.markdown(card, unsafe_allow_html=True)

    with st.expander("פרטים, מניות וחדשות"):
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

        if len(sector_news) == 0:
            st.markdown(section_header("📰 חדשות אחרונות בתחום", "#a78bfa"), unsafe_allow_html=True)
            st.caption("אין חדשות זמינות כרגע לתחום הזה")
        else:
            st.markdown(section_header("📰 חדשות אחרונות בתחום", "#a78bfa"), unsafe_allow_html=True)
            head_col, btn_col = st.columns([3, 1])
            with head_col:
                st.caption("לחצי לניתוח סנטימנט החדשות עם AI")
            with btn_col:
                titles_list = [item["title"] for sym, item in sector_news]
                sig = titles_signature(titles_list)
                news_key = "news_analysis_" + str(rank) + "_" + sig
                do_analyze = st.button("🧠 נתח חדשות", key="newsbtn_" + str(rank))

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

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    rank = rank + 1

# ---------- צלילה לתחום ----------
st.divider()
st.header("🔍 צלילה לתחום")

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
# דירוג נושאי לפי חשיפה — שלוש קבוצות העל
# ======================================================
st.divider()
st.header("🧪 דירוג נושאי לפי חשיפה")
st.caption("ניסיוני · כל נושא מדורג לפי תשואה משוקללת בחשיפת המניות אליו (ציון 0–3)")


def exposure_level_block(level, data):
    """כרטיס לרמת חשיפה אחת: כותרת צבעונית, תרומה, וטבלת מניות."""
    titles = {
        3: ("🎯 ליבה — מוכרות את הרכיב", "#22c55e"),
        2: ("🚀 מנוע צמיחה", "#3b82f6"),
        1: ("↪️ חשיפה עקיפה", "#a78bfa"),
    }
    title, head_color = titles[level]
    avg = data["avg"]
    contrib = data["contribution"]
    avg_str = "—" if avg is None else str(round(avg, 1)) + "%"
    contrib_sign = "+" if contrib >= 0 else ""
    contrib_str = contrib_sign + str(round(contrib, 1)) + " נק'"

    st.markdown(
        "<div dir='rtl' style='text-align:right; border-top:3px solid " + head_color +
        "; background:rgba(120,120,120,0.06); border-radius:6px; padding:8px 10px; margin-bottom:4px;'>"
        "<div style='font-weight:800; font-size:15px; color:" + head_color + ";'>" + title + "</div>"
        "<div style='font-size:13px; color:#bbb; margin-top:3px;'>ממוצע " + avg_str
        + " · תרומה לנושא <b>" + contrib_str + "</b></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if data["stocks"]:
        st.markdown(returns_table_html(data["stocks"]), unsafe_allow_html=True)
    else:
        st.caption("אין מניות עם נתונים ברמה זו")


def render_theme_card(theme_name, idx):
    """כרטיס נושא מלא: כותרת עם תשואה משוקללת + expander עם פירוק שתי-עמודות."""
    wret = idx["weighted_return"]
    color = "#22c55e" if wret >= 0 else "#ef4444"
    sign = "+" if wret >= 0 else ""
    n_stocks = sum(len(idx["by_level"][lv]["stocks"]) for lv in (3, 2, 1))

    st.markdown(
        "<div dir='rtl' style='background:rgba(120,120,120,0.10); border-right:6px solid " + color +
        "; border-radius:10px; padding:12px 16px; margin-bottom:2px; text-align:right; "
        "display:flex; justify-content:space-between; align-items:center;'>"
        "<span style='font-weight:700; font-size:18px;'>" + theme_name + "</span>"
        "<span style='color:" + color + "; font-weight:800; font-size:20px;'>" + sign + str(round(wret, 1)) + "%</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("פירוק: שחקניות ישירות מול שרשרת אספקה  ·  " + str(n_stocks) + " מניות"):
        st.markdown(
            "<div dir='rtl' style='text-align:right; color:#999; font-size:13px; margin-bottom:10px;'>"
            "💡 <b>ליבה</b> = מוכרות את הרכיב עצמו · <b>מנוע צמיחה</b> ו<b>עקיפה</b> = שרשרת האספקה שנהנית. "
            "ה<b>תרומה</b> מראה כמה נקודות אחוז מתוך " + sign + str(round(wret, 1))
            + "% הגיעו מכל רמה — שלושתן יחד = התשואה הכוללת.</div>",
            unsafe_allow_html=True,
        )
        right_col, left_col = st.columns(2)
        with right_col:
            st.markdown("<div dir='rtl' style='text-align:center; font-weight:800; color:#22c55e; margin-bottom:6px;'>שחקניות ישירות</div>", unsafe_allow_html=True)
            exposure_level_block(3, idx["by_level"][3])
        with left_col:
            st.markdown("<div dir='rtl' style='text-align:center; font-weight:800; color:#3b82f6; margin-bottom:6px;'>שרשרת אספקה מאפשרת</div>", unsafe_allow_html=True)
            exposure_level_block(2, idx["by_level"][2])
            exposure_level_block(1, idx["by_level"][1])

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)


# לולאה על שלוש קבוצות העל. כל קבוצה מקבלת כותרת, ובתוכה הנושאים ממוינים מהחם לקר.
for group_name, group_themes in THEME_GROUPS.items():
    st.markdown(
        "<div dir='rtl' style='text-align:right; font-weight:800; font-size:22px; "
        "margin:18px 0 8px 0; padding-bottom:4px; border-bottom:2px solid #555;'>"
        + group_name + "</div>",
        unsafe_allow_html=True,
    )

    group_results = []
    for theme_name in group_themes:
        idx = compute_theme_index(theme_name, period)
        if idx["weighted_return"] is not None:
            group_results.append((idx["weighted_return"], theme_name, idx))

    group_results.sort(reverse=True)

    if len(group_results) == 0:
        st.caption("אין נתונים זמינים לקבוצה זו כרגע")
        continue

    for wret, theme_name, idx in group_results:
        render_theme_card(theme_name, idx)