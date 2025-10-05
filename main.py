import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from zigzag import calculate_zigzag
from martin_strategy2 import martin_backtest
from update_daily import update_data


filename = "ETH每小時Ｋ棒.csv"
# 側邊欄按鈕
if st.sidebar.button("🔄 更新資料"):
    df = update_data(filename=filename)
    st.cache_data.clear()   # <<< 清除快取，確保下一次 load_data 會重新讀檔
    st.sidebar.success(f"✅ 資料已更新到 {df['時間'].iloc[-1]}")
else:
    try:
        df = pd.read_csv(filename, parse_dates=["時間"])
    except FileNotFoundError:
        st.error("⚠️ 尚未有資料，請先點擊『更新資料』")
        df = pd.DataFrame()

# 顯示最後一筆時間
if not df.empty:
    last_time = df["時間"].iloc[-1]
    st.metric("最後一筆K棒時間", last_time.strftime("%Y-%m-%d %H:%M:%S")+" UTC")

# --- 分頁標題 ---
st.set_page_config(page_title="波段分析", layout="wide")

# --- 主網頁標題 ---
st.title("📈 波段分析")

# --- 載入資料 ---
@st.cache_data
def load_data():
    return pd.read_csv("ETH每小時Ｋ棒.csv", parse_dates=["時間"])

df = load_data()

# --- 設定時間範圍 ---
time_min = df["時間"].min().to_pydatetime()
time_max = df["時間"].max().to_pydatetime()

# --- 快速時間範圍選擇 ---
quick_select = st.sidebar.radio(
    "快速選擇時間範圍",
    ("自訂", "近 7 天", "近 30 天", "近 90 天", "全區間")
)

if quick_select == "全區間":
    start_time = time_min
    end_time = time_max
elif quick_select == "近 7 天":
    end_time = time_max
    start_time = time_max - pd.Timedelta(days=7)
elif quick_select == "近 30 天":
    end_time = time_max
    start_time = time_max - pd.Timedelta(days=30)
elif quick_select == "近 90 天":
    end_time = time_max
    start_time = time_max - pd.Timedelta(days=90)
else:
    start_date = st.sidebar.date_input("開始日期", time_min.date(), min_value=time_min.date(), max_value=time_max.date())
    start_hour = st.sidebar.time_input("開始時間", time_min.time())
    end_date = st.sidebar.date_input("結束日期", time_max.date(), min_value=time_min.date(), max_value=time_max.date())
    end_hour = st.sidebar.time_input("結束時間", time_max.time())
    start_time = pd.Timestamp.combine(start_date, start_hour)
    end_time = pd.Timestamp.combine(end_date, end_hour)

# 驗證時間
if start_time > end_time:
    st.sidebar.error("❌ 開始時間不能晚於結束時間")
    st.stop()

# --- ZigZag 參數設定 ---
st.sidebar.header("🔧 ZigZag 參數設定")
threshold = st.sidebar.slider("Deviation (%)", 0.5, 10.0, 5.0, 0.5)
depth = st.sidebar.slider("Depth (Pivot 前後比較長度)", 1, 20, 10)
chart_height = st.sidebar.slider("調整圖表高度（單位：px）", 400, 1200, 550, step=50)

df_filtered = df[(df["時間"] >= pd.Timestamp(start_time)) & (df["時間"] <= pd.Timestamp(end_time))]

if len(df_filtered) < 2 * depth + 1:
    st.warning("⚠️ 資料太少，請選擇更長的時間範圍")
    st.stop()

# --- 建立分頁 ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 波段統計",
    "📈 上漲波段清單",
    "📉 下跌波段清單",
    "📈 K 線圖",
    "📈 上漲波段分佈圖",
    "📉 下跌波段分佈圖",
    "📒 馬丁策略回測 - 做多", 
    "📒 馬丁策略回測 - 做空",
    
])

# --- zigzag指標 ---回傳轉折點位置標籤、漲跌區段價差、最小最大漲跌幅
swing_points, segment_info, inc_max, inc_min, dec_min, dec_max = calculate_zigzag(df_filtered, threshold, depth)

# 📊 波段統計分頁
with tab1:
    df_stats = pd.DataFrame({
            "項目": ["最大", "最小"],
            "📈 上漲": [inc_max, inc_min],
            "📉 下跌": [dec_min, dec_max]
        }).set_index("項目")
    
    st.markdown("### 📊 ZigZag 波段統計（含波段編號）")
    st.dataframe(df_stats, width="stretch")

# 上漲波段清單分頁
with tab2:
    increases = [x for x in segment_info if x[0] == "📈 上漲"]
    if increases:
        df_inc = pd.DataFrame(increases, columns=["方向", "價差", "漲跌幅 (%)", "波段編號", "起始時間", "結束時間"])
        df_inc_sorted = df_inc.sort_values(by="漲跌幅 (%)", ascending=False)
        df_inc_sorted.set_index("方向", inplace=True)  # 方向設為索引
        st.markdown("### 📈 上漲波段清單（由漲跌幅由大到小排列）")
        st.dataframe(df_inc_sorted)
    else:
        st.info("沒有上漲波段資料")

