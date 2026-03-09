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

# ====================== 初始化Supabase连接 ======================
def init_supabase_connection():
    """初始化Supabase连接（仅验证，不返回客户端对象）"""
    try:
        supabase_temp = create_client(SUPABASE_URL, SUPABASE_KEY)
        # 验证gold_price表连接（指定limit避免分页问题）
        response = supabase_temp.table("gold_price").select("*").limit(1).execute()
        if len(response.data) > 0:
            return True, "✅ Supabase连接成功！"
        else:
            return True, "✅ Supabase连接成功！（gold_price表查询到空数据）"
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid" in error_str:
            return False, "❌ 鉴权失败：URL或Key错误，请检查Secrets配置"
        elif "pgrst205" in error_str or "relation" in error_str:
            return True, "✅ Supabase连接成功！（表可能未创建/权限不足）"
        else:
            return False, f"❌ 连接失败：{str(e)[:100]}"

# 自动初始化连接
conn_success, conn_msg = init_supabase_connection()
st.sidebar.header("🔌 连接状态")
st.sidebar.info(conn_msg)

# ====================== 数据加载函数（修复gold_price表分页/读取问题） ======================
@st.cache_data(ttl=3600)
def load_supabase_table(table_name):
    """
    加载Supabase表数据（适配gold_price表：取消分页限制，兼容text主键）
    """
    config = TABLES_CONFIG[table_name]
    date_col = config["date_col"]
    value_cols = config["value_cols"]
    
    try:
        # 1. 创建连接
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 2. 核心修复：取消分页限制，读取所有数据（适配2000+条数据）
        # gold_price表特殊处理：指定limit=10000（覆盖2000条），兼容text主键
        if table_name == "gold_price":
            response = supabase.table(table_name).select("*").limit(10000).execute()
        else:
            response = supabase.table(table_name).select("*").limit(10000).execute()
        
        # 3. 解析响应数据（关键：确保data不为空）
        df = pd.DataFrame(response.data)
        # 修复：用write替代无效的debug命令，显示原始数据条数
        st.sidebar.write(f"📝 {table_name} 原始数据条数：{len(df)}")
        
        # 4. 检查数据是否为空
        if df.empty:
            raise Exception(f"表查询返回空数据（响应数据条数：{len(response.data)}）")
        
        # 5. 字段检查
        if date_col not in df.columns:
            raise Exception(f"日期字段 {date_col} 不存在，表字段：{list(df.columns)}")
        
        actual_value_col = None
        for col in value_cols:
            if col in df.columns:
                actual_value_col = col
                break
        if not actual_value_col:
            raise Exception(f"数值字段 {value_cols} 不存在，表字段：{list(df.columns)}")
        
        # 6. 数据清洗（重点适配gold_price的text类型日期/数值）
        # 日期字段转换（gold_date是text类型，需强制转换）
        if table_name == "gold_price":
            # 强制转换text类型的gold_date为日期（忽略格式错误）
            df["date"] = pd.to_datetime(df[date_col], errors="coerce", format="%Y-%m-%d")
        else:
            if df[date_col].dtype == "object":
                df["date"] = pd.to_datetime(df[date_col], errors="coerce")
            else:
                df["date"] = pd.to_datetime(df[date_col])
        
        # 数值字段转换（gold_price的nwgold_price是text类型）
        df["value"] = pd.to_numeric(df[actual_value_col], errors="coerce").fillna(0)
        
        # 过滤无效数据
        df = df.dropna(subset=["date"]).reset_index(drop=True)
        st.sidebar.info(f"📋 {table_name} 有效数据条数：{len(df)}（原始：{len(response.data)}）")
        
        return df, True, f"✅ 加载成功（有效数据：{len(df)} 条）"
    
    except Exception as e:
        st.warning(f"⚠️ 加载表 {table_name} 失败：{str(e)[:150]}")
        # 生成模拟数据
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

# ====================== 数据概览 ======================
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
    merged_df = None
    for table_name, data in all_data.items():
        temp_df = data["df"][["date", "value"]].rename(columns={"value": data["display_name"]})
        if merged_df is None:
            merged_df = temp_df
        else:
            merged_df = pd.merge(merged_df, temp_df, on="date", how="outer")
    
    if merged_df is not None:
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
