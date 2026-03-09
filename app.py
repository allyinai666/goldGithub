import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta

# 页面基础设置
st.set_page_config(page_title="黄金投资分析系统", layout="wide")
st.title("📈 黄金投资实时分析系统（免费云版）")

# 封装数据获取函数（直接从Yahoo Finance拉取，无数据库）
@st.cache_data(ttl=3600)  # 1小时缓存，避免频繁请求
def get_gold_data():
    # 1. 黄金现货价格（XAU/USD）
    gold = yf.Ticker("XAU=X")
    gold_hist = gold.history(period="30d")  # 近30天数据
    gold_hist.reset_index(inplace=True)
    gold_hist["Date"] = pd.to_datetime(gold_hist["Date"]).dt.date

    # 2. 美元指数（DXY）
    dxy = yf.Ticker("DX-Y.NYB")
    dxy_hist = dxy.history(period="30d")
    dxy_hist.reset_index(inplace=True)
    dxy_hist["Date"] = pd.to_datetime(dxy_hist["Date"]).dt.date

    # 3. 黄金ETF（GLD）持仓相关
    gld = yf.Ticker("GLD")
    gld_hist = gld.history(period="30d")
    gld_hist.reset_index(inplace=True)
    gld_hist["Date"] = pd.to_datetime(gld_hist["Date"]).dt.date

    # 4. 10年期TIPS（实际利率）
    tips = yf.Ticker("LTPZ")  # TIPS ETF替代直接收益率
    tips_hist = tips.history(period="30d")
    tips_hist.reset_index(inplace=True)
    tips_hist["Date"] = pd.to_datetime(tips_hist["Date"]).dt.date

    return {
        "gold": gold_hist,
        "dxy": dxy_hist,
        "gld": gld_hist,
        "tips": tips_hist
    }

# 获取数据（增加异常处理）
try:
    data = get_gold_data()
    gold_df = data["gold"]
    dxy_df = data["dxy"]
    gld_df = data["gld"]
    tips_df = data["tips"]
    st.success("✅ 数据获取成功！")
except Exception as e:
    st.error(f"❌ 数据获取失败：{str(e)}")
    st.stop()

# 核心指标展示（最新值）
st.subheader("🔍 核心驱动指标（实时）")
col1, col2, col3, col4 = st.columns(4)

with col1:
    latest_gold = gold_df.iloc[-1]["Close"]
    st.metric("黄金现货价格（USD/盎司）", f"{latest_gold:.2f}")

with col2:
    latest_dxy = dxy_df.iloc[-1]["Close"]
    st.metric("美元指数（DXY）", f"{latest_dxy:.2f}")

with col3:
    latest_gld = gld_df.iloc[-1]["Close"]
    st.metric("GLD ETF价格（USD）", f"{latest_gld:.2f}")

with col4:
    latest_tips = tips_df.iloc[-1]["Close"]
    st.metric("TIPS ETF价格（替代实际利率）", f"{latest_tips:.2f}")

# 趋势图展示
st.subheader("📊 近30天趋势")
tab1, tab2, tab3 = st.tabs(["黄金价格趋势", "美元指数趋势", "GLD ETF趋势"])

with tab1:
    fig_gold = px.line(gold_df, x="Date", y="Close", title="黄金现货价格（XAU/USD）")
    fig_gold.update_layout(xaxis_title="日期", yaxis_title="价格（USD/盎司）")
    st.plotly_chart(fig_gold, use_container_width=True)

with tab2:
    fig_dxy = px.line(dxy_df, x="Date", y="Close", title="美元指数（DXY）")
    fig_dxy.update_layout(xaxis_title="日期", yaxis_title="指数值")
    st.plotly_chart(fig_dxy, use_container_width=True)

with tab3:
    fig_gld = px.line(gld_df, x="Date", y="Close", title="黄金ETF（GLD）价格")
    fig_gld.update_layout(xaxis_title="日期", yaxis_title="价格（USD）")
    st.plotly_chart(fig_gld, use_container_width=True)

# 数据说明
st.info("""
📝 数据说明：
1. 数据来源：Yahoo Finance（免费公开API）；
2. 缓存机制：数据每小时更新一次，避免频繁请求；
3. 替代说明：TIPS收益率用LTPZ ETF价格替代（免费API无直接收益率数据）；
4. 更新频率：页面刷新即可获取最新数据。
""")
