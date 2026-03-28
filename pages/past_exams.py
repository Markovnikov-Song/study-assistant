"""
历年题管理页面
需求：13.1, 13.5, 13.6, 13.7
"""

import streamlit as st

from utils import require_login, get_subject
from services.exam_service import ExamService


def _show_questions(exam_file_id: int) -> None:
    """展示指定文件的题目列表。"""
    from database import get_session, PastExamQuestion

    with get_session() as session:
        questions = (
            session.query(PastExamQuestion)
            .filter(PastExamQuestion.exam_file_id == exam_file_id)
            .order_by(PastExamQuestion.id)
            .all()
        )
        for q in questions:
            num = q.question_number or str(q.id)
            preview = q.content[:100] + ("…" if len(q.content) > 100 else "")
            st.markdown(f"**第 {num} 题**　{preview}")


# ── 登录检查 ──────────────────────────────────────────────────────────────
user = require_login()
user_id = user["id"]

# ── 获取学科 ──────────────────────────────────────────────────────────────
subject_id = st.session_state.get("current_subject_id")
if not subject_id:
    st.warning("未选择学科，请先进入学科详情页。")
    st.stop()

subject = get_subject(subject_id, user_id)
if not subject:
    st.error("学科不存在或无权限访问。")
    st.stop()

st.title(f"历年题管理 — {subject['name']}")

exam_service = ExamService()

# ── 文件上传 ──────────────────────────────────────────────────────────────
st.subheader("上传历年题文件")

uploaded_file = st.file_uploader(
    "选择文件（支持 PDF、图片、Word）",
    type=["pdf", "jpg", "jpeg", "png", "docx"],
    accept_multiple_files=False,
)

if uploaded_file is not None:
    with st.spinner(f"正在处理「{uploaded_file.name}」，请稍候…"):
        result = exam_service.process_past_exam_file(
            file_bytes=uploaded_file.read(),
            filename=uploaded_file.name,
            subject_id=subject_id,
            user_id=user_id,
        )
    if result["success"]:
        st.success(f"「{uploaded_file.name}」处理成功，共识别 {result['question_count']} 道题目。")
    else:
        st.error(f"处理失败：{result['error']}")

st.divider()

# ── 历年题文件列表 ────────────────────────────────────────────────────────
st.subheader("历年题文件列表")

exam_files = exam_service.list_past_exam_files(subject_id=subject_id, user_id=user_id)

if not exam_files:
    st.info("暂无历年题文件，请上传文件。")
else:
    status_map = {
        "pending": "⏳ 等待处理",
        "processing": "🔄 处理中",
        "completed": "✅ 已完成",
        "failed": "❌ 处理失败",
    }

    for f in exam_files:
        status_label = status_map.get(f["status"], f["status"])
        created_at = f["created_at"].strftime("%Y-%m-%d %H:%M") if f["created_at"] else ""

        with st.container(border=True):
            col_info, col_del = st.columns([8, 1])

            with col_info:
                st.write(f"**{f['filename']}**")
                st.caption(
                    f"{status_label}　共 {f['question_count']} 道题　上传时间：{created_at}"
                )
                if f["status"] == "failed" and f.get("error"):
                    st.caption(f"错误：{f['error']}")

            with col_del:
                with st.popover("删除"):
                    st.warning(f"确定要删除「{f['filename']}」及其所有题目吗？")
                    if st.button("确认删除", key=f"del_exam_{f['id']}", type="primary"):
                        del_result = exam_service.delete_past_exam_file(
                            file_id=f["id"],
                            subject_id=subject_id,
                            user_id=user_id,
                        )
                        if del_result["success"]:
                            st.rerun()
                        else:
                            st.error(del_result["error"])

            # 展开查看题目列表
            if f["status"] == "completed" and f["question_count"] > 0:
                with st.expander(f"查看题目（共 {f['question_count']} 道）"):
                    _show_questions(f["id"])
