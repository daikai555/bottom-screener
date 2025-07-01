import streamlit as st
import pandas as pd
import yfinance as yf
import ta
from datetime import date, timedelta
from pathlib import Path

# ---------- パラメータ ----------
MA25_BIAS_MAX = st.sidebar.number_input("25日線乖離率 ≤", -50.0, 0.0, -10.0, 1.0)
RSI_MAX        = st.sidebar.number_input("RSI14 ≤", 0, 100, 30, 5)
VOL_RATIO_MIN  = st.sidebar.number_input("出来高倍率 ≥", 1.0, 10.0, 2.0, 0.5)
# -------------------------------

@st.cache_data(show_spinner=False)
def load_tickers():
    url = "https://raw.githubusercontent.com/orangain/jpstocks/master/all/all_tickers.txt"
    return pd.read_csv(url, header=None)[0].tolist()[:800]  # 800銘柄で速度確保

@st.cache_data(show_spinner=True)
def scan():
    tickers = load_tickers()
    start   = date.today() - timedelta(days=130)
    hist    = yf.download(tickers, start=start, interval="1d",
                          progress=False, group_by="ticker")
    data = []
    for code in tickers:
        df = hist[code].dropna()
        if len(df) < 30:
            continue
        df["ma25"]      = df["Close"].rolling(25).mean()
        df["bias"]      = (df["Close"]/df["ma25"]-1)*100
        df["rsi"]       = ta.momentum.rsi(df["Close"], window=14)
        df["vol_mean5"] = df["Volume"].rolling(5).mean()
        df["vol_ratio"] = df["Volume"]/df["vol_mean5"]
        today, yest = df.iloc[-1], df.iloc[-2]
        if (today["bias"] <= MA25_BIAS_MAX and today["rsi"] <= RSI_MAX
            and today["Close"] > yest["Close"]
            and today["vol_ratio"] >= VOL_RATIO_MIN):
            data.append([code.replace(".T",""), today["Close"], int(today["Volume"]),
                         round(today["bias"],1), round(today["rsi"],1),
                         round(today["vol_ratio"],1)])
    return pd.DataFrame(data,
            columns=["コード","終値","出来高","25日乖離%","RSI14","出来高比"])

st.title("底打ち候補スクリーナー（Streamlit版）")
if st.button("抽出を実行"):
    st.info("スキャン中…1〜2分程度お待ちください")
    df = scan()
    st.success(f"抽出完了: {len(df)} 銘柄")
    st.dataframe(df, use_container_width=True)
    if len(df):
        csv_path = Path("bottom_candidates.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        st.download_button("結果をCSVダウンロード",
                           csv_path.read_bytes(), file_name=csv_path.name)
else:
    st.write("左サイドバーで条件を調整し、[抽出を実行] をクリックしてください。")
