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

# ====================== 导入独立配置文件 ======================
from config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    TABLES_CONFIG,
    PAGE_CONFIG,
    SIMULATE_DATA_BASE
)

# ====================== 页面基础设置（从配置读取） ======================
st.set_page_config(
    page_title=PAGE_CONFIG["page_title"],
    layout=PAGE_CONFIG["layout"],
    initial_sidebar_state=PAGE_CONFIG["initial_sidebar_state"]
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

# ====================== 初始化Supabase连接（移除缓存，避免返回客户端对象） ======================
def init_supabase_connection():
    """
    初始化Supabase连接（移除@st.cache_data装饰，避免序列化错误）
    返回：连接状态、提示信息（不返回客户端对象）
    """
    try:
        # 仅验证连接，不返回客户端对象
        supabase_temp = create_client(SUPABASE_URL, SUPABASE_KEY)
        # 验证连接（兼容测试表不存在的情况）
        supabase_temp.table("temp_test_table_12345").select("*").limit(1).execute()
        return True, "✅ Supabase连接成功！（测试表不存在）"
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid" in error_str:
            return False, "❌ 鉴权失败：URL或Key错误，请检查Secrets配置"
        elif "pgrst205" in error_str:
            return True, "✅ Supabase连接成功！"
        else:
            return False, f"❌ 连接失败：{str(e)[:100]}"

# 自动初始化连接（仅获取状态和提示，不获取客户端对象）
conn_success, conn_msg = init_supabase_connection()
st.sidebar.header("🔌 连接状态")
st.sidebar.info(conn_msg)

# ====================== 数据加载函数（适配建表SQL的字段类型） ======================
@st.cache_data(ttl=3600)
def load_supabase_table(table_name):
    """
    加载Supabase表数据（内部创建客户端对象，仅缓存数据，不缓存客户端）
    """
    # 从配置读取当前表的字段信息
    config = TABLES_CONFIG[table_name]
    date_col = config["date_col"]
    value_cols = config["value_cols"]
    
    try:
        # 1. 内部创建连接（每次缓存命中时重新创建，避免序列化问题）
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 2. 查询表结构和数据
        # 查询所有字段
        columns_response = supabase.from_("columns").select("column_name").eq("table_name", table_name).execute()
        table_columns = [col["column_name"] for col in columns_response.data]
        st.sidebar.info(f"📋 表 {table_name} 字段：{table_columns}")
        
        # 3. 字段兼容性处理
        # 日期字段处理（兼容text/date/timestamp类型）
        actual_date_col = date_col if date_col in table_columns else None
        if not actual_date_col:
            raise Exception(f"未找到日期字段：{date_col}")
        
        # 数值字段处理
        actual_value_col = None
        for col in value_cols:
            if col in table_columns:
                actual_value_col = col
                break
        if not actual_value_col:
            raise Exception(f"未找到数值字段：{value_cols}")
        
        # 4. 查询数据并处理类型
        response = supabase.table(table_name).select("*").order(actual_date_col, desc=False).execute()
        df = pd.DataFrame(response.data)
        
        # 5. 数据清洗（适配建表SQL的字段类型）
        # 日期字段转换（兼容text/date/timestamp）
        if df[actual_date_col].dtype == "object":  # gold_date是text类型
            df["date"] = pd.to_datetime(df[actual_date_col], errors="coerce")
        else:  # date是date/timestamp类型
            df["date"] = pd.to_datetime(df[actual_date_col])
        
        # 数值字段转换（兼容text/double precision）
        df["value"] = pd.to_numeric(df[actual_value_col], errors="coerce").fillna(0)
        
        # 过滤无效数据
        df = df.dropna(subset=["date"]).reset_index(drop=True)
        
        return df, True, f"✅ 加载成功（{len(df)} 条数据）"
    
    except Exception as e:
        st.warning(f"⚠️ 加载表 {table_name} 失败：{str(e)[:100]}")
        # 生成模拟数据（从配置读取基础值）
        dates = pd.date_range(start="2024-01-01", periods=30)
        base_value = SIMULATE_DATA_BASE.get(table_name, 100)
        
        df = pd.DataFrame({
            "date": dates,
            "value": base_value + np.cumsum(np.random.normal(0, 1, 30))
        })
        return df, False, f"⚠️ 使用{config['display_name']}模拟数据"

# ====================== 加载所有表数据 ======================
all_data = {}
if conn_success:
    for table_name in TABLES_CONFIG.keys():
        df, is_real, msg = load_supabase_table(table_name)
        st.sidebar.text(f"{TABLES_CONFIG[table_name]['display_name']}：{msg}")
        all_data[table_name] = {
            "df": df,
            "is_real": is_real,
            "display_name": TABLES_CONFIG[table_name]["display_name"],
            "color": TABLES_CONFIG[table_name]["color"],
            "unit": TABLES_CONFIG[table_name]["unit"]
        }
else:
    # 连接失败时生成所有模拟数据
    st.warning("⚠️ Supabase连接失败，全部使用模拟数据")
    for table_name in TABLES_CONFIG.keys():
        dates = pd.date_range(start="2024-01-01", periods=30)
        base_value = SIMULATE_DATA_BASE.get(table_name, 100)
        
        df = pd.DataFrame({
            "date": dates,
            "value": base_value + np.cumsum(np.random.normal(0, 1, 30))
        })
        all_data[table_name] = {
            "df": df,
            "is_real": False,
            "display_name": TABLES_CONFIG[table_name]["display_name"],
            "color": TABLES_CONFIG[table_name]["color"],
            "unit": TABLES_CONFIG[table_name]["unit"]
        }

# ====================== 数据概览（无KeyError） ======================
st.subheader("📋 数据概览")
col1, col2, col3, col4 = st.columns(4)

# GLD持仓量
with col1:
    gld_df = all_data["gld_holdings"]["df"]
    latest_gld = gld_df["value"].iloc[-1] if len(gld_df) > 0 else 0
    change_gld = latest_gld - gld_df["value"].iloc[0] if len(gld_df) > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <h4>📦 {all_data['gld_holdings']['display_name']}</h4>
        <p style="font-size:18px; color:{all_data['gld_holdings']['color']}; font-weight:bold;">{latest_gld:,.0f}</p>
        <p style="color:{'green' if change_gld>0 else 'red'}">
            {"↑" if change_gld>0 else "↓"} {abs(change_gld):,.0f} {all_data['gld_holdings']['unit']}
        </p>
    </div>
    """, unsafe_allow_html=True)

# TIPS收益率
with col2:
    tips_df = all_data["tips_yield"]["df"]
    latest_tips = tips_df["value"].iloc[-1] if len(tips_df) > 0 else 0
    change_tips = latest_tips - tips_df["value"].iloc[0] if len(tips_df) > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <h4>📈 {all_data['tips_yield']['display_name']}</h4>
        <p style="font-size:18px; color:{all_data['tips_yield']['color']}; font-weight:bold;">{latest_tips:.2f}</p>
        <p style="color:{'green' if change_tips>0 else 'red'}">
            {"↑" if change_tips>0 else "↓"} {abs(change_tips):.2f} {all_data['tips_yield']['unit']}
        </p>
    </div>
    """, unsafe_allow_html=True)

