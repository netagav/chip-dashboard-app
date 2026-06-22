import streamlit as st
import yfinance as yf
import statistics
import math
import pandas as pd
import altair as alt

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

HOT_THRESHOLD = 10
BROAD_THRESHOLD = 0.6
GAP_THRESHOLD = 15


# ---------- פונקציות ----------
@st.cache_data
def get_history(symbol, period):
    try:
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


# מסיר את מספר התחום מתחילת השם (למשל "5. ")
def clean_name(sector):
    if ". " in sector:
        return sector.split(". ", 1)[1]
    return sector


# טבלת תשואות כ-HTML: מניה מימין, תשואה משמאל (וצבועה)
def returns_table_html(pairs):
    sortable = []
    for symbol, change in pairs:
        sortable.append((change, symbol))
    sortable.sort(reverse=True)
    rows = ""
    for change, symbol in sortable:
        c = "#22c55e" if change >= 0 else "#ef4444"
        rows += ("<tr><td style='text-align:right; padding:4px 10px;'>" + symbol +
                 "</td><td style='text-align:left; padding:4px 10px; color:" + c +
                 "; font-weight:600;'>" + str(round(change, 1)) + "%</td></tr>")
    return ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
            "<tr><th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
            "<th style='text-align:left; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th></tr>"
            + rows + "</table>")


# ---------- ממשק ----------
st.title("💹 דשבורד שרשרת הערך של השבבים")

period = st.sidebar.selectbox("תקופת זמן:", ["5d", "1mo", "6mo", "1y", "5y"], index=1)
st.sidebar.caption("בחרי תקופה — כל הדשבורד יתעדכן")

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
        for c in numbers:
            if c > 0:
                up = up + 1
        breadth = up / len(numbers)
        results.append((median, average, up, len(numbers), breadth, sector, pairs))
    results.sort(reverse=True)

# ---------- מפת חום (כרטיסים צבעוניים ונפתחים) ----------
st.header("🗺️ מפת חום — דירוג התחומים")
st.caption("לחצי על תחום כדי לפתוח את המניות שלו")

rank = 1
for median, average, up, total, breadth, sector, pairs in results:
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
                    + "% · עלו " + str(up) + "/" + str(total) + "</div>")

    card = ("<details dir='rtl' style='background:" + bg + "; border-right:6px solid " + color +
            "; border-radius:10px; padding:10px 14px; margin-bottom:10px; text-align:right;'>"
            "<summary style='cursor:pointer; font-weight:700; font-size:17px; text-align:right;'>"
            + str(rank) + ". " + label + " — " + clean_name(sector) + "</summary>"
            + summary_line + driver + returns_table_html(pairs) + "</details>")
    st.markdown(card, unsafe_allow_html=True)
    rank = rank + 1

# ---------- צלילה לתחום ----------
st.divider()
st.header("🔍 צלילה לתחום")

sector_names = []
for r in results:
    sector_names.append(r[5])

chosen = st.selectbox("בחרי תחום:", sector_names, format_func=clean_name)

chart_data = build_chart(value_chain[chosen], period)
if chart_data.empty:
    st.warning("אין מספיק נתונים לתחום הזה")
else:
    st.caption("ביצועי המניות, מנורמלות ל-100 בתחילת התקופה.")
    long_df = chart_data.reset_index()
    date_col = long_df.columns[0]
    long_df = long_df.melt(id_vars=[date_col], var_name="מניה", value_name="ערך")
    line = alt.Chart(long_df).mark_line().encode(
        x=alt.X(date_col + ":T", title=None),
        y=alt.Y("ערך:Q", scale=alt.Scale(zero=False), title="מנורמל ל-100"),
        color=alt.Color("מניה:N", title="מניה"),
    )
    baseline = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(strokeDash=[4, 4], color="#888").encode(y="y:Q")
    st.altair_chart(line + baseline, use_container_width=True)

    st.subheader("טבלת תשואות")
    st.markdown(returns_table_html(get_changes(value_chain[chosen], period)), unsafe_allow_html=True)