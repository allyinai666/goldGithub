import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import os

# 页面基础设置
st.set_page_config(page_title="黄金投资分析系统", layout="wide")
st.title("📈 黄金投资实时分析系统（免费云版）")

# 读取Supabase数据库配置（从Streamlit Secrets获取）
try:
    DB_HOST = st.secrets["DB_HOST"]
    DB_PORT = st.secrets["DB_PORT"]
    DB_USER = st.secrets["DB_USER"]
    DB_PASS = st.secrets["DB_PASSWORD"]
    DB_NAME = st.secrets["DB_NAME"]
    
    # 连接数据库
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
except Exception as e:
    st.error(f"数据库配置读取失败：{str(e)}")
    engine = None

# 封装数据读取函数（增加异常处理）
@st.cache_data(ttl=3600)  # 1小时缓存
def get_data(table_name):
    if engine is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY date DESC", engine)
        df["date"] = pd.to_datetime(df["date"])  # 统一日期格式
        return df
    except Exception as e:
        st.warning(f"读取{table_name}数据失败：{str(e)}")
        return pd.DataFrame()

# 读取各表数据
dxy_df = get_data("dxy_data")
gld_df = get_data("gld_holdings")
tips_df = get_data("tips_yield")

# 核心指标展示（增加空数据判断）
st.subheader("🔍 核心驱动指标")
col1, col2, col3 = st.columns(3)

with col1:
    if not dxy_df.empty and "dxy_value" in dxy_df.columns:
        latest_dxy = dxy_df.iloc[0]["dxy_value"]
        st.metric("美元指数（DXY）", f"{latest_dxy:.2f}")
    else:
        st.metric("美元指数（DXY）", "暂无数据")

with col2:
    if not gld_df.empty and "gld_holdings_oz" in gld_df.columns:
        latest_gld = gld_df.iloc[0]["gld_holdings_oz"]
        st.metric("GLD持仓（盎司）", latest_gld)
    else:
        st.metric("GLD持仓（盎司）", "暂无数据")

with col3:
    if not tips_df.empty and "y10_tips_yield" in tips_df.columns:
        latest_tips = tips_df.iloc[0]["y10_tips_yield"]
        st.metric("10年TIPS收益率（%）", f"{latest_tips:.2f}")
    else:
        st.metric("10年TIPS收益率（%）", "暂无数据")

# 趋势图展示（仅当有数据时绘制）
st.subheader("📊 指标趋势")
tab1, tab2 = st.tabs(["美元指数趋势", "实际利率趋势"])

with tab1:
    if not dxy_df.empty and "dxy_value" in dxy_df.columns:
        fig_dxy = px.line(dxy_df, x="date", y="dxy_value", title="美元指数变化")
        st.plotly_chart(fig_dxy, use_container_width=True)
    else:
        st.info("暂无美元指数数据，请等待GitHub Actions自动更新")

with tab2:
    if not tips_df.empty and "y10_tips_yield" in tips_df.columns:
        fig_tips = px.line(tips_df, x="date", y="y10_tips_yield", title="10年TIPS收益率变化")
        st.plotly_chart(fig_tips, use_container_width=True)
    else:
        st.info("暂无实际利率数据，请等待GitHub Actions自动更新")
