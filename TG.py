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

        # 計算 SAR
        psar = ta.psar(df["high"], df["low"], df["close"], af=0.02, max_af=0.2)
        if "PSAR" in psar.columns:
            df["SAR"] = psar["PSAR"]
        elif "PSARr_0.02_0.2" in psar.columns:
            df["SAR"] = psar["PSARr_0.02_0.2"]
        else:
            raise ValueError("無法找到 PSAR 列，請檢查 pandas-ta 的版本和返回結果")

        # 取得最新 SAR 數值
        latest_sar = df.iloc[-1]["SAR"]
        latest_close = df.iloc[-1]["close"]

        return df, latest_close, latest_sar
    except Exception as e:
        print(f"計算技術指標失敗: {e}")
        return None, None, None

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

    for symbol in symbols:
        market_type = exchange.market(symbol).get("type", "spot")  # 確認交易對類型
        if market_type != "swap":  # 只處理合約
            continue

        # 抓取當前 1 小時 K 線數據
        df = fetch_data(exchange, symbol, timeframe="1h")
        if df is not None and len(df) > 0:
            # 計算技術指標
            df, latest_close, latest_sar = calculate_indicators(df)
            if df is not None:
                # 傳送 SAR 數值到 Telegram
                message = f"交易對: {symbol}\n最新收盤價: {latest_close}\n最新 SAR 值: {latest_sar}"
                asyncio.run(send_to_telegram(message))

if __name__ == "__main__":
    main()
