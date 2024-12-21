from flask import Flask, jsonify
import os
import ccxt
import talib
import pandas as pd

app = Flask(__name__)

@app.route("/")
def run_script():
    # 在這裡調用您的主程式邏輯
    try:
        # 示例：打印一句話或運行主邏輯
        return jsonify({"message": "Hello, your script is running!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Vercel 預設需要使用 app 變數
if __name__ == "__main__":
    app.run(debug=True)
