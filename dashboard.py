import streamlit as st
import yfinance as yf
import statistics
import math
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

# אפשרויות התקופה. כל ערך הוא קוד פנימי שנפענח בפונקציית המשיכה.
PERIOD_OPTIONS = {
    "Online": "online",        # היום הנוכחי בזמן אמת (עם עיכוב קטן)
    "Last close": "lastclose", # יום המסחר השלם האחרון שנסגר
    "5D": "5d",
    "1M": "1mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
}


# ---------- פונקציות נתונים ----------
@st.cache_data(ttl=300)   # זיכרון קצר (5 דק') כי יש מצב אונליין
def get_history(symbol, period):
    try:
        if period == "online":
            # היום הנוכחי, נתונים תוך-יומיים בקפיצות 5 דקות
            data = yf.Ticker(symbol).history(period="1d", interval="5m")
        elif period == "lastclose":
            # שבוע אחרון, כדי לתפוס בוודאות את הסגירות השלמות האחרונות
            data = yf.Ticker(symbol).history(period="7d")
        else:
            data = yf.Ticker(symbol).history(period=period)
        close = data["Close"].dropna()
        if len(close) < 2:
            return None
        return close
    except Exception:
        return None


def get_change(symbol, period):
    close = get_history(symbol, period)
    if close is None:
        return None
    if period == "lastclose":
        # מדלגים על היום הנוכחי אם הוא עדיין רץ, ולוקחים את שתי הסגירות השלמות האחרונות
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
                 "</td><td style='text-align:left; padding:4px 10px; color:" + c +
                 "; font-weight:600;'>" + str(round(change, 1)) + "%</td></tr>")
    return ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
            "<tr><th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
            "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th></tr>"
            + rows + "</table>")


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

    soxx_price = soxx_close.reset_index()
    soxx_price.columns = ["תאריך", "מחיר"]
    if period == "lastclose":
        soxx_price = soxx_price.tail(3)   # מציג את הימים האחרונים בלבד
    mini = alt.Chart(soxx_price).mark_area(
        line={"color": "#f59e0b", "strokeWidth": 2.5}, color="rgba(245,158,11,0.15)"
    ).encode(
        x=alt.X("תאריך:T", title=None),
        y=alt.Y("מחיר:Q", scale=alt.Scale(zero=False), title="מחיר ($)"),
    ).properties(height=240)
    st.altair_chart(mini, use_container_width=True)

    holdings_pairs = get_changes(SOXX_HOLDINGS, period)
    holdings_pairs.sort(key=lambda x: x[1], reverse=True)

    if len(holdings_pairs) >= 2:
        top5 = holdings_pairs[:5]
        bottom5 = list(reversed(holdings_pairs[-5:]))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📈 העליות הגדולות</div>", unsafe_allow_html=True)
            # מהטוב ביותר כלפי מטה
            st.markdown(returns_table_html(top5, descending=True), unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📉 הירידות הגדולות</div>", unsafe_allow_html=True)
            # הגרועה ביותר למעלה
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
        any_news = False
        for symbol, change in pairs:
            news = get_news(symbol, limit=2)
            if len(news) == 0:
                continue
            any_news = True
            st.markdown("<div style='text-align:right; font-weight:700; margin-top:6px;'>" + symbol + "</div>", unsafe_allow_html=True)
            for item in news:
                date_part = ""
                if item["date"]:
                    date_part = " (" + item["date"] + ")"
                if item["link"]:
                    st.markdown("<div style='text-align:right;'>• <a href='" + item["link"] + "' target='_blank'>" + item["title"] + "</a>" + date_part + "</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='text-align:right;'>• " + item["title"] + date_part + "</div>", unsafe_allow_html=True)
        if not any_news:
            st.caption("אין חדשות זמינות כרגע לתחום הזה")

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