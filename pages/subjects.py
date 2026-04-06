"""
学科管理页面
"""

import streamlit as st

from utils import (
    require_login, get_user_subjects, create_subject,
    delete_subject, update_subject, toggle_pin_subject, toggle_archive_subject,
)

user = require_login()
user_id = user["id"]

st.title("我的学科")

# ── 学科列表 ──────────────────────────────────────────────────────────────
subjects = get_user_subjects(user_id, include_archived=False)

if not subjects:
    st.info("还没有学科，请在下方创建一个。")
else:
    for subject in subjects:
        pin_icon = "📌" if subject["is_pinned"] else ""
        with st.container(border=True):
            col_info, col_enter, col_edit, col_pin, col_more = st.columns([5, 1, 1, 1, 1])

            with col_info:
                st.subheader(f"{pin_icon} {subject['name']}" if pin_icon else subject["name"])
                if subject["category"]:
                    st.caption(f"分类：{subject['category']}")
                if subject["description"]:
                    st.write(subject["description"])

            with col_enter:
                if st.button("进入", key=f"enter_{subject['id']}"):
                    st.session_state["current_subject_id"] = subject["id"]
                    st.switch_page("pages/subject_detail.py")

            with col_edit:
                with st.popover("编辑"):
                    with st.form(key=f"edit_form_{subject['id']}"):
                        new_name = st.text_input("学科名称 *", value=subject["name"])
                        new_category = st.text_input("分类", value=subject["category"] or "")
                        new_desc = st.text_area("描述", value=subject["description"] or "")
                        save = st.form_submit_button("保存")
                    if save:
                        result = update_subject(subject["id"], user_id, new_name, new_category, new_desc)
                        if result["success"]:
                            st.rerun()
                        else:
                            st.error(result["error"])

            with col_pin:
                pin_label = "取消置顶" if subject["is_pinned"] else "📌 置顶"
                if st.button(pin_label, key=f"pin_{subject['id']}"):
                    toggle_pin_subject(subject["id"], user_id)
                    st.rerun()

            with col_more:
                with st.popover("⋯"):
                    if st.button("📦 归档", key=f"archive_{subject['id']}"):
                        toggle_archive_subject(subject["id"], user_id)
                        st.rerun()
                    st.divider()
                    with st.popover("🗑 删除"):
                        st.warning(f"确定要删除「{subject['name']}」吗？此操作不可撤销。")
                        if st.button("确认删除", key=f"confirm_del_{subject['id']}", type="primary"):
                            result = delete_subject(subject["id"], user_id)
                            if result["success"]:
                                st.rerun()
                            else:
                                st.error(result["error"])

# ── 归档学科 ──────────────────────────────────────────────────────────────
archived = get_user_subjects(user_id, include_archived=True)
archived = [s for s in archived if s["is_archived"]]

if archived:
    with st.expander(f"📦 归档学科（{len(archived)}）", expanded=False):
        for subject in archived:
            with st.container(border=True):
                c1, c2, c3 = st.columns([6, 1, 1])
                with c1:
                    st.write(f"**{subject['name']}**")
                    if subject["category"]:
                        st.caption(f"分类：{subject['category']}")
                with c2:
                    if st.button("恢复", key=f"unarchive_{subject['id']}"):
                        toggle_archive_subject(subject["id"], user_id)
                        st.rerun()
                with c3:
                    with st.popover("删除"):
                        st.warning(f"确定删除「{subject['name']}」？")
                        if st.button("确认", key=f"del_archived_{subject['id']}", type="primary"):
                            result = delete_subject(subject["id"], user_id)
                            if result["success"]:
                                st.rerun()
                            else:
                                st.error(result["error"])

# ── 创建学科 ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("创建学科")

with st.form("create_subject_form"):
    name = st.text_input("学科名称 *")
    category = st.text_input("分类（可选）")
    description = st.text_area("描述（可选）")
    create_submitted = st.form_submit_button("创建")

if create_submitted:
    if not name or not name.strip():
        st.error("学科名称不能为空")
    else:
        result = create_subject(user_id, name, category, description)
        if result["success"]:
            st.success(f"学科「{result['subject']['name']}」创建成功！")
            st.rerun()
        else:
            st.error(result["error"])
