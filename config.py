import os
from dotenv import load_dotenv

# 加载环境变量（本地开发用）
load_dotenv()

# 从环境变量读取配置（部署时优先读取Secrets）
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
