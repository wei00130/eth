# update_data.py
import ccxt
import pandas as pd
from datetime import datetime

def update_data(symbol="ETH/USDT:USDT", timeframe="1h", filename="ETH每小時Ｋ棒.csv"):
    exchange = ccxt.okx()

    # 讀取已存在的檔案（如果有）
    try:
        df_old = pd.read_csv(filename, parse_dates=["時間"])
        since = int(df_old["時間"].iloc[-1].timestamp() * 1000) + 1
    except FileNotFoundError:
        df_old = pd.DataFrame()
        since = None  # 從頭抓

    # 抓取最新資料
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=500)
    df_new = pd.DataFrame(ohlcv, columns=["時間", "開盤", "最高", "最低", "收盤", "成交量"])
    df_new["時間"] = pd.to_datetime(df_new["時間"], unit="ms")

    # 合併舊資料
    if not df_old.empty:
        df = pd.concat([df_old, df_new])
        df = df.drop_duplicates(subset=["時間"]).reset_index(drop=True)
    else:
        df = df_new

    df = df.iloc[:-1]

    # 存檔
    df.to_csv(filename, index=False)
    print(f"✅ 已更新資料到 {filename}, 最新時間：{df['時間'].iloc[-1]}")

    return df
