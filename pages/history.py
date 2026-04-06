"""
对话历史页面
"""

import streamlit as st

from utils import (
    require_login,
    get_user_sessions,
    get_session_history,
    delete_session,
    delete_message,
    delete_all_sessions,
    delete_empty_sessions,
    export_session_markdown,
    export_session_html,
    export_session_word,
)

user = require_login()
user_id = user["id"]

st.title("对话历史")

sessions = get_user_sessions(user_id)

if not sessions:
    st.info("暂无对话记录。")
    st.stop()

# 顶部操作栏
top_col1, top_col2, top_col3 = st.columns([3, 1, 1])
with top_col1:
    sort_by = st.radio(
        "排序",
        ["按时间排序", "按学科分组"],
        horizontal=True,
        label_visibility="collapsed",
    )
with top_col2:
    if st.button("🧹 清理空会话", use_container_width=True):
        count = delete_empty_sessions(user_id)
        st.success(f"已清理 {count} 条空会话")
        st.rerun()
with top_col3:
    with st.popover("🗑 清空全部", use_container_width=True):
        st.warning(f"确定删除全部 {len(sessions)} 条对话记录？此操作不可撤销。")
        if st.button("确认清空", key="del_all_btn", type="primary"):
            result = delete_all_sessions(user_id)
            if result["success"]:
                st.rerun()

st.divider()


def _render_sessions(session_list: list, uid: int) -> None:
    for s in session_list:
        title = s["title"] or f"对话 #{s['id']}"
        subject_name = s["subject_name"] or "未关联学科"
        type_label_map = {"qa": "问答", "solve": "解题", "mindmap": "思维导图", "exam": "出题"}
        type_label = type_label_map.get(s["session_type"] or "", s["session_type"] or "")
        created_at = s["created_at"].strftime("%Y-%m-%d %H:%M") if s["created_at"] else ""

        with st.expander(f"**{title}**　{subject_name}　{type_label}　{created_at}"):
            history = get_session_history(s["id"], uid)
            if not history:
                st.caption("暂无对话记录。")
            else:
                for msg in history:
                    role_label = "🧑 用户" if msg["role"] == "user" else "🤖 助手"
                    ts = msg["created_at"].strftime("%H:%M:%S") if msg["created_at"] else ""
                    msg_col, del_col = st.columns([10, 1])
                    with msg_col:
                        st.markdown(f"**{role_label}** `{ts}`")
                        st.markdown(msg["content"])
                    with del_col:
                        if st.button("✕", key=f"del_msg_{msg['id']}", help="删除这条消息"):
                            delete_message(msg["id"], uid)
                            st.rerun()
                    st.divider()

            # 会话操作按钮
            col_del, col_md, col_html, col_word = st.columns(4)
            with col_del:
                with st.popover("🗑 删除会话"):
                    st.warning(f"确定删除「{title}」？")
                    if st.button("确认", key=f"del_session_{s['id']}", type="primary"):
                        delete_session(s["id"], uid)
                        st.rerun()
            with col_md:
                md = export_session_markdown(s["id"], uid)
                if md:
                    st.download_button("📄 MD", data=md,
                        file_name=f"session_{s['id']}.md", mime="text/markdown",
                        key=f"exp_md_{s['id']}")
            with col_html:
                html = export_session_html(s["id"], uid)
                if html:
                    st.download_button("🌐 HTML", data=html,
                        file_name=f"session_{s['id']}.html", mime="text/html",
                        key=f"exp_html_{s['id']}")
            with col_word:
                word = export_session_word(s["id"], uid)
                if word:
                    st.download_button("📝 Word", data=word,
                        file_name=f"session_{s['id']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"exp_word_{s['id']}")


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
