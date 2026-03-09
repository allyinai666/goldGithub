import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from pyecharts import options as opts
from pyecharts.charts import Line
from streamlit_echarts import st_pyecharts
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 页面基础设置
st.set_page_config(
    page_title="Supabase 多表数据可视化",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
    <style>
    .dataframe {font-size: 12px !important;}
    .stExpander {border: 1px solid #e6e6e6; border-radius: 8px; margin-bottom: 10px;}
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin: 5px 0;}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Supabase 多表数据可视化分析")

# ---------------------- 1. Supabase 连接配置（修复版） ----------------------
with st.sidebar:
    st.header("🔌 Supabase 配置")
    supabase_url = st.text_input("Supabase URL", placeholder="https://xxxx.supabase.co")
    supabase_key = st.text_input("Supabase Key", type="password", placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    
    # 测试连接按钮（修复版）
    if st.button("测试连接", type="primary"):
        if not supabase_url or not supabase_key:
            st.warning("请填写完整的URL和Key！")
        else:
            try:
                # 步骤1：创建客户端对象
                supabase = create_client(supabase_url, supabase_key)
                
                # 步骤2：尝试查询表元数据（通用验证）
                try:
                    # 查询数据库中的表列表（所有Supabase实例都支持）
                    tables_response = supabase.from_("tables").select("table_name").limit(5).execute()
                    st.success("✅ Supabase连接成功！")
                    st.session_state["supabase_conn"] = supabase
                    
                    # 显示检测到的表
                    table_names = [t['table_name'] for t in tables_response.data]
                    if table_names:
                        st.info(f"ℹ️ 检测到表：{', '.join(table_names)}")
                    else:
                        st.info("ℹ️ 连接成功，但未检测到数据表")
                        
                except Exception as meta_e:
                    # 元数据查询失败，尝试基础鉴权验证
                    try:
                        # 尝试查询任意表（仅验证鉴权，不关心表是否存在）
                        supabase.table("temp_table_12345").select("*").limit(1).execute()
                    except Exception as auth_e:
                        error_str = str(auth_e).lower()
                        # 区分错误类型
                        if "pgrst205" in error_str:
                            # PGRST205 = 表不存在，但鉴权成功
                            st.success("✅ Supabase连接成功！（测试表不存在）")
                            st.session_state["supabase_conn"] = supabase
                        elif "authentication" in error_str or "invalid" in error_str:
                            st.error("❌ 鉴权失败：URL或Key错误，请检查")
                        else:
                            st.error(f"❌ 连接异常：{str(auth_e)[:100]}")
                
            except Exception as e:
                st.error(f"❌ 连接失败：{str(e)[:150]}")

# ---------------------- 2. 数据加载函数 ----------------------
@st.cache_data(ttl=3600)
def load_supabase_table(supabase, table_name):
    """加载Supabase指定表的数据"""
    try:
        # 查询表中所有数据并按日期排序
        response = supabase.table(table_name).select("*").order("date", desc=False).execute()
        df = pd.DataFrame(response.data)
        
        # 数据预处理
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        df = df.fillna(0)  # 填充空值
        df = df.reset_index(drop=True)
        
        return df, True
    except Exception as e:
        error_msg = str(e).lower()
        if "pgrst205" in error_msg:
            st.warning(f"⚠️ 表 `{table_name}` 不存在，请检查表名是否正确")
        elif "authentication" in error_msg:
            st.warning(f"⚠️ 访问表 `{table_name}` 权限不足")
        else:
            st.warning(f"⚠️ 加载表 `{table_name}` 失败：{str(e)[:80]}")
        
        # 生成模拟数据
        dates = pd.date_range(start="2024-01-01", periods=30)
        if table_name == "gold_price":
            data = pd.DataFrame({
                "date": dates,
                "price": 2100 + np.cumsum(np.random.normal(0, 3, 30)),
                "open": 2100 + np.cumsum(np.random.normal(0, 2.5, 30)),
                "high": 2100 + np.cumsum(np.random.normal(0, 3.5, 30)),
                "low": 2100 + np.cumsum(np.random.normal(0, 2, 30))
            })
        elif table_name == "dxy_data":
            data = pd.DataFrame({
                "date": dates,
                "value": 102 + np.cumsum(np.random.normal(0, 0.1, 30))
            })
        elif table_name == "gld_holdings":
            data = pd.DataFrame({
                "date": dates,
                "holdings": 900 + np.cumsum(np.random.normal(0, 1, 30))
            })
        elif table_name == "tips_yield":
            data = pd.DataFrame({
                "date": dates,
                "yield": 1.5 + np.cumsum(np.random.normal(0, 0.05, 30))
            })
        return data, False

# ---------------------- 3. 数据加载与展示 ----------------------
if "supabase_conn" in st.session_state:
    supabase = st.session_state["supabase_conn"]
    
    # 定义要展示的表信息
    tables_config = {
        "gold_price": {"name": "黄金价格", "color": "#FFD700", "unit": "USD/盎司"},
        "dxy_data": {"name": "美元指数", "color": "#0052CC", "unit": ""},
        "gld_holdings": {"name": "GLD持仓量", "color": "#FF6B6B", "unit": "吨"},
        "tips_yield": {"name": "TIPS收益率", "color": "#4ECDC4", "unit": "%"},
    }
    
    # 加载所有表数据
    all_data = {}
    for table_name in tables_config.keys():
        df, is_real = load_supabase_table(supabase, table_name)
        all_data[table_name] = {"df": df, "is_real": is_real, "config": tables_config[table_name]}
    
    # ---------------------- 4. 数据概览 ----------------------
    st.subheader("📋 数据概览")
    col1, col2, col3, col4 = st.columns(4)
    
    # 黄金价格概览
    with col1:
        gold_df = all_data["gold_price"]["df"]
        latest_gold = gold_df["price"].iloc[-1] if "price" in gold_df.columns else 0
        change_gold = latest_gold - gold_df["price"].iloc[0] if len(gold_df) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h4>🎯 黄金价格</h4>
            <p style="font-size:20px; color:#FFD700; font-weight:bold;">{latest_gold:.2f}</p>
            <p style="color:{'green' if change_gold>0 else 'red'}">
                {"↑" if change_gold>0 else "↓"} {abs(change_gold):.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # 美元指数概览
    with col2:
        dxy_df = all_data["dxy_data"]["df"]
        latest_dxy = dxy_df["value"].iloc[-1] if "value" in dxy_df.columns else 0
        change_dxy = latest_dxy - dxy_df["value"].iloc[0] if len(dxy_df) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h4>💵 美元指数</h4>
            <p style="font-size:20px; color:#0052CC; font-weight:bold;">{latest_dxy:.2f}</p>
            <p style="color:{'green' if change_dxy>0 else 'red'}">
                {"↑" if change_dxy>0 else "↓"} {abs(change_dxy):.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # GLD持仓概览
    with col3:
        gld_df = all_data["gld_holdings"]["df"]
        latest_gld = gld_df["holdings"].iloc[-1] if "holdings" in gld_df.columns else 0
        change_gld = latest_gld - gld_df["holdings"].iloc[0] if len(gld_df) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h4>📦 GLD持仓</h4>
            <p style="font-size:20px; color:#FF6B6B; font-weight:bold;">{latest_gld:.1f}</p>
            <p style="color:{'green' if change_gld>0 else 'red'}">
                {"↑" if change_gld>0 else "↓"} {abs(change_gld):.1f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # TIPS收益率概览
    with col4:
        tips_df = all_data["tips_yield"]["df"]
        latest_tips = tips_df["yield"].iloc[-1] if "yield" in tips_df.columns else 0
        change_tips = latest_tips - tips_df["yield"].iloc[0] if len(tips_df) > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h4>📈 TIPS收益率</h4>
            <p style="font-size:20px; color:#4ECDC4; font-weight:bold;">{latest_tips:.2f}</p>
            <p style="color:{'green' if change_tips>0 else 'red'}">
                {"↑" if change_tips>0 else "↓"} {abs(change_tips):.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # ---------------------- 5. 详细数据与可视化 ----------------------
    # 5.1 黄金价格详情
    with st.expander("📊 黄金价格详情", expanded=True):
        gold_data = all_data["gold_price"]
        gold_df = gold_data["df"]
        
        # 提示是否使用模拟数据
        if not gold_data["is_real"]:
            st.info("ℹ️ 当前使用模拟数据，请确认Supabase中存在 `gold_price` 表")
        
        # 数据表格
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(gold_df, use_container_width=True, height=200)
        
        # 数据统计
        with col2:
            st.subheader("统计信息")
            if "price" in gold_df.columns:
                stats = {
                    "平均值": gold_df["price"].mean(),
                    "最大值": gold_df["price"].max(),
                    "最小值": gold_df["price"].min(),
                    "最新值": gold_df["price"].iloc[-1],
                    "数据条数": len(gold_df)
                }
                for key, value in stats.items():
                    st.write(f"**{key}**: {value:.2f}" if key != "数据条数" else f"**{key}**: {value}")
        
        # 黄金价格图表
        if "date" in gold_df.columns and "price" in gold_df.columns:
            x_data = [d.strftime("%Y-%m-%d") for d in gold_df["date"]]
            y_price = gold_df["price"].round(2).tolist()
            
            # 构建图表
            line = (
                Line(init_opts=opts.InitOpts(width="100%", height="400px"))
                .add_xaxis(x_data)
                .add_yaxis(
                    f"黄金价格 ({gold_data['config']['unit']})",
                    y_price,
                    itemstyle_opts=opts.ItemStyleOpts(color=gold_data["config"]["color"]),
                    markpoint_opts=opts.MarkPointOpts(
                        data=[opts.MarkPointItem(type_="max"), opts.MarkPointItem(type_="min")]
                    ),
                    markline_opts=opts.MarkLineOpts(
                        data=[opts.MarkLineItem(type_="average")]
                    )
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="黄金价格走势", subtitle="按日期排序"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                    tooltip_opts=opts.TooltipOpts(trigger="axis", formatter="{b}<br/>{a}: {c}"),
                    legend_opts=opts.LegendOpts(pos_top="5%")
                )
            )
            st_pyecharts(line, width="100%")
    
    # 5.2 其他表详情（折叠展示）
    for table_name in ["dxy_data", "gld_holdings", "tips_yield"]:
        with st.expander(f"📊 {tables_config[table_name]['name']}详情", expanded=False):
            table_data = all_data[table_name]
            df = table_data["df"]
            
            if not table_data["is_real"]:
                st.info(f"ℹ️ 当前使用模拟数据，请确认Supabase中存在 `{table_name}` 表")
            
            # 数据表格
            st.dataframe(df, use_container_width=True, height=200)
            
            # 可视化
            value_col = "value" if table_name == "dxy_data" else "holdings" if table_name == "gld_holdings" else "yield"
            if "date" in df.columns and value_col in df.columns:
                x_data = [d.strftime("%Y-%m-%d") for d in df["date"]]
                y_data = df[value_col].round(2).tolist()
                
                line = (
                    Line(init_opts=opts.InitOpts(width="100%", height="300px"))
                    .add_xaxis(x_data)
                    .add_yaxis(
                        f"{tables_config[table_name]['name']} ({tables_config[table_name]['unit']})",
                        y_data,
                        itemstyle_opts=opts.ItemStyleOpts(color=table_data["config"]["color"])
                    )
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title=f"{tables_config[table_name]['name']}走势"),
                        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                        tooltip_opts=opts.TooltipOpts(trigger="axis")
                    )
                )
                st_pyecharts(line, width="100%")
    
    # ---------------------- 6. 数据下载 ----------------------
    st.subheader("💾 数据下载")
    download_cols = st.columns(2)
    
    with download_cols[0]:
        st.markdown("#### 单表下载")
        table_to_download = st.selectbox("选择要下载的表", list(tables_config.keys()), format_func=lambda x: tables_config[x]["name"])
        df_to_download = all_data[table_to_download]["df"]
        
        # CSV下载
        csv_data = df_to_download.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label=f"下载{tables_config[table_to_download]['name']}为CSV",
            data=csv_data,
            file_name=f"{table_to_download}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with download_cols[1]:
        st.markdown("#### 全部数据下载")
        # 合并所有表数据
        merged_df = None
        for table_name, data in all_data.items():
            if merged_df is None:
                merged_df = data["df"].add_prefix(f"{table_name}_")
            else:
                temp_df = data["df"].add_prefix(f"{table_name}_")
                merged_df = pd.merge(
                    merged_df, 
                    temp_df, 
                    left_on=f"{merged_df.columns[0]}", 
                    right_on=f"{temp_df.columns[0]}", 
                    how="outer"
                )
        
        if merged_df is not None:
            # Excel下载
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for table_name, data in all_data.items():
                    data["df"].to_excel(writer, sheet_name=tables_config[table_name]["name"], index=False)
            
            buffer.seek(0)
            st.download_button(
                label="下载所有数据为Excel（多sheet）",
                data=buffer,
                file_name=f"supabase_all_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    # 未连接Supabase时的提示
    st.info("""
    📝 请先在左侧边栏配置Supabase连接信息：
    1. 输入Supabase URL（格式：https://xxxx.supabase.co）
    2. 输入Supabase Key（anon/public key）
    3. 点击"测试连接"按钮
    4. 连接成功后即可查看和分析4张表的数据
    """)
    
    # 显示模拟数据预览
    if st.button("查看模拟数据预览"):
        # 生成模拟数据预览
        st.subheader("模拟数据预览")
        
        # 黄金价格模拟数据
        dates = pd.date_range(start="2024-01-01", periods=10)
        gold_df = pd.DataFrame({
            "date": dates,
            "price": 2100 + np.cumsum(np.random.normal(0, 3, 10)),
            "open": 2100 + np.cumsum(np.random.normal(0, 2.5, 10)),
            "high": 2100 + np.cumsum(np.random.normal(0, 3.5, 10)),
            "low": 2100 + np.cumsum(np.random.normal(0, 2, 10))
        })
        
        st.dataframe(gold_df, use_container_width=True)
        st.info("这是模拟数据，连接Supabase后将显示真实数据")
