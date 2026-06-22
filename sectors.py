import yfinance as yf
import statistics
import math

# שרשרת הערך של סקטור השבבים
# כל תחום מוביל לרשימת המניות ששייכות אליו

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

period = "1mo"   # תקופה: 5d, 1mo, 6mo, 1y, 5y

HOT_THRESHOLD = 10     # חציון מעל זה נחשב חם
BROAD_THRESHOLD = 0.6  # לפחות כך אחוז מהמניות עלו = רחב
GAP_THRESHOLD = 15     # פער כזה בין ממוצע לחציון = מנוף ממניה בודדת

# פונקציה שמחזירה את אחוזי השינוי של כל המניות בתחום אחד
def get_changes(stocks):
    changes = []
    for symbol in stocks:
        try:
            data = yf.Ticker(symbol).history(period=period)
            if len(data) < 2:
                continue
            start_price = data["Close"].iloc[0]
            end_price = data["Close"].iloc[-1]
            change = (end_price - start_price) / start_price * 100
            if math.isnan(change):   # מדלגים על ערך חסר (nan)
                continue
            changes.append(change)
        except Exception:
            continue
    return changes

# פונקציה שקובעת תווית לתחום לפי המומנטום שלו
def label_sector(median, mean, up, total):
    breadth = up / total   # איזה חלק מהמניות עלו (0 עד 1)

    # חלש / מסוכן: חציון שלילי או רוב המניות יורדות
    if median <= 0 or breadth < 0.4:
        return "⚠️ חלש"

    # חם: חציון גבוה וגם רחב
    if median >= HOT_THRESHOLD and breadth >= BROAD_THRESHOLD:
        return "🔥 חם"

    # באמצע
    return "🟡 ניטרלי"

# סריקת כל התחומים
print("סורק את כל התחומים... זה ייקח כמה רגעים, רגע בבקשה")
print("")

results = []
for sector in value_chain:
    stocks = value_chain[sector]
    changes = get_changes(stocks)
    if len(changes) == 0:
        continue
    median = statistics.median(changes)
    average = sum(changes) / len(changes)
    up = 0
    for c in changes:
        if c > 0:
            up = up + 1
    results.append((median, average, up, len(changes), sector))

# מיון מהחם (חציון גבוה) לקר (חציון נמוך)
results.sort(reverse=True)

# הדפסת הדירוג
print("דירוג התחומים לפי מומנטום — מהחם לקר")
print("תקופה:", period)
print("================================================")
rank = 1
for median, average, up, total, sector in results:
    label = label_sector(median, average, up, total)
    caveat = ""
    if average - median >= GAP_THRESHOLD:
        caveat = "  📍 (מונע בעיקר ממניה בודדת)"
    print(rank, ")", label, "|", sector)
    print("    חציון:", round(median, 2), "% | ממוצע:", round(average, 2), "% | עלו:", up, "מתוך", total, caveat)
    print("")
    rank = rank + 1
