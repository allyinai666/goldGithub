# config.py - 读取Streamlit Cloud Secrets环境变量 + 全局配置
import os
import streamlit as st  # Streamlit Cloud读取Secrets必须用st.secrets

# ====================== 从Streamlit Secrets读取Supabase连接配置 ======================
# 适配Streamlit Cloud的Secrets读取方式
try:
    # 优先读取Streamlit Secrets（部署环境）
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    # 本地开发时读取.env文件（可选）
    try:
        from dotenv import load_dotenv
        load_dotenv()
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    except:
        # 兜底：避免本地运行报错
        SUPABASE_URL = ""
        SUPABASE_KEY = ""

# ====================== 表字段配置（全局变量，确保app.py能导入） ======================
# 注意：此变量必须顶格定义（无缩进），名称严格为TABLES_CONFIG
TABLES_CONFIG = {
    "gld_holdings": {
        "date_col": "date",
        "value_cols": ["gld_holdings_oz"],
        "display_name": "GLD持仓量",
        "color": "#FF6B6B",
        "unit": "盎司"
    },
    "tips_yield": {
        "date_col": "date",
        "value_cols": ["y10_tips_yield"],
        "display_name": "10年期TIPS收益率",
        "color": "#4ECDC4",
        "unit": "%"
    },
    "dxy_data": {
        "date_col": "date",
        "value_cols": ["dxy_value"],
        "display_name": "美元指数",
        "color": "#0052CC",
        "unit": ""
    },
    "gold_price": {
        "date_col": "gold_date",
        "value_cols": ["nwgold_price"],
        "display_name": "黄金价格",
        "color": "#FFD700",
        "unit": "USD/盎司"
    }
}

# ====================== 页面配置（全局变量） ======================
PAGE_CONFIG = {
    "page_title": "Supabase 多表数据可视化",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# ====================== 模拟数据基础值配置（全局变量） ======================
SIMULATE_DATA_BASE = {
    "gld_holdings": 10000000,
    "tips_yield": 1.5,
    "dxy_data": 102,
    "gold_price": 2100
}
