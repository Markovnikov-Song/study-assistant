"""
对话历史页面
需求：8.1, 8.2, 8.3, 8.4, 8.5
"""

import streamlit as st

from utils import (
    require_login,
    get_user_sessions,
    get_session_history,
    delete_session,
    export_session_markdown,
    export_session_html,
    export_session_word,
)

# ── 登录检查 ──────────────────────────────────────────────────────────────
user = require_login()
user_id = user["id"]

st.title("对话历史")


def _render_sessions(session_list: list, uid: int) -> None:
    """渲染会话列表。"""
    for s in session_list:
        title = s["title"] or f"对话 #{s['id']}"
        subject_name = s["subject_name"] or "未关联学科"
        session_type = s["session_type"] or ""
        created_at = s["created_at"].strftime("%Y-%m-%d %H:%M") if s["created_at"] else ""

        type_label_map = {
            "qa": "问答",
            "solve": "解题",
            "mindmap": "思维导图",
            "exam": "出题",
        }
        type_label = type_label_map.get(session_type, session_type)

        with st.expander(f"**{title}**　{subject_name}　{type_label}　{created_at}"):
            # 对话记录
            history = get_session_history(s["id"], uid)
            if not history:
                st.caption("暂无对话记录。")
            else:
                for msg in history:
                    role_label = "🧑 用户" if msg["role"] == "user" else "🤖 助手"
                    ts = msg["created_at"].strftime("%H:%M:%S") if msg["created_at"] else ""
                    st.markdown(f"**{role_label}** `{ts}`")
                    st.markdown(msg["content"])
                    st.divider()

            # 操作按钮
            col_del, col_md, col_html, col_word = st.columns([1, 1, 1, 1])

            with col_del:
                with st.popover("删除"):
                    st.warning(f"确定要删除「{title}」吗？此操作不可撤销。")
                    if st.button("确认删除", key=f"del_session_{s['id']}", type="primary"):
                        result = delete_session(s["id"], uid)
                        if result["success"]:
                            st.rerun()
                        else:
                            st.error(result["error"])

            with col_md:
                md_content = export_session_markdown(s["id"], uid)
                if md_content:
                    st.download_button("📄 MD", data=md_content,
                        file_name=f"session_{s['id']}.md", mime="text/markdown",
                        key=f"export_md_{s['id']}")

            with col_html:
                html_content = export_session_html(s["id"], uid)
                if html_content:
                    st.download_button("🌐 HTML", data=html_content,
                        file_name=f"session_{s['id']}.html", mime="text/html",
                        key=f"export_html_{s['id']}")

            with col_word:
                word_bytes = export_session_word(s["id"], uid)
                if word_bytes:
                    st.download_button("📝 Word", data=word_bytes,
                        file_name=f"session_{s['id']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"export_word_{s['id']}")


# ── 获取会话列表 ──────────────────────────────────────────────────────────
sessions = get_user_sessions(user_id)

if not sessions:
    st.info("暂无对话记录。")
    st.stop()

# ── 排序选项 ──────────────────────────────────────────────────────────────
sort_by = st.radio(
    "排序方式",
    ["按时间排序", "按学科分组"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

# ── 渲染 ──────────────────────────────────────────────────────────────────
if sort_by == "按学科分组":
    groups: dict = {}
    for s in sessions:
        key = s["subject_name"] or "未关联学科"
        groups.setdefault(key, []).append(s)

    for subject_name, group_sessions in groups.items():
        st.subheader(subject_name)
        _render_sessions(group_sessions, user_id)
else:
    _render_sessions(sessions, user_id)
