"""
AI 出题页面
需求：14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7
"""

import streamlit as st

from utils import require_login, get_subject
from services.exam_service import ExamService
from services.rag_pipeline import RAGPipeline
from database import get_session, ConversationHistory


def _save_exam_result(user_id: int, subject_id: int, session_type: str, prompt: str, result: str) -> None:
    """将出题结果保存到 conversation_history。"""
    session_id = RAGPipeline().create_session(
        user_id=user_id,
        subject_id=subject_id,
        session_type=session_type,
    )
    with get_session() as db:
        db.add(ConversationHistory(
            session_id=session_id,
            role="user",
            content=prompt,
        ))
        db.add(ConversationHistory(
            session_id=session_id,
            role="assistant",
            content=result,
        ))


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

st.title(f"AI 出题 — {subject['name']}")

exam_service = ExamService()

tab_predicted, tab_custom = st.tabs(["预测试卷", "自定义出题"])

# =============================================================================
# 预测试卷
# =============================================================================
with tab_predicted:
    st.markdown("基于已上传的历年题，AI 将分析考点分布和题型规律，自动生成一份预测试卷。")

    # 检查是否有历年题
    exam_files = exam_service.list_past_exam_files(subject_id=subject_id, user_id=user_id)
    has_past_exams = any(f["status"] == "completed" and f["question_count"] > 0 for f in exam_files)

    if not has_past_exams:
        st.warning("请先在「历年题管理」页上传并处理历年题文件，才能生成预测试卷。")
    else:
        if st.button("生成预测试卷", key="predicted_generate", type="primary"):
            with st.spinner("正在分析历年题并生成预测试卷，请稍候…"):
                result = exam_service.generate_predicted_paper(
                    subject_id=subject_id,
                    user_id=user_id,
                )
            if result:
                st.session_state["predicted_paper_result"] = result
                _save_exam_result(
                    user_id=user_id,
                    subject_id=subject_id,
                    session_type="exam",
                    prompt="生成预测试卷",
                    result=result,
                )
            else:
                st.error("生成失败，请稍后重试。")

        predicted_result = st.session_state.get("predicted_paper_result")
        if predicted_result:
            st.divider()
            st.markdown(predicted_result)
            st.download_button(
                label="导出试卷（Markdown）",
                data=predicted_result,
                file_name=f"{subject['name']}_预测试卷.md",
                mime="text/markdown",
                key="predicted_download",
            )

# =============================================================================
# 自定义出题
# =============================================================================
with tab_custom:
    st.markdown("按照你的需求自定义题型、数量、难度和考点，AI 将为你生成对应题目和参考答案。")

    question_types = st.multiselect(
        "题型",
        ["选择题", "填空题", "简答题", "计算题"],
        default=["选择题", "简答题"],
        key="custom_question_types",
    )

    count = st.slider("题目数量", min_value=1, max_value=20, value=5, key="custom_count")

    difficulty = st.radio(
        "难度",
        ["简单", "中等", "困难"],
        index=1,
        horizontal=True,
        key="custom_difficulty",
    )

    topic = st.text_input(
        "考点 / 主题（可选，留空则覆盖全部资料）",
        placeholder="例如：牛顿第二定律、函数极值",
        key="custom_topic",
    )

    if st.button("生成题目", key="custom_generate", type="primary"):
        if not question_types:
            st.warning("请至少选择一种题型。")
        else:
            with st.spinner("正在生成题目，请稍候…"):
                result = exam_service.generate_custom_questions(
                    subject_id=subject_id,
                    user_id=user_id,
                    question_types=question_types,
                    count=count,
                    difficulty=difficulty,
                    topic=topic.strip() or "全部考点",
                )
            if result:
                st.session_state["custom_questions_result"] = result
                types_str = "、".join(question_types)
                prompt = (
                    f"自定义出题：题型={types_str}，数量={count}，"
                    f"难度={difficulty}，考点={topic.strip() or '全部考点'}"
                )
                _save_exam_result(
                    user_id=user_id,
                    subject_id=subject_id,
                    session_type="exam",
                    prompt=prompt,
                    result=result,
                )
            else:
                st.error("生成失败，请稍后重试。")

    custom_result = st.session_state.get("custom_questions_result")
    if custom_result:
        st.divider()
        st.markdown(custom_result)
        st.download_button(
            label="导出题目（Markdown）",
            data=custom_result,
            file_name=f"{subject['name']}_自定义题目.md",
            mime="text/markdown",
            key="custom_download",
        )
