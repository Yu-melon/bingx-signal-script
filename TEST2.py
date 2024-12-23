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
        api_key = os.getenv("BINGX_API_KEY")
        secret_key = os.getenv("BINGX_SECRET_KEY")
        print(f"讀取的 API Key: {api_key}, Secret Key: {secret_key[:4]}****")

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
        return df
    except Exception as e:
        print(f"計算技術指標失敗: {e}")
        return None

# 信號生成邏輯
def generate_signal(row):
    try:
        if row["RSI"] < 50 and row["EMA_short"] > row["EMA_long"] and row["MACD"] > row["MACD_signal"]:
            return "多方"
        elif row["RSI"] > 50 and row["EMA_short"] < row["EMA_long"] and row["MACD"] < row["MACD_signal"]:
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

# 格式化訊息
def format_message(results):
    message = "合約信號（所有結果）：\n\n"
    long_signals = "多方 信號:\n"
    short_signals = "空方 信號:\n"

    for result in results:
        symbol = result["symbol"]
        signal = result["signal"]
        row = result["row"]
        formatted = (f"交易對: {symbol}\n"
                     f"RSI: {row['RSI']:.2f}\n"
                     f"EMA 短期: {row['EMA_short']:.2f}\n"
                     f"EMA 長期: {row['EMA_long']:.2f}\n"
                     f"MACD: {row['MACD']:.2f}\n"
                     f"MACD 信號線: {row['MACD_signal']:.2f}\n"
                     f"\n收盤價: {row['close']:.4f}\n------------------------\n")

        if signal == "多方":
            long_signals += formatted
        elif signal == "空方":
            short_signals += formatted

    message += long_signals + "\n" + short_signals
    return message

# 主程式
def main():
    print("開始運行程式...")
    exchange = initialize_bingx()
    if not exchange:
        print("BingX 初始化失敗，請檢查 API 配置或網路連線。")
        return

    results = []
    symbols = [symbol for symbol in exchange.symbols if "/USDT" in symbol]
    for symbol in symbols:
        df = fetch_data(exchange, symbol)
        if df is not None:
            df = calculate_indicators(df)
            if df is not None:
                last_row = df.iloc[-1]
                signal = generate_signal(last_row)
                if signal:
                    results.append({"symbol": symbol, "signal": signal, "row": last_row})

    if results:
        message = format_message(results)
    else:
        message = "未生成任何有效信號。"

    asyncio.run(send_to_telegram(message))

if __name__ == "__main__":
    main()
