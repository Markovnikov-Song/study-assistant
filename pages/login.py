"""
登录/注册页面
需求：1.1, 1.5, 2.1
"""

import streamlit as st

from services.auth_service import AuthService

st.title("学科学习助手")

login_tab, register_tab = st.tabs(["登录", "注册"])

# ── 登录 ──────────────────────────────────────────────────────────────────
with login_tab:
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")

    if submitted:
        result = AuthService().login(username, password)
        if result["success"]:
            st.rerun()
        else:
            st.error(result["error"])

# ── 注册 ──────────────────────────────────────────────────────────────────
with register_tab:
    with st.form("register_form"):
        reg_username = st.text_input("用户名", key="reg_username")
        reg_password = st.text_input("密码", type="password", key="reg_password")
        reg_confirm = st.text_input("确认密码", type="password", key="reg_confirm")
        reg_submitted = st.form_submit_button("注册")

    if reg_submitted:
        if reg_password != reg_confirm:
            st.error("两次密码输入不一致")
        else:
            result = AuthService().register(reg_username, reg_password)
            if result["success"]:
                login_result = AuthService().login(reg_username, reg_password)
                if login_result["success"]:
                    st.rerun()
            else:
                st.error(result["error"])
