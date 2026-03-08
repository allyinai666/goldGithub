import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import os

# 从环境变量读取数据库配置
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def get_dxy():
    dx = yf.Ticker("DX-Y.NYB")
    data = dx.history(period='1d')
    if not data.empty:
        price = data['Close'].iloc[-1]
        change = data['Close'].iloc[-1] - data['Open'].iloc[-1]
        df = pd.DataFrame([{
            "date": datetime.now(),
            "dxy_value": price,
            "dxy_change": change,
            "dxy_change_pct": change/price*100
        }])
        df.to_sql("dxy_data", engine, if_exists="append", index=False)

def get_gld():
    gld = yf.Ticker("GLD")
    holdings = gld.info.get("heldPercentInsiders", 0)
    df = pd.DataFrame([{
        "date": datetime.now().date(),
        "gld_holdings_oz": str(holdings),
        "gld_holdings_value": ""
    }])
    df.to_sql("gld_holdings", engine, if_exists="append", index=False)

def get_tips():
    tips = yf.Ticker("DFX")
    price = tips.history(period='1d')['Close'].iloc[-1]
    df = pd.DataFrame([{
        "date": datetime.now().date(),
        "y10_tips_yield": price
    }])
    df.to_sql("tips_yield", engine, if_exists="append", index=False)

if __name__ == "__main__":
    get_dxy()
    get_gld()
    get_tips()
    print("更新完成")