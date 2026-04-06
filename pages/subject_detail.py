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


@st.cache_data(ttl=30, show_spinner=False)
def _cached_list_docs(subject_id, user_id):
    return DocumentService().list_documents(subject_id=subject_id, user_id=user_id)


@st.cache_data(ttl=30, show_spinner=False)
def _cached_sessions(subject_id, user_id):
    return get_subject_sessions(subject_id, user_id)


@st.cache_data(ttl=30, show_spinner=False)
def _cached_history(session_id, user_id):
    return get_session_history(session_id, user_id)

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

st.title(subject["name"])
if subject.get("category"):
    st.caption(f"分类：{subject['category']}")

tab_chat, tab_docs, tab_exams, tab_gen = st.tabs(["💬 学习助手", "📁 资料管理", "📝 历年题", "🤖 AI 出题"])

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
    # 历史记录（折叠面板）
    with st.expander("📋 历史记录", expanded=False):
        if st.button("＋ 新建对话", key="new_session_btn", use_container_width=True, type="primary"):
            for k in ["current_session_id", "pending_question", "needs_confirm"]:
                st.session_state.pop(k, None)
            st.rerun()

        past = get_subject_sessions(subject_id, user_id)
        for s in past:
            is_cur = s["id"] == st.session_state.get("current_session_id")
            label = f"{'▶ ' if is_cur else ''}{s['type_label']} {s['title']}"
            ts = s["created_at"].strftime("%m-%d %H:%M")
            if st.button(f"{label}  {ts}", key=f"hist_{s['id']}", use_container_width=True):
                st.session_state["current_session_id"] = s["id"]
                st.rerun()

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

    mode_map = {"💬 问答": "qa", "🔢 解题": "solve", "🗺 思维导图": "mindmap"}
    session_type = mode_map[mode]

    # 确保当前会话类型匹配
    past = get_subject_sessions(subject_id, user_id)
    cur_sid = st.session_state.get("current_session_id")
    if cur_sid:
        past_types = {s["id"]: s["session_type"] for s in past}
        if past_types.get(cur_sid) and past_types[cur_sid] != session_type:
            cur_sid = None
            st.session_state.pop("current_session_id", None)

    if not cur_sid:
        cur_sid = None  # 懒创建，提交时才建

    history_msgs = get_session_history(cur_sid, user_id) if cur_sid else []

    # 显示消息
    if session_type == "mindmap":
        last_answer = next(
            (m["content"] for m in reversed(history_msgs) if m["role"] == "assistant"), None
        )
        if last_answer:
            try:
                from streamlit_markmap import markmap
                markmap(last_answer, height=500)
            except ImportError:
                st.markdown(last_answer)
            st.download_button("导出 Markdown", data=last_answer,
                file_name=f"{subject['name']}_mindmap.md", mime="text/markdown",
                key="mindmap_dl")
            st.caption("💡 想导出为图片？将上方 Markdown 文件粘贴到 [markmap.js.org](https://markmap.js.org/repl)，点右上角可导出 SVG/PNG。")
    else:
        for msg in history_msgs:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("参考来源", expanded=False):
                        for src in msg["sources"]:
                            st.caption(f"· {src.get('filename','')}（片段 {src.get('chunk_index','')}）：{str(src.get('content',''))[:80]}…")

    if st.session_state.get("needs_confirm") and cur_sid:
        st.warning("已上传资料中未找到高度相关内容，请选择：")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("仅基于已上传资料", key="confirm_strict"):
                _q = st.session_state.get("pending_question", "")
                _mode = st.session_state.get("pending_mode", "strict")
                with st.spinner("生成中…"):
                    RAGPipeline().query(_q, subject_id, cur_sid, mode=_mode)
                st.session_state.pop("needs_confirm", None)
                st.rerun()
        with c2:
            if st.button("拓宽范围，结合通用知识", key="confirm_broad"):
                _q = st.session_state.get("pending_question", "")
                with st.spinner("生成中…"):
                    RAGPipeline().query(_q, subject_id, cur_sid, mode="broad")
                st.session_state.pop("needs_confirm", None)
                st.rerun()

    # 输入区
    if session_type == "mindmap":
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
                with st.status("正在生成思维导图…", expanded=True) as status:
                    try:
                        st.write("📖 读取资料内容…")
                        st.write("🧠 AI 分析知识结构…")
                        mindmap_text = MindMapService().generate_from_subject(subject_id, doc_id_filter)
                        st.write("💾 保存结果…")
                        # 懒创建会话
                        if not cur_sid:
                            cur_sid = RAGPipeline().create_session(
                                user_id=user_id, subject_id=subject_id, session_type="mindmap"
                            )
                            st.session_state["current_session_id"] = cur_sid
                        from database import get_session as db_session, ConversationHistory
                        with db_session() as db:
                            db.add(ConversationHistory(session_id=cur_sid, role="user", content=f"生成思维导图：{sel}"))
                            db.add(ConversationHistory(session_id=cur_sid, role="assistant", content=mindmap_text))
                        status.update(label="✅ 思维导图生成完成！", state="complete")
                        st.rerun()
                    except Exception as e:
                        status.update(label="❌ 生成失败", state="error")
                        st.error(str(e))
    else:
        placeholder = "输入题目…" if session_type == "solve" else "输入问题…"

        # 图片上传 + 粘贴 + 文本输入
        ocr_key = f"{session_type}_img_upload"
        prefill_key = f"{session_type}_ocr_prefill"
        text_key = f"{session_type}_text_input"
        submit_key = f"{session_type}_submit_btn"
        ocr_btn_key = f"{session_type}_ocr_btn"
        paste_key = f"{session_type}_paste_btn"

        img_col, paste_col = st.columns([3, 1])
        with img_col:
            img_file = st.file_uploader(
                "📷 上传图片（JPG/PNG）",
                type=["jpg", "jpeg", "png"],
                key=ocr_key,
            )
        with paste_col:
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                from streamlit_paste_button import paste_image_button
                pasted = paste_image_button("📋 粘贴截图", key=paste_key)
                paste_processed_key = f"{paste_key}_processed"
                if pasted.image_data is not None and not st.session_state.get(paste_processed_key):
                    st.session_state[paste_processed_key] = True
                    import base64, io as _io
                    buf = _io.BytesIO()
                    pasted.image_data.save(buf, format="PNG")
                    img_bytes = buf.getvalue()
                    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                    st.session_state[f"{paste_key}_img"] = img_bytes
                    with st.spinner("正在识别…"):
                        from services.llm_service import LLMService
                        try:
                            ocr_text = LLMService().chat_with_vision(
                                [{"role": "system", "content": "请识别图片中的文字内容，只输出文字，不要其他说明。"}],
                                img_b64
                            )
                            st.session_state[prefill_key] = ocr_text
                            st.session_state[text_key] = ocr_text  # 直接写入 text_area 的 key
                            st.rerun()
                        except Exception as e:
                            st.error(f"识别失败：{e}")
                elif pasted.image_data is None:
                    st.session_state.pop(paste_processed_key, None)

                # 显示已粘贴的图片预览
                if st.session_state.get(f"{paste_key}_img"):
                    st.image(st.session_state[f"{paste_key}_img"], caption="已粘贴图片", use_container_width=True)
            except ImportError:
                st.caption("安装 streamlit-paste-button 支持粘贴")

        if img_file is not None:
            import base64
            img_b64 = base64.b64encode(img_file.read()).decode("utf-8")
            if st.button("识别图片文字", key=ocr_btn_key):
                with st.spinner("正在识别…"):
                    from services.llm_service import LLMService
                    try:
                        ocr_text = LLMService().chat_with_vision(
                            [{"role": "system", "content": "请识别图片中的文字内容，只输出文字，不要其他说明。"}],
                            img_b64
                        )
                        st.session_state[prefill_key] = ocr_text
                        st.session_state[text_key] = ocr_text  # 直接写入 text_area 的 key
                        st.rerun()
                    except Exception as e:
                        st.error(f"识别失败：{e}")

        prefill = st.session_state.get(prefill_key, "")
        question_text = st.text_area(
            "内容",
            height=100,
            key=text_key,
            placeholder=placeholder,
            label_visibility="collapsed",
        )
        if prefill:
            st.caption("已识别内容，可在上方编辑后提交")
        btn_label = "提交解题" if session_type == "solve" else "提交问题"
        question = question_text if st.button(btn_label, key=submit_key, type="primary") else None

        if question and question.strip():
            st.session_state.pop(f"{session_type}_ocr_prefill", None)
            st.session_state.pop("ocr_prefill", None)
            st.session_state.pop(f"{paste_key}_img", None)
            st.session_state.pop(f"{paste_key}_processed", None)
            st.session_state["pending_question"] = question.strip()
            query_mode = "broad" if use_broad else ("solve" if session_type == "solve" else "strict")
            st.session_state["pending_mode"] = query_mode

            # 懒创建会话：只在真正提交时才建
            if not cur_sid:
                cur_sid = RAGPipeline().create_session(
                    user_id=user_id,
                    subject_id=subject_id,
                    session_type=session_type,
                )
                st.session_state["current_session_id"] = cur_sid

            with st.chat_message("user"):
                st.markdown(question.strip())

            label = "🔢 正在解题…" if session_type == "solve" else "💬 正在生成回答…"
            with st.status(label, expanded=True) as status:
                st.write("🔍 检索相关资料…")
                result = RAGPipeline().query(
                    question=question.strip(),
                    subject_id=subject_id,
                    session_id=cur_sid,
                    mode=query_mode,
                )
                if not result.needs_confirmation:
                    status.update(label="✅ 完成", state="complete")

            if result.needs_confirmation:
                st.session_state["needs_confirm"] = True
            st.rerun()

    # 导出 / 删除
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

