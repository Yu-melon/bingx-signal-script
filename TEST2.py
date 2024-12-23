import os
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from telegram import Bot
import asyncio

# 初始化 BingX
def initialize_bingx():
    try:
        # 讀取環境變數
        api_key = os.getenv("BINGX_API_KEY")
        secret_key = os.getenv("BINGX_SECRET_KEY")
        print(f"讀取的 API Key: {api_key}, Secret Key: {secret_key[:4]}****")

        # 初始化 BingX
        exchange = ccxt.bingx({
            "apiKey": api_key,
            "secret": secret_key,
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
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=50)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"抓取 {symbol} 數據失敗: {e}")
        return None

# 計算技術指標
def calculate_indicators(df):
    try:
        if len(df) < 50:
            print("數據不足，無法計算技術指標。")
            return None
        df["RSI"] = ta.rsi(df["close"], length=7)
        df["EMA_short"] = ta.ema(df["close"], length=5)
        df["EMA_long"] = ta.ema(df["close"], length=15)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["MACD"] = macd["MACD_12_26_9"]
        df["MACD_signal"] = macd["MACDs_12_26_9"]
        df["MACD_hist"] = macd["MACDh_12_26_9"]
        # SAR 指標部分已註解，因為 pandas_ta 不支持 SAR
        # df["SAR"] = ta.sar(df["high"], df["low"], acceleration=0.02, maximum=0.2)
        return df
    except Exception as e:
        print(f"計算技術指標失敗: {e}")
        return None

# 信號生成邏輯
def generate_signal(row):
    try:
        if (row["RSI"] < 50 and
            row["EMA_short"] > row["EMA_long"] and
            row["MACD"] > row["MACD_signal"]):  # SAR 已移除
            return "多方"
        elif (row["RSI"] > 50 and
              row["EMA_short"] < row["EMA_long"] and
              row["MACD"] < row["MACD_signal"]):  # SAR 已移除
            return "空方"
        else:
            return None
    except Exception as e:
        print(f"生成信號失敗: {e}")
        return None

# 發送訊息到 Telegram（異步）
async def send_to_telegram(message):
    TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    bot = Bot(token=TELEGRAM_API_TOKEN)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("訊息已成功發送至 Telegram。")
    except Exception as e:
        print(f"Telegram 傳送失敗: {e}")

# 主程式
def main():
    print("開始運行程式...")
    print("測試 Heroku 環境變數讀取...")
    print(f"BINGX_API_KEY: {os.getenv('BINGX_API_KEY')}")
    print(f"BINGX_SECRET_KEY: {os.getenv('BINGX_SECRET_KEY')[:4]}****")
    print(f"TELEGRAM_API_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')}")
    print(f"TELEGRAM_CHAT_ID: {os.getenv('TELEGRAM_CHAT_ID')}")

    # 初始化 BingX
    exchange = initialize_bingx()
    if not exchange:
        print("BingX 初始化失敗，請檢查 API 配置或網路連線。")
        return

    symbols = [symbol for symbol in exchange.symbols if "/USDT" in symbol]
    for symbol in symbols[:5]:  # 測試抓取前 5 個交易對
        df = fetch_data(exchange, symbol)
        if df is not None:
            df = calculate_indicators(df)
            if df is not None:
                print(f"成功處理 {symbol} 的技術指標！")
    
    # 測試 Telegram
    test_message = "測試訊息：BingX 初始化成功，Telegram 測試開始。"
    asyncio.run(send_to_telegram(test_message))

if __name__ == "__main__":
    main()