# 下跌波段清單分頁
with tab3:
    decreases = [x for x in segment_info if x[0] == "📉 下跌"]
    if decreases:
        df_dec = pd.DataFrame(decreases, columns=["方向", "價差", "漲跌幅 (%)", "波段編號", "起始時間", "結束時間"])
        df_dec_sorted = df_dec.sort_values(by="漲跌幅 (%)")
        df_dec_sorted.set_index("方向", inplace=True)  # 方向設為索引
        st.markdown("### 📉 下跌波段清單（由跌幅由大到小排列）")
        st.dataframe(df_dec_sorted)
    else:
        st.info("沒有下跌波段資料")

# 📈 K 線圖分頁
with tab4:
    window_size = st.sidebar.slider("滑動視窗大小(根K棒)", 50, min(500, len(df_filtered)), 240, step=10)
    total_bars = len(df_filtered)
    if total_bars < window_size:
        st.warning(f"資料不足 {window_size} 根K棒，請選擇更長的時間區間")
        st.stop()

    start_idx = st.slider("滑動視窗起始K棒編號", 0, total_bars - window_size, 0, 1)
    end_idx = start_idx + window_size
    df_window = df_filtered.iloc[start_idx:end_idx].reset_index(drop=True)
    mask_in_window = (swing_points["時間"] >= df_window["時間"].iloc[0]) & (swing_points["時間"] <= df_window["時間"].iloc[-1])
    swing_points_window = swing_points[mask_in_window].reset_index(drop=True)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_window["時間"], open=df_window["開盤"], high=df_window["最高"], low=df_window["最低"], close=df_window["收盤"], name="K線"
    ))
    fig.add_trace(go.Scatter(
        x=swing_points_window["時間"], y=swing_points_window["pivot_price"],
        mode="markers+text", text=swing_points_window["label"], textposition=swing_points_window["text_position"],
        marker=dict(size=8, color="white", symbol="circle"),
        textfont=dict(color=swing_points_window["text_color"]),
        name="ZigZag轉折點"
    ))
    for i in range(1, len(swing_points_window)):
        fig.add_trace(go.Scatter(
            x=[swing_points_window.iloc[i - 1]["時間"], swing_points_window.iloc[i]["時間"]],
            y=[swing_points_window.iloc[i - 1]["pivot_price"], swing_points_window.iloc[i]["pivot_price"]],
            mode="lines", line=dict(color="orange", width=2), showlegend=False
        ))
    fig.update_layout(
        template="plotly_dark", height=chart_height,
        xaxis_rangeslider_visible=False,
        yaxis=dict(range=[df_window["最低"].min() * 0.985, df_window["最高"].max() * 1.015]),
        xaxis=dict(range=[df_window["時間"].iloc[0], df_window["時間"].iloc[-1]]),
        dragmode="zoom"
    )
    st.plotly_chart(fig, width="stretch")

# --- 新增 tab5: 上漲波段散佈圖 ---
with tab5:
    increases = [x for x in segment_info if x[0] == "📈 上漲"]
    if increases:
        df_inc = pd.DataFrame(increases, columns=["方向", "價差", "漲跌幅 (%)", "波段編號", "起始時間", "結束時間"])
        
        # 計算 80% 集中區間
        p10 = df_inc["漲跌幅 (%)"].quantile(0.05)
        p90 = df_inc["漲跌幅 (%)"].quantile(0.85)
        st.markdown(f"**📊 80% 的上漲波段漲幅落在 `{p10:.2f}%` ~ `{p90:.2f}%` 之間**")

        fig_inc = go.Figure()
        fig_inc.add_trace(go.Scatter(
            x=df_inc["波段編號"],
            y=df_inc["漲跌幅 (%)"],
            mode="markers",
            marker=dict(size=8, color="limegreen"),
            name="上漲波段"
        ))
        # 加淡色背景區間
        fig_inc.add_shape(
            type="rect",
            x0=min(df_inc["波段編號"]),
            x1=max(df_inc["波段編號"]),
            y0=p10,
            y1=p90,
            fillcolor="lightgreen",
            opacity=0.2,
            layer="below",
            line_width=0,
        )
        # 加上水平線
        fig_inc.add_hline(y=p10, line_dash="dot", line_color="orange", annotation_text="P10", annotation_position="bottom right")
        fig_inc.add_hline(y=p90, line_dash="dot", line_color="orange", annotation_text="P90", annotation_position="top right")

        fig_inc.update_layout(
            title="📈 上漲波段漲幅分佈",
            xaxis_title="波段編號",
            yaxis_title="漲跌幅 (%)",
            template="plotly_white",
            height=chart_height,
            yaxis=dict(dtick=5)  # 每 5% 一條格線
        )
        st.plotly_chart(fig_inc, width="stretch")
    else:
        st.info("沒有上漲波段資料")

