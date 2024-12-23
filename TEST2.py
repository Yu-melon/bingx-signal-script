import os
import ccxt
import talib
import pandas_ta as ta
from datetime import datetime, timedelta
from telegram import Bot
import asyncio
import time

# 初始化 BingX
def initialize_bingx():
    try:
        exchange = ccxt.bingx({
            "apiKey": os.environ["BINGX_API_KEY"],  # 從環境變數中讀取 API Key
            "secret": os.environ["BINGX_SECRET"]    # 從環境變數中讀取 Secret Key
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
        df["RSI"] = talib.RSI(df["close"], timeperiod=7)
        df["EMA_short"] = talib.EMA(df["close"], timeperiod=5)
        df["EMA_long"] = talib.EMA(df["close"], timeperiod=15)
        df["MACD"], df["MACD_signal"], df["MACD_hist"] = talib.MACD(
            df["close"], fastperiod=12, slowperiod=26, signalperiod=9
        )
        df["SAR"] = talib.SAR(df["high"], df["low"], acceleration=0.02, maximum=0.2)
        return df
    except Exception as e:
        print(f"計算技術指標失敗: {e}")
        return None

# 信號生成邏輯
def generate_signal(row):
    try:
        if (row["RSI"] < 50 and
            row["EMA_short"] > row["EMA_long"] and
            row["MACD"] > row["MACD_signal"] and
            row["close"] > row["SAR"]):
            return "多方"
        elif (row["RSI"] > 50 and
              row["EMA_short"] < row["EMA_long"] and
              row["MACD"] < row["MACD_signal"] and
              row["close"] < row["SAR"]):
            return "空方"
        else:
            return None  # 無信號
    except Exception as e:
        print(f"生成信號失敗: {e}")
        return None

# 格式化結果
def format_results(results):
    message = "合約信號（所有結果）：\n\n"

    # 多方與空方分開處理
    for signal_type, entries in results.items():
        message += f"{signal_type} 信號:\n"
        for entry in entries:
            message += f"交易對: {entry['symbol']}\n"
        message += "------------------------\n"
    return message

# 發送訊息到 Telegram（異步）
async def send_to_telegram(message):
    TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]
    TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
    bot = Bot(token=TELEGRAM_API_TOKEN)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("訊息已成功發送至 Telegram。")
    except Exception as e:
        print(f"Telegram 傳送失敗: {e}")

# 計算下一個 1 小時更新的剩餘時間
def calculate_time_to_next_update():
    now = datetime.utcnow()
    next_update = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    remaining_time = (next_update - now).total_seconds()
    print(f"下一個 1 小時 K 線更新時間: {next_update} (UTC)")
    return remaining_time

# 主程式
def main():
    while True:
        print("開始運行程式...")
        exchange = initialize_bingx()
        if not exchange:
            print("BingX 初始化失敗，請檢查 API 配置或網路連線。")
            return

        symbols = [symbol for symbol in exchange.symbols if "/USDT" in symbol]
        contract_signals = {"多方": [], "空方": []}

        for symbol in symbols:
            market_type = exchange.market(symbol).get("type", "spot")
            if market_type != "swap":
                continue

            df = fetch_data(exchange, symbol, timeframe="1h")
            if df is not None and len(df) > 0:
                df = calculate_indicators(df)
                if df is not None:
                    latest = df.iloc[-1]
                    signal = generate_signal(latest)
                    if signal:
                        contract_signals[signal].append({"symbol": symbol})

        contract_message = format_results(contract_signals)
        asyncio.run(send_to_telegram(contract_message))
        time_to_next_update = calculate_time_to_next_update()
        print(f"程序將在 {int(time_to_next_update // 60)} 分鐘後再次運行...")
        time.sleep(time_to_next_update)

if __name__ == "__main__":
    main()
