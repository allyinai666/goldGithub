# 安装依赖：requirements.txt需要包含这些包
# streamlit>=1.30.0
# pandas>=2.0.0
# supabase-py>=2.0.0
# pyecharts>=2.0.0
# streamlit-echarts>=0.4.0

import streamlit as st
import pandas as pd
from supabase import create_client, Client
from pyecharts import options as opts
from pyecharts.charts import Line, Bar, Pie
from streamlit_echarts import st_pyecharts

# ---------------------- 1. 配置Supabase连接 ----------------------
st.title("📊 Supabase + ECharts 数据可视化展示")

# 从Streamlit Secrets读取配置（生产环境），本地开发用直接赋值
url = st.secrets.get("SUPABASE_URL", "你的Project URL")
key = st.secrets.get("SUPABASE_KEY", "你的anon/public API Key")

# 连接Supabase
try:
    supabase: Client = create_client(url, key)
    st.success("✅ Supabase数据库连接成功！")
except Exception as e:
    st.error(f"❌ 数据库连接失败：{e}")
    st.stop()

# ---------------------- 2. 从Supabase读取数据 ----------------------
@st.cache_data(ttl=3600)  # 1小时缓存，减少数据库请求
def get_data_from_supabase():
    # 读取数据表（替换为你的表名：gold_data）
    response = supabase.table("gold_data").select("*").execute()
    # 转为DataFrame
    df = pd.DataFrame(response.data)
    # 数据清洗（根据你的Excel结构调整）
    # 示例：将日期列转为datetime格式
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

# 获取数据
try:
    df = get_data_from_supabase()
    st.subheader("📋 原始数据预览")
    st.dataframe(df.head(10))  # 展示前10行
    st.info(f"✅ 共读取 {len(df)} 条数据")
except Exception as e:
    st.error(f"❌ 读取数据失败：{e}")
    st.stop()

# ---------------------- 3. ECharts可视化 ----------------------
st.subheader("📈 数据可视化（ECharts）")

# 示例1：折线图（日期+黄金价格）
if "date" in df.columns and "gold_price" in df.columns:
    st.markdown("### 黄金价格趋势（折线图）")
    # 准备数据
    x_data = [d.strftime("%Y-%m-%d") for d in df["date"]]
    y_data = df["gold_price"].tolist()
    # 创建ECharts折线图
    line_chart = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis("黄金价格（USD/盎司）", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="黄金价格月度趋势"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
            yaxis_opts=opts.AxisOpts(name="价格"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
    )
    # 在Streamlit中展示
    st_pyecharts(line_chart, width="100%", height=400)

# 示例2：柱状图（日期+美元指数）
if "date" in df.columns and "dxy" in df.columns:
    st.markdown("### 美元指数变化（柱状图）")
    x_data = [d.strftime("%Y-%m-%d") for d in df["date"]]
    y_data = df["dxy"].tolist()
    bar_chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("美元指数（DXY）", y_data)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="美元指数月度变化"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
            yaxis_opts=opts.AxisOpts(name="指数值"),
        )
    )
    st_pyecharts(bar_chart, width="100%", height=400)

# 示例3：饼图（分类数据，如：交易类型占比）
if "trade_type" in df.columns:
    st.markdown("### 交易类型占比（饼图）")
    # 统计分类数量
    trade_count = df["trade_type"].value_counts()
    pie_chart = (
        Pie()
        .add("", list(zip(trade_count.index.tolist(), trade_count.values.tolist())))
        .set_global_opts(title_opts=opts.TitleOpts(title="交易类型分布"))
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
    )
    st_pyecharts(pie_chart, width="100%", height=400)

# ---------------------- 4. 数据下载 ----------------------
st.subheader("💾 数据下载")
# 将DataFrame转为CSV供下载
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="下载数据为CSV",
    data=csv_data,
    file_name="supabase_gold_data.csv",
    mime="text/csv",
)
