"""
认证服务：提供用户注册、登录、登出和当前用户查询功能。
使用 bcrypt 加密密码，通过 session_state 管理登录状态。
"""

from __future__ import annotations

from typing import Optional

import bcrypt
import streamlit as st

from database import User, get_session


class AuthService:
    """用户认证服务，封装注册、登录、登出和会话管理逻辑。"""

    def register(self, username: str, password: str) -> dict:
        """
        注册新用户。

        :param username: 用户名
        :param password: 明文密码
        :return: {"success": True, "user": {...}} 或 {"success": False, "error": "..."}
        """
        if not username or not username.strip():
            return {"success": False, "error": "用户名不能为空"}

        if len(password) < 6:
            return {"success": False, "error": "密码长度不能少于6个字符"}

        with get_session() as session:
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return {"success": False, "error": "用户名已被占用"}

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            user = User(username=username, password_hash=password_hash)
            session.add(user)
            session.flush()  # 获取自增 id

            return {
                "success": True,
                "user": {"id": user.id, "username": user.username},
            }

    def login(self, username: str, password: str) -> dict:
        """
        用户登录。

        :param username: 用户名
        :param password: 明文密码
        :return: {"success": True, "user": {...}} 或 {"success": False, "error": "..."}
        """
        with get_session() as session:
            user = session.query(User).filter_by(username=username).first()

            if user is None:
                return {"success": False, "error": "用户名或密码错误"}

            if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
                return {"success": False, "error": "用户名或密码错误"}

            user_info = {"id": user.id, "username": user.username}
            st.session_state["user"] = user_info
            return {"success": True, "user": user_info}

    def logout(self) -> None:
        """登出：清除 session_state 中的用户信息。"""
        st.session_state["user"] = None

    def get_current_user(self) -> Optional[dict]:
        """
        获取当前登录用户信息。

        :return: {"id": ..., "username": ...} 或 None（未登录）
        """
        return st.session_state.get("user", None)
