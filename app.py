import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# =========================
# 頁面設定
# =========================
st.set_page_config(
    page_title="Lcc投資回測系統",
    page_icon="🤌",
    layout="wide"
)

# =========================
# 標題
# =========================
st.title("🤌美股定期定額回測系統")
st.markdown("### 輸入股票代碼，模擬長期定期定額投資績效")
st.markdown("by lcc_0811")

# =========================
# 快取資料
# =========================
@st.cache_data(ttl=3600)
def load_data(ticker, start, end):

    data = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )

    # 處理 MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data

# =========================
# Session State
# =========================
if "run_backtest" not in st.session_state:
    st.session_state.run_backtest = False

# =========================
# 側邊欄
# =========================
st.sidebar.header("⚙️投資參數設定")

ticker = st.sidebar.text_input(
    "股票代碼 (例如: QQQ, VOO, TSLA, NVDA)",
    value="QQQ"
).upper()

monthly_investment = st.sidebar.number_input(
    "每月投入金額 (USD)",
    min_value=10,
    value=100,
    step=10
)

start_date = st.sidebar.date_input(
    "開始日期",
    value=datetime(2020, 1, 1),
    min_value=datetime(1990, 1, 1),
    max_value=datetime.now()
)

end_date = st.sidebar.date_input(
    "結束日期",
    value=datetime.now(),
    min_value=datetime(1990, 1, 1),
    max_value=datetime.now()
)

# =========================
# 開始計算按鈕
# =========================
if st.sidebar.button("開始計算"):
    st.session_state.run_backtest = True

# =========================
# 主程式
# =========================
if st.session_state.run_backtest:

    # 日期檢查
    if start_date >= end_date:
        st.error("❌開始日期必須早於結束日期")
        st.stop()

    with st.spinner(f"正在下載 {ticker} 的歷史資料..."):

        try:

            # =========================
            # 公司資訊
            # =========================
            ticker_obj = yf.Ticker(ticker)

            try:
                company_name = ticker_obj.info.get("longName", ticker)
            except:
                company_name = ticker

            # =========================
            # 下載股價資料
            # =========================
            data = load_data(
                ticker,
                start_date,
                end_date
            )

            if data.empty:
                st.error("❌找不到資料，請檢查股票代碼")
                st.stop()

            st.subheader(f"📊 {company_name} ({ticker}) 回測報告")

            # =========================
            # 定期定額邏輯
            # =========================
            monthly_data = data.resample("MS").first()

            total_shares = 0
            total_invested = 0

            history = []

            for date, row in monthly_data.iterrows():

                price = row["Close"]

                if pd.isna(price):
                    continue

                # 當月買入股數
                shares_bought = monthly_investment / price

                total_shares += shares_bought
                total_invested += monthly_investment

                # 當前資產價值
                current_value = total_shares * price

                history.append({
                    "Date": date,
                    "Invested": total_invested,
                    "Value": current_value
                })

            # 建立 DataFrame
            df = pd.DataFrame(history)

            # =========================
            # KPI 計算
            # =========================
            final_value = df.iloc[-1]["Value"]

            final_invested = df.iloc[-1]["Invested"]

            profit = final_value - final_invested

            roi = (
                profit / final_invested
            ) * 100

            # CAGR
            years = (
                df.iloc[-1]["Date"] -
                df.iloc[0]["Date"]
            ).days / 365.25

            cagr = (
                (final_value / final_invested) ** (1 / years) - 1
            ) * 100

            # 最大回撤
            rolling_max = df["Value"].cummax()

            drawdown = (
                (df["Value"] - rolling_max)
                / rolling_max
            )

            max_drawdown = drawdown.min() * 100

            # =========================
            # KPI 顯示
            # =========================
            st.markdown("## 📌 投資績效摘要")

            col1, col2, col3, col4, col5 = st.columns(5)

            col1.metric(
                "累積投入",
                f"${final_invested:,.0f}"
            )

            col2.metric(
                "目前價值",
                f"${final_value:,.0f}"
            )

            col3.metric(
                "總獲利",
                f"${profit:,.0f}"
            )

            col4.metric(
                "總報酬率",
                f"{roi:.2f}%"
            )

            col5.metric(
                "CAGR",
                f"{cagr:.2f}%"
            )

            st.caption(
                f"📉 最大回撤 (Max Drawdown)：{max_drawdown:.2f}%"
            )

            # =========================
            # 投資曲線圖
            # =========================
            st.markdown("## 📈 投資績效走勢")

            fig = go.Figure()

            # 累積投入
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["Invested"],
                    name="累積投入",
                    line=dict(
                        color="gray",
                        dash="dash"
                    )
                )
            )

            # 投資價值
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["Value"],
                    name="投資價值",
                    fill="tozeroy",
                    line=dict(
                        color="#00CC96",
                        width=3
                    )
                )
            )

            fig.update_layout(
                template="plotly_white",
                hovermode="x unified",
                height=600,
                margin=dict(
                    l=0,
                    r=0,
                    t=30,
                    b=0
                ),
                legend=dict(
                    orientation="h",
                    y=1.02
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            # =========================
            # 表格區域
            # =========================
            st.markdown("## 📅 投資數據明細")

            display_mode = st.radio(
                "選擇顯示模式",
                ["逐年摘要", "逐月明細"],
                horizontal=True
            )

            # 複製資料
            table_df = df.copy()

            # 確保 Date 是 datetime
            table_df["Date"] = pd.to_datetime(
                table_df["Date"]
            )

            # 設定 index
            table_df = table_df.set_index("Date")

            # =========================
            # 逐年 / 逐月
            # =========================
            if display_mode == "逐年摘要":

                display_df = (
                    table_df
                    .resample("YE")
                    .last()
                    .copy()
                )

                display_df.index = (
                    display_df.index.strftime("%Y")
                )

            else:

                display_df = table_df.copy()

                display_df.index = (
                    display_df.index.strftime("%Y-%m")
                )

            # =========================
            # 計算欄位
            # =========================
            display_df["損益"] = (
                display_df["Value"]
                - display_df["Invested"]
            )

            display_df["報酬率"] = (
                display_df["損益"]
                / display_df["Invested"]
                * 100
            )

            # =========================
            # 格式化表格
            # =========================
            formatted_df = pd.DataFrame({

                "累積投入":
                display_df["Invested"].map(
                    "${:,.0f}".format
                ),

                "目前價值":
                display_df["Value"].map(
                    "${:,.0f}".format
                ),

                "損益":
                display_df["損益"].map(
                    "${:,.0f}".format
                ),

                "報酬率":
                display_df["報酬率"].map(
                    "{:.2f}%".format
                )

            })

            # 顯示表格
            st.dataframe(
                formatted_df,
                use_container_width=True
            )

            # =========================
            # CSV 下載
            # =========================
            csv = (
                display_df
                .to_csv()
                .encode("utf-8-sig")
            )

            st.download_button(
                label="📥 下載 CSV",
                data=csv,
                file_name=f"{ticker}_backtest.csv",
                mime="text/csv"
            )

        except Exception as e:

            st.error(f"❌ 發生錯誤：{e}")

# =========================
# 初始畫面
# =========================
else:

    st.info("👈 請在左側輸入參數後，點擊『開始計算』")