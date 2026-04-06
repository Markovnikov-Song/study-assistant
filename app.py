"""
应用入口：配置页面路由、初始化配置与数据库。
需求：9.3, 10.3
"""

import streamlit as st

st.set_page_config(
    page_title="学科学习助手",
    page_icon="📚",
)

# ── 配置校验 ──────────────────────────────────────────────────────────────
import config as cfg

try:
    cfg.validate_config(st.secrets)
except ValueError as e:
    st.error(f"配置错误：{e}")
    st.stop()

# ── 数据库初始化 ──────────────────────────────────────────────────────────
import database

try:
    database.init_db()
except Exception as e:
    st.error(f"数据库初始化失败：{e}")
    st.stop()

# ── 页面定义 ──────────────────────────────────────────────────────────────
from services.auth_service import AuthService

login_page = st.Page("pages/login.py", title="登录", icon="🔑")

subjects_page = st.Page("pages/subjects.py", title="学科列表", icon="📋")
subject_detail_page = st.Page("pages/subject_detail.py", title="学科详情", icon="📖")
history_page = st.Page("pages/history.py", title="对话历史", icon="💬")
past_exams_page = st.Page("pages/past_exams.py", title="历年题管理", icon="📝")
exam_generator_page = st.Page("pages/exam_generator.py", title="AI 出题", icon="🤖")
guide_page = st.Page("pages/guide.py", title="新手教程", icon="📖")

# ── 路由逻辑 ──────────────────────────────────────────────────────────────
user = AuthService().get_current_user()

if not user:
    pg = st.navigation([login_page, guide_page])
else:
    # 侧边栏：用户信息与登出
    with st.sidebar:
        st.write(f"👤 {user['username']}")
        if st.button("登出", use_container_width=True):
            AuthService().logout()
            st.rerun()

    pg = st.navigation([
        subjects_page,
        subject_detail_page,
        history_page,
        guide_page,
    ])

pg.run()
