import streamlit as st
import pandas as pd
from supabase import create_client  # 修正导入（包名改了，导入方式不变）
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts
from datetime import datetime

# 页面基础设置
st.title("📊 Excel + Supabase + ECharts 可视化演示")

# ---------------------- 1. 本地Excel数据（绕开Supabase部署问题，先跑通） ----------------------
# 先读取本地Excel（避免Supabase依赖问题，确保可视化先跑通）
@st.cache_data(ttl=86400)
def get_local_excel_data():
    # 注意：Streamlit部署时，Excel文件要放在和app.py同目录下
    try:
        df = pd.read_excel("gold_data.xlsx")  # 替换为你的Excel文件名
        df = df.fillna("")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception as e:
        st.warning(f"⚠️ 本地Excel读取失败，使用模拟数据：{e}")
        # 生成模拟数据
        dates = pd.date_range(start="2024-01-01", periods=30)
        gold_prices = [2100 + i*2 for i in range(30)]
        dxy = [102 - i*0.1 for i in range(30)]
        return pd.DataFrame({
            "date": dates,
            "gold_price": gold_prices,
            "dxy": dxy
        })

# 获取数据
df = get_local_excel_data()
st.success("✅ 数据加载成功！")
st.subheader("📋 数据预览")
st.dataframe(df.head(10))

# ---------------------- 2. ECharts可视化（核心功能） ----------------------
st.subheader("📈 黄金价格趋势（ECharts）")
# 准备数据
x_data = [d.strftime("%Y-%m-%d") for d in df["date"]]
y_data = df["gold_price"].tolist()

# 创建折线图
line_chart = (
    Line()
    .add_xaxis(x_data)
    .add_yaxis("黄金价格（USD/盎司）", y_data)
    .set_global_opts(
        title_opts=opts.TitleOpts(title="黄金价格月度趋势"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
    )
)
st_pyecharts(line_chart, width="100%", height=400)

# ---------------------- 3. 可选：Supabase连接（本地测试用，部署时注释） ----------------------
with st.expander("🔧 连接Supabase（本地测试）"):
    supabase_url = st.text_input("Supabase URL")
    supabase_key = st.text_input("Supabase Key", type="password")
    if st.button("测试连接"):
        try:
            supabase = create_client(supabase_url, supabase_key)
            st.success("✅ Supabase连接成功！")
        except Exception as e:
            st.error(f"❌ 连接失败：{e}")

# 数据下载
st.subheader("💾 数据下载")
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="下载数据为CSV",
    data=csv_data,
    file_name="gold_data.csv",
    mime="text/csv"
)
