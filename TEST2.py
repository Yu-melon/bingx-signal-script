import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from telegram import Bot
import asyncio

# 初始化 BingX
def initialize_bingx():
    try:
        exchange = ccxt.bingx({
            "apiKey": "YOUR_API_KEY",  # 替換為 BingX API Key
            "secret": "YOUR_SECRET_KEY"   # 替換為 BingX Secret
        })
        exchange.load_markets()
        print("BingX 交易所連線成功！")
        return exchange
    except Exception as e:
        print(f"初始化失敗: {e}")
        return None

# 抓取 K 線數據
def fetch_data(exchange, symbol, timeframe="1h"):
    try:
        print(f"正在抓取 {symbol} 的 {timeframe} K 線數據...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=50)  # 確保數據足夠
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"抓取 {symbol} 數據失敗: {e}")
        return None

# 計算技術指標
def calculate_indicators(df):
    try:
        if len(df) < 50:  # 確保數據足夠
            print("數據不足，無法計算技術指標。")
            return None

        df["RSI"] = ta.rsi(df["close"], length=7)
        df["EMA_short"] = ta.ema(df["close"], length=5)
        df["EMA_long"] = ta.ema(df["close"], length=15)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["MACD"] = macd["MACD_12_26_9"]
        df["MACD_signal"] = macd["MACDs_12_26_9"]
        df["MACD_hist"] = macd["MACDh_12_26_9"]
        return df
    except Exception as e:
        print(f"計算技術指標失敗: {e}")
        return None

# 信號生成邏輯
def generate_signal(row):
    try:
        # 多方信號條件
        if (row["RSI"] < 50 and
            row["EMA_short"] > row["EMA_long"] and
            row["MACD"] > row["MACD_signal"]):
            return "多方"
        # 空方信號條件
        elif (row["RSI"] > 50 and
              row["EMA_short"] < row["EMA_long"] and
              row["MACD"] < row["MACD_signal"]):
            return "空方"
        else:
            return None  # 無信號
    except Exception as e:
        print(f"生成信號失敗: {e}")
        return None

# 發送訊息到 Telegram（異步）
async def send_to_telegram(message):
    TELEGRAM_API_TOKEN = "YOUR_TELEGRAM_API_TOKEN"  # 替換為 Telegram Bot API Token
    TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"      # 替換為 Telegram Chat ID
    bot = Bot(token=TELEGRAM_API_TOKEN)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("訊息已成功發送至 Telegram。")
    except Exception as e:
        print(f"Telegram 傳送失敗: {e}")

# 主程式
def main():
    print("開始運行程式...")
    exchange = initialize_bingx()
    if not exchange:
        print("BingX 初始化失敗，請檢查 API 配置或網路連線。")
        return

    # 獲取所有交易對
    symbols = [symbol for symbol in exchange.symbols if "/USDT" in symbol]

    # 分類結果
    results = {"多方": [], "空方": []}

    for symbol in symbols:
        try:
            # 抓取當前 1 小時 K 線數據
            df = fetch_data(exchange, symbol, timeframe="1h")
            if df is not None:
                df = calculate_indicators(df)
                if df is not None:
                    latest = df.iloc[-1]
                    signal = generate_signal(latest)
                    if signal:
                        results[signal].append(f"交易對: {symbol}, 收盤價: {latest['close']}, RSI: {latest['RSI']}")
        except Exception as e:
            print(f"處理 {symbol} 時出現錯誤: {e}")

    # 格式化結果
    message = "合約信號結果：\n"
    for key, value in results.items():
        message += f"\n{key} 信號:\n" + "\n".join(value)

    # 發送到 Telegram
    asyncio.run(send_to_telegram(message))

if __name__ == "__main__":
    main()
