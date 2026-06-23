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

BENCHMARK = "SOXX"

SOXX_HOLDINGS = ["NVDA", "AVGO", "AMD", "TXN", "QCOM", "INTC", "MU", "ADI",
                 "MRVL", "NXPI", "MCHP", "ON", "TSM", "ASML", "AMAT", "LRCX", "KLAC"]

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


def clean_name(sector):
    if ". " in sector:
        return sector.split(". ", 1)[1]
    return sector


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

# ======================================================
# אזור SOXX — מבט-על של הסקטור
# ======================================================
soxx_close = get_history(BENCHMARK, period)

if soxx_close is None:
    st.markdown("### 🏆 SOXX — מדד סקטור השבבים")
    st.warning("לא הצלחנו למשוך נתוני SOXX כרגע")
else:
    soxx_change = soxx_close.iloc[-1] / soxx_close.iloc[0] * 100 - 100
    soxx_color = "#22c55e" if soxx_change >= 0 else "#ef4444"
    sign = "+" if soxx_change >= 0 else ""

    # כותרת עם התשואה בסוגריים, צבועה
    st.markdown(
        "<h3>🏆 SOXX — מדד סקטור השבבים "
        "(<span style='color:" + soxx_color + ";'>" + sign + str(round(soxx_change, 1)) + "%</span>)</h3>",
        unsafe_allow_html=True,
    )
    st.caption("תקופה: " + period)

   # גרף רחב וברור — מחיר אמיתי של המדד
    soxx_price = soxx_close.reset_index()
    soxx_price.columns = ["תאריך", "מחיר"]
    mini = alt.Chart(soxx_price).mark_area(
        line={"color": "#f59e0b", "strokeWidth": 2.5}, color="rgba(245,158,11,0.15)"
    ).encode(
        x=alt.X("תאריך:T", title=None),
        y=alt.Y("מחיר:Q", scale=alt.Scale(zero=False), title="מחיר ($)"),
    ).properties(height=240)
    st.altair_chart(mini, use_container_width=True)

    # מובילים וגוררים — 5 כל אחד, כותרת מעל הטבלה ומיושרת לימין
    holdings_pairs = get_changes(SOXX_HOLDINGS, period)
    holdings_pairs.sort(key=lambda x: x[1], reverse=True)

    if len(holdings_pairs) >= 2:
        top5 = holdings_pairs[:5]
        bottom5 = list(reversed(holdings_pairs[-5:]))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📈 העליות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(top5), unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📉 הירידות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(bottom5), unsafe_allow_html=True)

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
        for c in numbers:
            if c > 0:
                up = up + 1
        breadth = up / len(numbers)
        results.append((median, average, up, len(numbers), breadth, sector, pairs))
    results.sort(reverse=True)

# ---------- מפת חום ----------
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
    st.caption("ביצועי המניות מול חציון התחום ומול מדד SOXX — הכל מנורמל ל-100 בתחילת התקופה.")

    long_df = chart_data.reset_index()
    date_col = long_df.columns[0]
    long_df = long_df.melt(id_vars=[date_col], var_name="סדרה", value_name="ערך")

    # קו חציון התחום
    median_series = chart_data.median(axis=1)
    median_df = median_series.reset_index()
    median_df.columns = [date_col, "ערך"]
    median_df["סדרה"] = "חציון התחום"

    # קו SOXX
    soxx_close2 = get_history(BENCHMARK, period)

    # שכבת המניות (דקות)
    stocks_layer = alt.Chart(long_df).mark_line(opacity=0.5, strokeWidth=1.5).encode(
        x=alt.X(date_col + ":T", title=None),
        y=alt.Y("ערך:Q", scale=alt.Scale(zero=False), title="מנורמל ל-100"),
        color=alt.Color("סדרה:N", title="מניה"),
    )
    # קו החציון (לבן עבה)
    median_layer = alt.Chart(median_df).mark_line(strokeWidth=4, color="#ffffff").encode(
        x=date_col + ":T", y="ערך:Q",
    )
    layers = [stocks_layer, median_layer]
    # קו SOXX (כתום מקווקו עבה)
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
    st.markdown(returns_table_html(get_changes(value_chain[chosen], period)), unsafe_allow_html=True)