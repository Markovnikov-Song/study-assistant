"""
独立思维导图页面
需求：12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

import streamlit as st

from utils import require_login, get_subject
from services.document_service import DocumentService
from services.mindmap_service import MindMapService

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

st.title(f"思维导图 — {subject['name']}")

# ── 资料选择 ──────────────────────────────────────────────────────────────
docs = DocumentService().list_documents(subject_id=subject_id, user_id=user_id)
completed_docs = [d for d in docs if d["status"] == "completed"]

if not completed_docs:
    st.info("暂无已处理完成的资料，请先在学科详情页上传并等待处理完成。")
    st.stop()

options = ["全部资料"] + [d["filename"] for d in completed_docs]
selected = st.selectbox("选择资料范围", options, key="mindmap_page_doc_select")

doc_id_filter = None
if selected != "全部资料":
    doc_id_filter = next(
        (d["id"] for d in completed_docs if d["filename"] == selected), None
    )

# ── 生成按钮 ──────────────────────────────────────────────────────────────
if st.button("生成思维导图", key="mindmap_page_generate", type="primary"):
    with st.spinner("正在生成思维导图…"):
        try:
            mermaid_text = MindMapService().generate_from_subject(
                subject_id=subject_id,
                doc_id=doc_id_filter,
            )
            st.session_state["mindmap_page_result"] = mermaid_text
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"生成失败：{e}")

# ── 展示结果 ──────────────────────────────────────────────────────────────
mindmap_result = st.session_state.get("mindmap_page_result")
if mindmap_result:
    st.markdown(f"```mermaid\n{mindmap_result}\n```")
    st.download_button(
        label="导出 Mermaid 文本",
        data=mindmap_result,
        file_name=f"{subject['name']}_mindmap.md",
        mime="text/markdown",
        key="mindmap_page_download",
    )