# =============================================================================
# 历年题管理
# =============================================================================
with tab_exams:
    from services.exam_service import ExamService
    exam_service = ExamService()

    st.subheader("上传历年题")
    exam_file = st.file_uploader(
        "选择文件（PDF、图片、Word）",
        type=["pdf", "jpg", "jpeg", "png", "docx"],
        key="exam_upload",
    )
    if exam_file is not None:
        with st.spinner(f"正在处理「{exam_file.name}」…"):
            result = exam_service.process_past_exam_file(
                file_bytes=exam_file.read(),
                filename=exam_file.name,
                subject_id=subject_id,
                user_id=user_id,
            )
        if result["success"]:
            st.success(f"处理成功，共识别 {result['question_count']} 道题目。")
        else:
            st.error(f"处理失败：{result['error']}")

    st.divider()
    st.subheader("历年题列表")
    exam_files = exam_service.list_past_exam_files(subject_id=subject_id, user_id=user_id)
    if not exam_files:
        st.info("暂无历年题，请上传文件。")
    else:
        status_map = {"pending": "⏳", "processing": "🔄", "completed": "✅", "failed": "❌"}
        for f in exam_files:
            with st.container(border=True):
                c1, c2 = st.columns([8, 1])
                with c1:
                    st.write(f"**{f['filename']}**")
                    st.caption(f"{status_map.get(f['status'], '')} {f['question_count']} 道题　{f['created_at'].strftime('%Y-%m-%d %H:%M')}")
                with c2:
                    with st.popover("删除"):
                        st.warning(f"确定删除？")
                        if st.button("确认", key=f"del_exam_{f['id']}", type="primary"):
                            r = exam_service.delete_past_exam_file(f["id"], subject_id, user_id)
                            if r["success"]:
                                st.rerun()
                if f["status"] == "completed" and f["question_count"] > 0:
                    with st.expander(f"查看题目（{f['question_count']} 道）"):
                        from database import get_session as _db, PastExamQuestion
                        with _db() as _s:
                            qs = _s.query(PastExamQuestion).filter_by(exam_file_id=f["id"]).all()
                            for q in qs:
                                st.markdown(f"**第 {q.question_number} 题**　{q.content[:100]}{'…' if len(q.content) > 100 else ''}")

