import yfinance as yf

# בודקים אילו חדשות מגיעות עבור מניה אחת
symbol = "NVDA"
ticker = yf.Ticker(symbol)
news = ticker.news

print("מספר ידיעות שהתקבלו:", len(news))
print("========================================")

# מדפיסים את הידיעה הראשונה כדי לראות איך היא בנויה
if len(news) > 0:
    print("דוגמה לידיעה אחת:")
    print(news[0])