# --- 新增 tab6: 下跌波段散佈圖 ---
with tab6:
    decreases = [x for x in segment_info if x[0] == "📉 下跌"]
    if decreases:
        df_dec = pd.DataFrame(decreases, columns=["方向", "價差", "漲跌幅 (%)", "波段編號", "起始時間", "結束時間"])
        
        # 計算 80% 集中區間
        p10 = df_dec["漲跌幅 (%)"].quantile(0.05)
        p90 = df_dec["漲跌幅 (%)"].quantile(0.85)
        st.markdown(f"**📊 80% 的下跌波段跌幅落在 `{p90:.2f}%` ~ `{p10:.2f}%` 之間**")

        fig_dec = go.Figure()
        fig_dec.add_trace(go.Scatter(
            x=df_dec["波段編號"],
            y=df_dec["漲跌幅 (%)"],
            mode="markers",
            marker=dict(size=8, color="red"),
            name="下跌波段"
        ))
        # 加淡色背景區間
        fig_dec.add_shape(
            type="rect",
            x0=min(df_dec["波段編號"]),
            x1=max(df_dec["波段編號"]),
            y0=p10,
            y1=p90,
            fillcolor="lightblue",
            opacity=0.2,
            layer="below",
            line_width=0,
        )
        # 加上水平線
        fig_dec.add_hline(y=p10, line_dash="dot", line_color="blue", annotation_text="P10", annotation_position="bottom right")
        fig_dec.add_hline(y=p90, line_dash="dot", line_color="blue", annotation_text="P90", annotation_position="top right")

        fig_dec.update_layout(
            title="📉 下跌波段跌幅分佈",
            xaxis_title="波段編號",
            yaxis_title="跌幅 (%)",
            template="plotly_white",
            height=chart_height,
            yaxis=dict(dtick=5)  # 每 5% 一條格線
        )
        st.plotly_chart(fig_dec, width="stretch")
    else:
        st.info("沒有下跌波段資料")

# --- 馬丁策略參數 ---
st.sidebar.header("💹 馬丁策略參數")
initial_balance = st.sidebar.number_input("初始金額 (USDT)", 1, 100000, 1000, step=1)
leverage = st.sidebar.number_input("槓桿倍數", 1, 125, 10, step=1)
add_pct = st.sidebar.number_input("跌多少/漲多少加碼 (%)", 0.5, 50.0, 2.0, step=0.1)
add_multiple = st.sidebar.number_input("加倉價差倍數", 0.1, 5.0, 1.0, step=0.1)
max_add_times = st.sidebar.number_input("最大加碼次數", 1, 20, 7)
add_amount = st.sidebar.number_input("首次加碼金額 (USDT)", 1, 100000, 100, step=1)
add_amount_multiple = st.sidebar.number_input("加碼金額倍數", 1.0, 5.0, 2.0, step=0.1)
take_profit_pct = st.sidebar.number_input("止盈 (%)", 0.5, 50.0, 1.0, step=0.1)
stop_loss_pct = st.sidebar.number_input("停損 (%)", 0.5, 100.0, 10.0, step=0.1)
direction = None

# ---馬丁多頭統計 ---
with tab7:
    prices_close = df_filtered["收盤"].values
    prices_high = df_filtered["最高"].values
    prices_low = df_filtered["最低"].values
    times = df_filtered["時間"].values
    df_trades_long, df_stats_long = martin_backtest(
        prices_close, prices_high, prices_low, times, direction=1, 
        initial_balance=initial_balance, add_amount=add_amount, 
        leverage=leverage, add_pct=add_pct,add_multiple=add_multiple, max_add_times=max_add_times, 
        add_amount_multiple=add_amount_multiple, take_profit_pct= take_profit_pct, stop_loss_pct=stop_loss_pct)
    
    st.subheader("📊 做多策略統計")
    st.dataframe(df_stats_long)
    st.dataframe(df_trades_long)

# ---馬丁空頭統計 ---
with tab8:
    prices_close = df_filtered["收盤"].values
    prices_high = df_filtered["最高"].values
    prices_low = df_filtered["最低"].values
    times = df_filtered["時間"].values

    df_trades_short, df_stats_short = martin_backtest(
         prices_close, prices_high, prices_low, times, direction=-1, 
        initial_balance=initial_balance, add_amount=add_amount, 
        leverage=leverage, add_pct=add_pct,add_multiple=add_multiple, max_add_times=max_add_times, 
        add_amount_multiple=add_amount_multiple, take_profit_pct= take_profit_pct, stop_loss_pct=stop_loss_pct)
    
    st.subheader("📊 做空策略統計")
    st.dataframe(df_stats_short)
    st.dataframe(df_trades_short)



