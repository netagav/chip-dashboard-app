import yfinance as yf
import matplotlib.pyplot as plt

# בחירת המניה והתקופה
symbol = "NVDA"
period = "6mo"   # אפשר לשנות: 1mo, 6mo, 1y, 5y

# משיכת הנתונים ההיסטוריים
stock = yf.Ticker(symbol)
data = stock.history(period=period)

# ציור הגרף
plt.plot(data.index, data["Close"])
plt.title(symbol + " - last " + period)
plt.xlabel("Date")
plt.ylabel("Price (USD)")
plt.grid(True)
plt.show()