import streamlit as st
import pandas as pd
import numpy as np  # 新增：用于生成更真实的模拟数据
from supabase import create_client
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts
from datetime import datetime, timedelta

# 页面基础设置
st.set_page_config(page_title="黄金价格可视化", layout="wide")  # 新增：优化页面布局
st.title("📊 Excel + Supabase + ECharts 可视化演示")

# ---------------------- 1. 本地Excel数据（增强版，解决文件不存在问题） ----------------------
@st.cache_data(ttl=86400)
def get_local_excel_data(file_path="gold_data.xlsx"):
    """
    加载本地Excel数据，文件不存在时生成更真实的模拟数据
    """
    try:
        # 尝试读取本地Excel文件
        df = pd.read_excel(file_path)
        df = df.fillna("")
        
        # 兼容不同的日期列名（date/日期）
        date_cols = [col for col in df.columns if col.lower() in ["date", "日期"]]
        if date_cols:
            df["date"] = pd.to_datetime(df[date_cols[0]])
            # 统一列名（确保后续代码能正常使用）
            df.rename(columns={
                "gold_price": "gold_price" if "gold_price" in df.columns else "黄金价格",
                "dxy": "dxy" if "dxy" in df.columns else "美元指数"
            }, inplace=True)
        st.info(f"✅ 成功读取本地Excel文件，共 {len(df)} 条数据")
        return df
    
    except FileNotFoundError as e:
        st.warning(f"⚠️ 本地Excel文件 '{file_path}' 不存在，自动生成模拟数据：{e}")
        # 生成更贴近真实市场的模拟数据（30天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=29)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 设置随机种子，保证数据可复现
        np.random.seed(42)
        # 黄金价格：基于2100波动，模拟真实涨跌
        base_gold = 2100
        gold_fluct = np.random.normal(0, 5, size=len(dates))  # 正态分布波动
        gold_prices = base_gold + np.cumsum(gold_fluct)
        
        # 美元指数：基于102波动，与黄金价格负相关
        base_dxy = 102
        dxy_fluct = -gold_fluct * 0.02  # 负相关
        dxy = base_dxy + np.cumsum(dxy_fluct)
        
        # 构建模拟DataFrame
        df = pd.DataFrame({
            "date": dates,
            "gold_price": np.round(gold_prices, 2),  # 保留2位小数
            "dxy": np.round(dxy, 2)
        })
        return df
    
    except Exception as e:
        st.error(f"❌ 读取数据时发生未知错误：{e}")
        # 生成极简备用数据，避免程序崩溃
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

# 数据预览（优化显示）
st.subheader("📋 数据预览")
st.dataframe(df.head(10), use_container_width=True)

# ---------------------- 2. ECharts可视化（增强鲁棒性） ----------------------
st.subheader("📈 黄金价格趋势（ECharts）")
# 安全检查：确保列存在
if "date" in df.columns and "gold_price" in df.columns:
    # 准备可视化数据
    x_data = [d.strftime("%Y-%m-%d") for d in df["date"]]
    y_data = df["gold_price"].tolist()

    # 创建折线图（优化样式）
    line_chart = (
        Line(init_opts=opts.InitOpts(width="100%", height="400px"))
        .add_xaxis(x_data)
        .add_yaxis(
            "黄金价格（USD/盎司）", 
            y_data,
            markpoint_opts=opts.MarkPointOpts(
                data=[opts.MarkPointItem(type_="max"), opts.MarkPointItem(type_="min")]
            ),
            markline_opts=opts.MarkLineOpts(
                data=[opts.MarkLineItem(type_="average")]
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="黄金价格30天趋势", subtitle="模拟数据/真实Excel数据"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
            yaxis_opts=opts.AxisOpts(min_="dataMin", max_="dataMax"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", formatter="{b}<br/>{a}: {c}"),
            legend_opts=opts.LegendOpts(pos_left="center"),
        )
    )
    st_pyecharts(line_chart, width="100%", height=400)
else:
    st.warning("⚠️ 数据格式异常，缺少日期或黄金价格列，无法生成图表")

# ---------------------- 3. Supabase连接（优化体验） ----------------------
with st.expander("🔧 连接Supabase（本地测试）", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        supabase_url = st.text_input("Supabase URL", placeholder="https://xxxx.supabase.co")
    with col2:
        supabase_key = st.text_input("Supabase Key", type="password", placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    
    if st.button("测试连接", type="primary"):
        if not supabase_url or not supabase_key:
            st.warning("⚠️ 请填写完整的URL和Key")
        else:
            try:
                supabase = create_client(supabase_url, supabase_key)
                # 测试连接是否真的可用
                response = supabase.table("nonexistent_table").select("*").limit(1).execute()
                st.success("✅ Supabase连接成功！")
            except Exception as e:
                st.error(f"❌ 连接失败：{str(e)[:200]}")  # 截断过长的错误信息

# ---------------------- 4. 数据下载（优化） ----------------------
st.subheader("💾 数据下载")
col1, col2 = st.columns(2)
with col1:
    # CSV下载
    csv_data = df.to_csv(index=False, encoding="utf-8-sig")  # 解决中文乱码
    st.download_button(
        label="📄 下载为CSV文件",
        data=csv_data,
        file_name=f"黄金价格数据_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
with col2:
    # Excel下载
    excel_data = df.to_excel(index=False, engine="openpyxl")
    import io
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button(
        label="📊 下载为Excel文件",
        data=buffer,
        file_name=f"黄金价格数据_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
