import os
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from telegram import Bot
import asyncio
from sar_calculator import calculate_sar  # 引用自建的 SAR 計算函數

# 初始化 BingX
def initialize_bingx():
    try:
        exchange = ccxt.bingx({
            "apiKey": os.getenv("BINGX_API_KEY"),
            "secret": os.getenv("BINGX_SECRET_KEY")
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

        # 使用自建 SAR 計算函數
        df["SAR"] = calculate_sar(df["high"].values, df["low"].values, acceleration=0.02, maximum=0.2)

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
            row["MACD"] > row["MACD_signal"] and
            row["close"] > row["SAR"]):  # SAR 支持多方
            return "多方", row["SAR"]
        # 空方信號條件
        elif (row["RSI"] > 50 and
              row["EMA_short"] < row["EMA_long"] and
              row["MACD"] < row["MACD_signal"] and
              row["close"] < row["SAR"]):  # SAR 支持空方
            return "空方", row["SAR"]
        # 其他信號（可擴展）
        else:
            return None, None  # 無信號
    except Exception as e:
        print(f"生成信號失敗: {e}")
        return None, None

# 格式化結果
def format_results(results):
    message = ""
    for signal_type, entries in results.items():
        message += f"\n{signal_type} 信號:\n"
        for entry in entries:
            message += f"{entry['交易對']} | SAR: {entry['SAR']:.4f}\n"
    return message

# 發送訊息到 Telegram（異步）
async def send_to_telegram(message):
    TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    bot = Bot(token=TELEGRAM_API_TOKEN)
    try:
        # 將訊息分段以避免超過 Telegram 的字符限制
        max_length = 4096  # Telegram 單條訊息最大字符數
        for i in range(0, len(message), max_length):
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message[i:i+max_length])
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
    contract_results = {"多方": [], "空方": []}

    for symbol in symbols:
        market_type = exchange.market(symbol).get("type", "spot")  # 確認交易對類型
        if market_type != "swap":  # 只處理合約
            continue

        # 抓取當前 1 小時 K 線數據
        df = fetch_data(exchange, symbol, timeframe="1h")
        if df is not None and len(df) > 0:
            # 計算技術指標
            df = calculate_indicators(df)
            if df is not None:
                latest = df.iloc[-1]
                signal, sar_value = generate_signal(latest)
                if signal:
                    contract_results[signal].append({"交易對": symbol, "SAR": sar_value})

    # 格式化結果
    contract_message = "合約信號（所有結果）：\n" + format_results(contract_results)

    # 發送到 Telegram
    asyncio.run(send_to_telegram(contract_message))

if __name__ == "__main__":
    main()