# 美元指数
with col3:
    dxy_df = all_data["dxy_data"]["df"]
    latest_dxy = dxy_df["value"].iloc[-1] if len(dxy_df) > 0 else 0
    change_dxy = latest_dxy - dxy_df["value"].iloc[0] if len(dxy_df) > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <h4>💵 {all_data['dxy_data']['display_name']}</h4>
        <p style="font-size:18px; color:{all_data['dxy_data']['color']}; font-weight:bold;">{latest_dxy:.2f}</p>
        <p style="color:{'green' if change_dxy>0 else 'red'}">
            {"↑" if change_dxy>0 else "↓"} {abs(change_dxy):.2f}
        </p>
    </div>
    """, unsafe_allow_html=True)

# 黄金价格
with col4:
    gold_df = all_data["gold_price"]["df"]
    latest_gold = gold_df["value"].iloc[-1] if len(gold_df) > 0 else 0
    change_gold = latest_gold - gold_df["value"].iloc[0] if len(gold_df) > 0 else 0
    st.markdown(f"""
    <div class="metric-card">
        <h4>🎯 {all_data['gold_price']['display_name']}</h4>
        <p style="font-size:18px; color:{all_data['gold_price']['color']}; font-weight:bold;">{latest_gold:.2f}</p>
        <p style="color:{'green' if change_gold>0 else 'red'}">
            {"↑" if change_gold>0 else "↓"} {abs(change_gold):.2f} {all_data['gold_price']['unit']}
        </p>
    </div>
    """, unsafe_allow_html=True)

# ====================== 详细数据与可视化 ======================
for table_name, data in all_data.items():
    with st.expander(f"📊 {data['display_name']}详情", expanded=(table_name == "gold_price")):
        df = data["df"]
        
        # 提示模拟数据
        if not data["is_real"]:
            st.info(f"ℹ️ 当前使用{data['display_name']}模拟数据（真实数据加载失败）")
        
        # 数据表格 + 统计
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df[["date", "value"]].rename(columns={"value": data["display_name"]}), 
                         use_container_width=True, height=200)
        with col2:
            st.subheader("统计信息")
            if len(df) > 0:
                stats = {
                    "平均值": df["value"].mean(),
                    "最大值": df["value"].max(),
                    "最小值": df["value"].min(),
                    "最新值": df["value"].iloc[-1],
                    "数据条数": len(df)
                }
                for key, value in stats.items():
                    if key == "数据条数":
                        st.write(f"**{key}**: {value}")
                    elif table_name == "gld_holdings":
                        st.write(f"**{key}**: {value:,.0f}")
                    else:
                        st.write(f"**{key}**: {value:.2f}")
        
        # 趋势图表
        if len(df) > 0 and "date" in df.columns and "value" in df.columns:
            x_data = [d.strftime("%Y-%m-%d") for d in df["date"]]
            y_data = df["value"].round(2).tolist()
            
            line = (
                Line(init_opts=opts.InitOpts(width="100%", height="400px"))
                .add_xaxis(x_data)
                .add_yaxis(
                    f"{data['display_name']} ({data['unit']})",
                    y_data,
                    itemstyle_opts=opts.ItemStyleOpts(color=data["color"]),
                    markpoint_opts=opts.MarkPointOpts(
                        data=[opts.MarkPointItem(type_="max"), opts.MarkPointItem(type_="min")]
                    ),
                    markline_opts=opts.MarkLineOpts(
                        data=[opts.MarkLineItem(type_="average")]
                    )
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title=f"{data['display_name']}30天走势"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                    tooltip_opts=opts.TooltipOpts(trigger="axis", formatter="{b}<br/>{a}: {c}"),
                    legend_opts=opts.LegendOpts(pos_top="5%")
                )
            )
            st_pyecharts(line, width="100%")

# ====================== 数据下载 ======================
st.subheader("💾 数据下载")
download_cols = st.columns(2)

with download_cols[0]:
    st.markdown("#### 单表下载")
    table_to_download = st.selectbox(
        "选择要下载的表", 
        list(all_data.keys()), 
        format_func=lambda x: all_data[x]["display_name"]
    )
    df_to_download = all_data[table_to_download]["df"][["date", "value"]].rename(
        columns={"value": all_data[table_to_download]["display_name"]}
    )
    
    # CSV下载
    csv_data = df_to_download.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label=f"下载{all_data[table_to_download]['display_name']}为CSV",
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
        temp_df = data["df"][["date", "value"]].rename(columns={"value": data["display_name"]})
        if merged_df is None:
            merged_df = temp_df
        else:
            merged_df = pd.merge(merged_df, temp_df, on="date", how="outer")
    
    if merged_df is not None:
        # Excel下载
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for table_name, data in all_data.items():
                data["df"][["date", "value"]].rename(
                    columns={"value": data["display_name"]}
                ).to_excel(writer, sheet_name=data["display_name"], index=False)
        
        buffer.seek(0)
        st.download_button(
            label="下载所有数据为Excel（多sheet）",
            data=buffer,
            file_name=f"supabase_all_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
