"""
学科详情页面 — 统一对话界面（问答 / 解题 / 思维导图）
"""

import streamlit as st

from utils import (
    require_login, get_subject,
    get_subject_sessions, get_session_history, delete_session,
    export_session_markdown, export_session_html, export_session_word,
)
from services.document_service import DocumentService
from services.rag_pipeline import RAGPipeline
from services.mindmap_service import MindMapService

# ── 登录检查 ──────────────────────────────────────────────────────────────
user = require_login()
user_id = user["id"]

subject_id = st.session_state.get("current_subject_id")
if not subject_id:
    st.warning("未选择学科，请返回学科列表。")
    st.stop()

subject = get_subject(subject_id, user_id)
if not subject:
    st.error("学科不存在或无权限访问。")
    st.stop()

# ── 顶部标题 + 标签页 ─────────────────────────────────────────────────────
st.title(subject["name"])
if subject.get("category"):
    st.caption(f"分类：{subject['category']}")

tab_chat, tab_docs = st.tabs(["💬 学习助手", "📁 资料管理"])

# =============================================================================
# 资料管理
# =============================================================================
with tab_docs:
    st.subheader("上传资料")

    uploaded_file = st.file_uploader(
        "选择文件",
        type=["pdf", "docx", "pptx", "txt", "md"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".pdf"):
            import pdfplumber, io
            sample_bytes = uploaded_file.read()
            is_scanned = False
            try:
                with pdfplumber.open(io.BytesIO(sample_bytes)) as pdf:
                    texts = [p.extract_text() or "" for p in pdf.pages[:5]]
                    if all(not t.strip() for t in texts):
                        is_scanned = True
            except Exception:
                pass
            if is_scanned:
                st.warning(
                    "⚠️ 检测到这是**扫描版 PDF**，无法直接提取文字。\n\n"
                    "请先转换为文字版再上传：\n"
                    "- [ilovepdf.com](https://www.ilovepdf.com/zh-cn/pdf_to_word)\n"
                    "- [smallpdf.com](https://smallpdf.com/cn/pdf-to-word)"
                )
                st.stop()
            file_bytes = sample_bytes
        else:
            file_bytes = uploaded_file.read()

        uploaded_set = st.session_state.get("uploaded_files", set())
        if uploaded_file.name in uploaded_set:
            st.info(f"「{uploaded_file.name}」已上传，跳过重复处理。")
        else:
            with st.spinner(f"正在处理「{uploaded_file.name}」…"):
                result = DocumentService().upload_and_process(
                    file_bytes=file_bytes,
                    filename=uploaded_file.name,
                    subject_id=subject_id,
                    user_id=user_id,
                )
            if result["success"]:
                st.session_state.setdefault("uploaded_files", set()).add(uploaded_file.name)
                st.success(f"「{uploaded_file.name}」上传并处理成功！")
            else:
                st.error(f"处理失败：{result['error']}")

    st.divider()
    st.subheader("资料列表")
    docs = DocumentService().list_documents(subject_id=subject_id, user_id=user_id)
    if not docs:
        st.info("暂无资料，请上传文件。")
    else:
        status_map = {"pending": "⏳ 等待", "processing": "🔄 处理中", "completed": "✅ 完成", "failed": "❌ 失败"}
        for doc in docs:
            with st.container(border=True):
                c1, c2 = st.columns([8, 1])
                with c1:
                    st.write(f"**{doc['filename']}**")
                    st.caption(f"{status_map.get(doc['status'], doc['status'])}　{doc['created_at'].strftime('%Y-%m-%d %H:%M')}")
                    if doc["status"] == "failed" and doc.get("error"):
                        st.caption(f"错误：{doc['error']}")
                with c2:
                    with st.popover("删除"):
                        st.warning(f"确定删除「{doc['filename']}」？")
                        if st.button("确认", key=f"del_doc_{doc['id']}", type="primary"):
                            r = DocumentService().delete_document(doc["id"], subject_id, user_id)
                            if r["success"]:
                                st.rerun()
                            else:
                                st.error(r["error"])

# =============================================================================
# 统一学习助手对话界面
# =============================================================================
with tab_chat:
    col_hist, col_main = st.columns([1, 3])

    # ── 左侧：历史会话列表 ────────────────────────────────────────────────
    with col_hist:
        st.markdown("**历史记录**")

        if st.button("＋ 新建对话", key="new_session_btn", use_container_width=True, type="primary"):
            for k in ["current_session_id", "pending_question", "needs_confirm", "mindmap_result"]:
                st.session_state.pop(k, None)
            st.rerun()

        past = get_subject_sessions(subject_id, user_id)
        for s in past:
            is_cur = s["id"] == st.session_state.get("current_session_id")
            label = f"{'▶ ' if is_cur else ''}{s['type_label']} {s['title']}"
            ts = s["created_at"].strftime("%m-%d %H:%M")
            if st.button(f"{label}\n{ts}", key=f"hist_{s['id']}", use_container_width=True):
                st.session_state["current_session_id"] = s["id"]
                st.session_state.pop("mindmap_result", None)
                st.rerun()

    # ── 右侧：对话区 ──────────────────────────────────────────────────────
    with col_main:

        # 模式选择 + 通用知识开关
        mode_col, toggle_col = st.columns([3, 2])
        with mode_col:
            mode = st.radio(
                "模式",
                ["💬 问答", "🔢 解题", "🗺 思维导图"],
                horizontal=True,
                key="chat_mode",
                label_visibility="collapsed",
            )
        with toggle_col:
            use_broad = st.checkbox(
                "结合通用知识",
                key="use_broad_toggle",
                help="勾选后不限于已上传资料，AI 会标注来源",
            )

        # 模式映射
        mode_map = {"💬 问答": "qa", "🔢 解题": "solve", "🗺 思维导图": "mindmap"}
        session_type = mode_map[mode]

        # 确保当前会话存在（切换模式时自动创建对应类型的新会话）
        cur_sid = st.session_state.get("current_session_id")
        if cur_sid:
            past_types = {s["id"]: s["session_type"] for s in past}
            if past_types.get(cur_sid) and past_types[cur_sid] != session_type:
                cur_sid = None
                st.session_state.pop("current_session_id", None)

        if not cur_sid:
            cur_sid = RAGPipeline().create_session(
                user_id=user_id,
                subject_id=subject_id,
                session_type=session_type,
            )
            st.session_state["current_session_id"] = cur_sid
            st.rerun()

        # ── 显示历史消息 ──────────────────────────────────────────────────
        history_msgs = get_session_history(cur_sid, user_id)

        if session_type == "mindmap":
            # 思维导图：显示最后一次生成结果
            last_answer = next(
                (m["content"] for m in reversed(history_msgs) if m["role"] == "assistant"), None
            )
            if last_answer:
                st.markdown(f"```mermaid\n{last_answer}\n```")
                st.download_button("导出 Mermaid", data=last_answer,
                    file_name=f"{subject['name']}_mindmap.md", mime="text/markdown",
                    key="mindmap_dl")
        else:
            for msg in history_msgs:
                with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        with st.expander("参考来源", expanded=False):
                            for src in msg["sources"]:
                                st.caption(f"· {src.get('filename','')}（片段 {src.get('chunk_index','')}）：{str(src.get('content',''))[:80]}…")

        # ── 相关性不足确认 ────────────────────────────────────────────────
        if st.session_state.get("needs_confirm"):
            st.warning("已上传资料中未找到高度相关内容，请选择：")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("仅基于已上传资料", key="confirm_strict"):
                    _q = st.session_state.get("pending_question", "")
                    _mode = st.session_state.get("pending_mode", "strict")
                    with st.spinner("生成中…"):
                        r = RAGPipeline().query(_q, subject_id, cur_sid, mode=_mode)
                    st.session_state.pop("needs_confirm", None)
                    st.rerun()
            with c2:
                if st.button("拓宽范围，结合通用知识", key="confirm_broad"):
                    _q = st.session_state.get("pending_question", "")
                    with st.spinner("生成中…"):
                        r = RAGPipeline().query(_q, subject_id, cur_sid, mode="broad")
                    st.session_state.pop("needs_confirm", None)
                    st.rerun()

        # ── 输入框 ────────────────────────────────────────────────────────
        if session_type == "mindmap":
            # 思维导图：选择资料范围 + 生成按钮
            all_docs = DocumentService().list_documents(subject_id=subject_id, user_id=user_id)
            done_docs = [d for d in all_docs if d["status"] == "completed"]
            if not done_docs:
                st.info("请先在「资料管理」上传并处理文件。")
            else:
                opts = ["全部资料"] + [d["filename"] for d in done_docs]
                sel = st.selectbox("选择资料范围", opts, key="mindmap_sel")
                doc_id_filter = None if sel == "全部资料" else next(
                    (d["id"] for d in done_docs if d["filename"] == sel), None
                )
                if st.button("生成思维导图", key="mindmap_gen", type="primary"):
                    with st.spinner("正在生成…"):
                        try:
                            mermaid = MindMapService().generate_from_subject(subject_id, doc_id_filter)
                            # 保存到历史
                            from database import get_session as db_session, ConversationHistory
                            with db_session() as db:
                                db.add(ConversationHistory(session_id=cur_sid, role="user", content=f"生成思维导图：{sel}"))
                                db.add(ConversationHistory(session_id=cur_sid, role="assistant", content=mermaid))
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        else:
            placeholder = "输入题目…" if session_type == "solve" else "输入问题…"
            question = st.chat_input(placeholder, key="unified_chat_input")

            if question and question.strip():
                st.session_state["pending_question"] = question.strip()
                query_mode = "broad" if use_broad else ("solve" if session_type == "solve" else "strict")
                st.session_state["pending_mode"] = query_mode

                with st.chat_message("user"):
                    st.markdown(question.strip())

                with st.spinner("生成中…"):
                    result = RAGPipeline().query(
                        question=question.strip(),
                        subject_id=subject_id,
                        session_id=cur_sid,
                        mode=query_mode,
                    )

                if result.needs_confirmation:
                    st.session_state["needs_confirm"] = True
                st.rerun()

        # ── 导出 / 删除工具栏 ─────────────────────────────────────────────
        if history_msgs:
            st.divider()
            ec1, ec2, ec3, ec4 = st.columns(4)
            with ec1:
                md = export_session_markdown(cur_sid, user_id)
                st.download_button("📄 Markdown", data=md,
                    file_name=f"对话_{cur_sid}.md", mime="text/markdown",
                    key="exp_md", use_container_width=True)
            with ec2:
                html = export_session_html(cur_sid, user_id)
                st.download_button("🌐 HTML", data=html,
                    file_name=f"对话_{cur_sid}.html", mime="text/html",
                    key="exp_html", use_container_width=True)
            with ec3:
                word = export_session_word(cur_sid, user_id)
                st.download_button("📝 Word", data=word,
                    file_name=f"对话_{cur_sid}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="exp_word", use_container_width=True)
            with ec4:
                with st.popover("🗑 删除", use_container_width=True):
                    st.warning("删除后不可恢复")
                    if st.button("确认删除", key="del_session_btn", type="primary"):
                        delete_session(cur_sid, user_id)
                        st.session_state.pop("current_session_id", None)
                        st.rerun()
