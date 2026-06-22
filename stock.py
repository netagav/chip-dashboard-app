import yfinance as yf

nvidia = yf.Ticker("NVDA")
price = nvidia.fast_info["last_price"]

print("מחיר המניה של NVIDIA הוא:")
print(price)