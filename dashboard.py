import streamlit as st
import yfinance as yf
import statistics
import math
import os
import json
import pandas as pd
import altair as alt
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
</style>
""", unsafe_allow_html=True)

# ---------- שרשרת הערך ----------
value_chain = {
    "0. Raw Materials & Wafers (חומרי גלם ופרוסות סיליקון)": ["SHECY", "SUOPY"],
    "1. EDA & IP (תוכנות תכנון וקניין רוחני)": ["SNPS", "CDNS", "ARM"],
    "2. Fabless - Compute & AI (מעבדים ומאיצי בינה מלאכותית)": ["NVDA", "AMD", "AAPL", "QCOM", "MRVL"],
    "3. Fabless - Networking (תקשורת, סיבים וקישוריות)": ["AVGO", "ANET", "COHR", "LITE"],
    "4. IDM - Logic, Analog & Power (יצרנים משולבים)": ["INTC", "TXN", "ADI", "NXPI", "STM", "ON", "IFNNY", "RNECY"],
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

HOT_THRESHOLD = 10
BROAD_THRESHOLD = 0.6
GAP_THRESHOLD = 15
MOVE_ALERT = 2.0

AI_CACHE_TTL = {
    "online": 3600,
    "lastclose": 43200,
    "5d": 86400,
    "1mo": 259200,
    "6mo": 604800,
    "1y": 1209600,
    "5y": 1209600,
}

PERIOD_OPTIONS = {
    "Online": "online",
    "Last close": "lastclose",
    "5D": "5d",
    "1M": "1mo",
    "6M": "6mo",
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


# ---------- מפתח תקופה לזיכרון (משתנה כשנכנס פרק זמן חדש) ----------
def period_stamp(period_code):
    # קובע מתי נחשב "תקופה חדשה" לכל בחירה, כדי לדעת מתי לרענן ניתוחים שמורים
    now = datetime.now(timezone.utc)
    if period_code in ("online",):
        return now.strftime("%Y-%m-%d-%H")        # כל שעה
    if period_code in ("lastclose", "5d"):
        return now.strftime("%Y-%m-%d")           # כל יום
    if period_code in ("1mo",):
        return now.strftime("%Y-%W")              # כל שבוע
    # 6mo, 1y, 5y — כל חודש
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
def gemini_analyze_news(sector_name, titles_block):
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


def label_info(median, breadth):
    if median <= 0 or breadth < 0.4:
        return "⚠️ חלש", "#ef4444", "rgba(239,68,68,0.12)"
    if median >= HOT_THRESHOLD and breadth >= BROAD_THRESHOLD:
        return "🔥 חם", "#22c55e", "rgba(34,197,94,0.12)"
    return "🟡 ניטרלי", "#eab308", "rgba(234,179,8,0.12)"


def build_chart(stocks, period):
    chart_data = pd.DataFrame()
    for symbol in stocks:
        close = get_history(symbol, period)
        if close is None:
            continue
        chart_data[symbol] = close / close.iloc[0] * 100
    return chart_data.ffill()


def clean_name(sector):
    if ". " in sector:
        return sector.split(". ", 1)[1]
    return sector


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
        # סיכום מגמה עם זיכרון session state
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

        # מציג סיכום שמור אם קיים לתקופה הנוכחית
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
    mini = alt.Chart(soxx_price).mark_area(
        line={"color": "#f59e0b", "strokeWidth": 2.5}, color="rgba(245,158,11,0.15)"
    ).encode(
        x=alt.X("תאריך:T", title=None),
        y=alt.Y("מחיר:Q", scale=alt.Scale(zero=False), title="מחיר ($)"),
    ).properties(height=240)
    st.altair_chart(mini, use_container_width=True)

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
    results.sort(reverse=True)

# ---------- מפת חום ----------
st.header("🗺️ מפת חום — דירוג התחומים")
st.caption("לחצי על תחום כדי לפתוח את המניות והחדשות שלו")

rank = 1
for median, average, up, down, total, breadth, sector, pairs in results:
    label, color, bg = label_info(median, breadth)

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

    card = ("<div dir='rtl' style='background:" + bg + "; border-right:6px solid " + color +
            "; border-radius:10px; padding:10px 14px; margin-bottom:6px; text-align:right;'>"
            "<div style='font-weight:700; font-size:17px;'>"
            + str(rank) + ". " + label + " — " + clean_name(sector) + "</div>"
            + summary_line + driver + "</div>")
    st.markdown(card, unsafe_allow_html=True)

    with st.expander("פרטים, מניות וחדשות"):
        st.markdown(returns_table_html(pairs), unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-weight:700; margin-top:10px;'>📰 חדשות אחרונות בתחום</div>", unsafe_allow_html=True)

        sector_news = []
        for symbol, change in pairs:
            for item in get_news(symbol, limit=2):
                sector_news.append((symbol, item))

        if len(sector_news) == 0:
            st.caption("אין חדשות זמינות כרגע לתחום הזה")
        else:
            # מפתח זיכרון לניתוח החדשות של התחום, מתויג ביום
            news_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            news_key = "news_analysis_" + str(rank) + "_" + news_stamp

            if st.button("🧠 נתח חדשות", key="newsbtn_" + str(rank)):
                titles_block = ""
                for sym, item in sector_news:
                    titles_block += "- " + item["title"] + "\n"
                with st.spinner("מנתח חדשות עם Gemini..."):
                    st.session_state[news_key] = gemini_analyze_news(clean_name(sector), titles_block)

            analysis = st.session_state.get(news_key)

            if analysis and "overall" in analysis:
                ov = analysis["overall"]
                ov_color = {"positive": "#22c55e", "negative": "#ef4444"}.get(ov, "#eab308")
                ov_label = {"positive": "🟢 חיובי", "negative": "🔴 שלילי"}.get(ov, "⚪ ניטרלי")
                st.markdown(
                    "<div dir='rtl' style='text-align:right; color:" + ov_color +
                    "; font-weight:700; margin:6px 0;'>סנטימנט חדשות בתחום: " + ov_label +
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
                line = "<div dir='rtl' style='text-align:right; margin-top:6px;'>"
                line += "<b>" + sym + "</b> · "
                info = item_map.get(item["title"])
                if info:
                    s = info.get("sentiment", "neutral")
                    emoji = {"positive": "🟢", "negative": "🔴"}.get(s, "⚪")
                    risk = " ⚠️ סיכון" if s == "negative" else ""
                    line += emoji + risk + " "
                if item["link"]:
                    line += "<a href='" + item["link"] + "' target='_blank'>" + item["title"] + "</a>" + date_part
                else:
                    line += item["title"] + date_part
                if info and info.get("summary"):
                    line += "<div style='color:#aaa; font-size:13px;'>" + info["summary"] + "</div>"
                line += "</div>"
                st.markdown(line, unsafe_allow_html=True)

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
    st.caption("ביצועי המניות מול חציון התחום ומול מדד SOXX — הכל מנורמל ל-100 בתחילת התקופה.")

    long_df = chart_data.reset_index()
    date_col = long_df.columns[0]
    long_df = long_df.melt(id_vars=[date_col], var_name="סדרה", value_name="ערך")

    median_series = chart_data.median(axis=1)
    median_df = median_series.reset_index()
    median_df.columns = [date_col, "ערך"]

    soxx_close2 = get_history(BENCHMARK, period)

    stocks_layer = alt.Chart(long_df).mark_line(opacity=0.5, strokeWidth=1.5).encode(
        x=alt.X(date_col + ":T", title=None),
        y=alt.Y("ערך:Q", scale=alt.Scale(zero=False), title="מנורמל ל-100"),
        color=alt.Color("סדרה:N", title="מניה"),
    )
    median_layer = alt.Chart(median_df).mark_line(strokeWidth=4, color="#ffffff").encode(
        x=date_col + ":T", y="ערך:Q",
    )
    layers = [stocks_layer, median_layer]
    if soxx_close2 is not None:
        soxx_norm2 = (soxx_close2 / soxx_close2.iloc[0] * 100).reset_index()
        soxx_norm2.columns = [date_col, "ערך"]
        soxx_layer = alt.Chart(soxx_norm2).mark_line(strokeWidth=4, strokeDash=[6, 3], color="#f59e0b").encode(
            x=date_col + ":T", y="ערך:Q",
        )
        layers.append(soxx_layer)

    baseline = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(strokeDash=[2, 2], color="#888").encode(y="y:Q")
    layers.append(baseline)

    chart = layers[0]
    for lyr in layers[1:]:
        chart = chart + lyr
    st.altair_chart(chart, use_container_width=True)
    st.caption("⚪ קו לבן עבה = חציון התחום · 🟠 קו כתום מקווקו = מדד SOXX · קווים דקים = מניות בודדות")

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