# =============================================================================
# AI 出题
# =============================================================================
with tab_gen:
    from services.exam_service import ExamService as _ES
    _exam_svc = _ES()

    gen_tab1, gen_tab2 = st.tabs(["预测试卷", "自定义出题"])

    with gen_tab1:
        st.markdown("基于已上传的历年题，AI 分析考点分布自动生成模拟试卷。")
        _exam_files = _exam_svc.list_past_exam_files(subject_id=subject_id, user_id=user_id)
        _has_exams = any(f["status"] == "completed" and f["question_count"] > 0 for f in _exam_files)
        if not _has_exams:
            st.warning("请先在「历年题」标签上传并处理历年题文件。")
        else:
            if st.button("生成预测试卷", key="gen_predicted", type="primary"):
                with st.spinner("正在生成…"):
                    _result = _exam_svc.generate_predicted_paper(subject_id=subject_id, user_id=user_id)
                if _result:
                    st.session_state["predicted_paper"] = _result
                else:
                    st.error("生成失败，请稍后重试。")
            if st.session_state.get("predicted_paper"):
                st.markdown(st.session_state["predicted_paper"])
                st.download_button("导出 Markdown", data=st.session_state["predicted_paper"],
                    file_name=f"{subject['name']}_预测试卷.md", mime="text/markdown",
                    key="dl_predicted")

    with gen_tab2:
        q_types = st.multiselect("题型", ["选择题", "填空题", "简答题", "计算题"],
            default=["选择题", "简答题"], key="custom_types")
        q_count = st.slider("数量", 1, 20, 5, key="custom_count")
        q_diff = st.radio("难度", ["简单", "中等", "困难"], index=1, horizontal=True, key="custom_diff")
        q_topic = st.text_input("考点/主题（可选）", key="custom_topic")

        if st.button("生成题目", key="gen_custom", type="primary"):
            if not q_types:
                st.warning("请至少选择一种题型。")
            else:
                with st.spinner("正在生成…"):
                    _result = _exam_svc.generate_custom_questions(
                        subject_id=subject_id, user_id=user_id,
                        question_types=q_types, count=q_count,
                        difficulty=q_diff, topic=q_topic.strip() or "全部考点",
                    )
                if _result:
                    st.session_state["custom_questions"] = _result
                else:
                    st.error("生成失败，请稍后重试。")
        if st.session_state.get("custom_questions"):
            st.markdown(st.session_state["custom_questions"])
            st.download_button("导出 Markdown", data=st.session_state["custom_questions"],
                file_name=f"{subject['name']}_自定义题目.md", mime="text/markdown",
                key="dl_custom")
