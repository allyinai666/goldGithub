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

# ====================== 页面基础设置 ======================
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
    .warning-box {background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0;}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Supabase 多表数据可视化分析")

# 权限提示
st.markdown("""
<div class="warning-box">
<b>⚠️ 数据加载失败？</b> 请检查 Supabase 表策略：
1. 进入 Supabase 后台 → Authentication → Policies；
2. 为 gld_holdings/tips_yield/dxy_data/gold_price 表添加「Allow anon access」策略；
3. 重启应用后重试。
</div>
""", unsafe_allow_html=True)

# ====================== 初始化Supabase连接（极简版，适配所有版本） ======================
def init_supabase_connection():
    """初始化Supabase连接（无多余方法，兼容所有客户端版本）"""
    try:
        # 仅创建客户端，不调用任何特殊方法
        supabase_temp = create_client(SUPABASE_URL, SUPABASE_KEY)
        return True, "✅ Supabase 连接正常！"
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid" in error_str:
            return False, "❌ 鉴权失败：URL/Key错误（检查Secrets）"
        elif "connection" in error_str or "timeout" in error_str:
            return False, "❌ 网络连接失败：无法访问Supabase"
        else:
            return False, f"❌ 连接异常：{str(e)[:80]}"

# 自动初始化连接
conn_success, conn_msg = init_supabase_connection()
st.sidebar.header("🔌 连接状态")
st.sidebar.info(conn_msg)

# ====================== 数据加载函数（移除所有特殊方法，极简兼容） ======================
@st.cache_data(ttl=3600)
def load_supabase_table(table_name):
    """
    加载Supabase表数据（移除timeout/health等特殊方法，适配所有版本）
    """
    config = TABLES_CONFIG[table_name]
    date_col = config["date_col"]
    value_cols = config["value_cols"]
    
    try:
        # 1. 创建连接
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 2. 兼容表名大小写，仅保留limit取消分页（核心必要逻辑）
        table_name_lower = table_name.lower()
        # 移除timeout，仅保留limit和select（所有版本都支持）
        response = supabase.table(table_name_lower).select("*").limit(10000).execute()
        
        # 3. 检查响应数据
        raw_data_count = len(response.data)
        st.sidebar.write(f"📝 {table_name} 原始响应条数：{raw_data_count}")
        
        if raw_data_count == 0:
            raise Exception(f"表 {table_name_lower} 查询返回空数据（请检查表权限/是否有数据）")
        
        # 4. 解析数据
        df = pd.DataFrame(response.data)
        
        # 5. 字段检查
        if date_col not in df.columns:
            raise Exception(f"日期字段 {date_col} 不存在（表字段：{list(df.columns)}）")
        
        actual_value_col = None
        for col in value_cols:
            if col in df.columns:
                actual_value_col = col
                break
        if not actual_value_col:
            raise Exception(f"数值字段 {value_cols} 不存在（表字段：{list(df.columns)}）")
        
        # 6. 数据清洗（适配gold_price）
        if table_name == "gold_price":
            df["date"] = pd.to_datetime(df[date_col], errors="coerce", format="%Y-%m-%d")
        else:
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
        
        df["value"] = pd.to_numeric(df[actual_value_col], errors="coerce").fillna(0)
        df = df.dropna(subset=["date"]).reset_index(drop=True)
        
        st.sidebar.info(f"📋 {table_name} 有效数据条数：{len(df)}")
        return df, True, f"✅ 加载成功（有效数据：{len(df)} 条）"
    
    except Exception as e:
        st.warning(f"⚠️ 加载表 {table_name} 失败：{str(e)[:180]}")
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
