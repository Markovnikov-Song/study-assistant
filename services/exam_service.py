"""
出题服务：历年题文件处理、预测试卷生成、自定义出题。
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExamService:
    """历年题处理与 AI 出题服务。"""

    def __init__(self) -> None:
        from services.llm_service import LLMService
        from services.ocr_service import OCRService
        self._llm_service = LLMService()
        self._ocr_service = OCRService()

    # ------------------------------------------------------------------
    # 13.1-13.4 历年题文件处理
    # ------------------------------------------------------------------

    def process_past_exam_file(
        self,
        file_bytes: bytes,
        filename: str,
        subject_id: int,
        user_id: int,
    ) -> dict:
        """
        处理历年题文件：解析文本、结构化题目、写入数据库。

        需求：13.1, 13.2, 13.3, 13.4

        :param file_bytes: 文件二进制内容
        :param filename: 原始文件名
        :param subject_id: 学科 ID
        :param user_id: 用户 ID
        :return: {"success": bool, "file_id": int, "question_count": int, "error": str}
        """
        from database import get_session, PastExamFile, PastExamQuestion

        tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid4()}_{filename}")
        file_id: Optional[int] = None

        try:
            # 写入临时文件
            with open(tmp_path, "wb") as f:
                f.write(file_bytes)

            # 写入 past_exam_files 表（status='pending'）
            with get_session() as session:
                exam_file = PastExamFile(
                    subject_id=subject_id,
                    user_id=user_id,
                    filename=filename,
                    status="pending",
                )
                session.add(exam_file)
                session.flush()
                file_id = exam_file.id

            # 解析文件文本
            text = self._parse_exam_file(tmp_path, filename)

            # 调用 LLM 结构化题目
            questions = self._extract_questions(text)

            # 写入 past_exam_questions 表
            with get_session() as session:
                for q in questions:
                    question = PastExamQuestion(
                        exam_file_id=file_id,
                        subject_id=subject_id,
                        question_number=q.get("number", ""),
                        content=q.get("content", ""),
                        answer=q.get("answer", ""),
                    )
                    session.add(question)

            # 更新 status='completed'
            self._update_file_status(file_id, "completed")

            return {
                "success": True,
                "file_id": file_id,
                "question_count": len(questions),
                "error": "",
            }

        except Exception as e:
            logger.error("历年题文件处理失败：%s", e)
            if file_id is not None:
                self._update_file_status(file_id, "failed", str(e))
            return {
                "success": False,
                "file_id": file_id,
                "question_count": 0,
                "error": str(e),
            }

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _parse_exam_file(self, tmp_path: str, filename: str) -> str:
        """按文件类型解析文本内容。"""
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return self._parse_pdf(tmp_path)
        elif ext in (".jpg", ".jpeg", ".png"):
            return self._ocr_service.extract_text(tmp_path)
        elif ext == ".docx":
            return self._parse_docx(tmp_path)
        else:
            raise ValueError(f"不支持的文件格式：{ext}")

    def _parse_pdf(self, tmp_path: str) -> str:
        """PDF 解析：文本页直接提取，图片页调用 OCR。"""
        import pdfplumber

        pages_text: List[str] = []
        with pdfplumber.open(tmp_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    try:
                        text = self._ocr_service.extract_text_from_pdf_page(
                            tmp_path, page_num
                        )
                    except Exception as e:
                        logger.warning("第 %d 页 OCR 失败：%s", page_num, e)
                        text = ""
                pages_text.append(text)
        return "\n".join(pages_text)

    def _parse_docx(self, tmp_path: str) -> str:
        """DOCX 解析。"""
        from docx import Document
        doc = Document(tmp_path)
        return "\n".join(para.text for para in doc.paragraphs)

    def _extract_questions(self, text: str) -> List[dict]:
        """调用 LLM 将文本结构化为题目列表。"""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的试卷解析助手。请将以下试卷文本按题目分割，"
                    "结构化为 JSON 数组格式。\n\n"
                    "输出格式（严格 JSON，不要有其他文字）：\n"
                    '[{"number": "1", "content": "题目内容", "answer": "参考答案（若有）"}, ...]'
                ),
            },
            {
                "role": "user",
                "content": f"试卷内容：\n{text}",
            },
        ]

        result = self._llm_service.chat(messages)
        result = result.strip()

        # 去除可能的 markdown 代码块
        if result.startswith("```"):
            lines = result.splitlines()
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            result = "\n".join(inner).strip()

        try:
            questions = json.loads(result)
            if isinstance(questions, list):
                return questions
        except json.JSONDecodeError:
            logger.warning("LLM 返回的题目 JSON 解析失败，尝试提取 JSON 数组")

        # 尝试从文本中提取 JSON 数组
        import re
        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error("无法解析 LLM 返回的题目结构")
        return []

    def _update_file_status(
        self, file_id: int, status: str, error: Optional[str] = None
    ) -> None:
        """更新 past_exam_files 表的 status 和 error 字段。"""
        from database import get_session, PastExamFile

        with get_session() as session:
            exam_file = session.get(PastExamFile, file_id)
            if exam_file:
                exam_file.status = status
                if error is not None:
                    exam_file.error = error

    # ------------------------------------------------------------------
    # 13.5-13.6 列表与删除
    # ------------------------------------------------------------------

    def list_past_exam_files(self, subject_id: int, user_id: int) -> List[dict]:
        """
        查询指定学科下当前用户的历年题文件列表。

        需求：13.5

        :param subject_id: 学科 ID
        :param user_id: 用户 ID
        :return: 文件信息列表
        """
        from database import get_session, PastExamFile, PastExamQuestion
        from sqlalchemy import func

        with get_session() as session:
            files = (
                session.query(PastExamFile)
                .filter(
                    PastExamFile.subject_id == subject_id,
                    PastExamFile.user_id == user_id,
                )
                .order_by(PastExamFile.created_at.desc())
                .all()
            )

            result = []
            for f in files:
                question_count = (
                    session.query(func.count(PastExamQuestion.id))
                    .filter(PastExamQuestion.exam_file_id == f.id)
                    .scalar()
                )
                result.append(
                    {
                        "id": f.id,
                        "filename": f.filename,
                        "status": f.status,
                        "error": f.error,
                        "question_count": question_count,
                        "created_at": f.created_at,
                    }
                )
            return result

    def delete_past_exam_file(
        self, file_id: int, subject_id: int, user_id: int
    ) -> dict:
        """
        删除历年题文件及其关联题目。

        需求：13.6

        :param file_id: 文件 ID
        :param subject_id: 学科 ID（验证归属）
        :param user_id: 用户 ID（验证归属）
        :return: {"success": bool, "error": str}
        """
        from database import get_session, PastExamFile

        try:
            with get_session() as session:
                exam_file = (
                    session.query(PastExamFile)
                    .filter(
                        PastExamFile.id == file_id,
                        PastExamFile.subject_id == subject_id,
                        PastExamFile.user_id == user_id,
                    )
                    .first()
                )
                if exam_file is None:
                    return {"success": False, "error": "文件不存在或无权限删除"}
                session.delete(exam_file)
            return {"success": True, "error": ""}
        except Exception as e:
            logger.error("删除历年题文件失败：%s", e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # 14.1-14.2 预测试卷生成
    # ------------------------------------------------------------------

    def generate_predicted_paper(self, subject_id: int, user_id: int) -> str:
        """
        基于历年题分析考点分布，生成预测试卷（Markdown 格式）。

        需求：14.1, 14.2

        :param subject_id: 学科 ID
        :param user_id: 用户 ID
        :return: Markdown 格式预测试卷，无历年题时返回空字符串
        """
        from database import get_session, PastExamQuestion

        with get_session() as session:
            questions = (
                session.query(PastExamQuestion)
                .filter(PastExamQuestion.subject_id == subject_id)
                .all()
            )
            if not questions:
                return ""

            questions_text = "\n\n".join(
                f"第{q.question_number}题：{q.content}"
                + (f"\n参考答案：{q.answer}" if q.answer else "")
                for q in questions
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的考试分析与出题助手。请根据以下历年题目，"
                    "分析考点分布和题型比例，然后生成一份预测试卷。\n\n"
                    "要求：\n"
                    "1. 先简要分析考点分布和题型规律\n"
                    "2. 生成预测试卷，题型和分值比例参考历年规律\n"
                    "3. 每道题附上参考答案\n"
                    "4. 使用 Markdown 格式输出"
                ),
            },
            {
                "role": "user",
                "content": f"历年题目：\n{questions_text}",
            },
        ]

        return self._llm_service.chat(messages)

    # ------------------------------------------------------------------
    # 14.3-14.5 自定义出题
    # ------------------------------------------------------------------

    def generate_custom_questions(
        self,
        subject_id: int,
        user_id: int,
        question_types: List[str],
        count: int,
        difficulty: str,
        topic: str,
    ) -> str:
        """
        按参数生成自定义题目和参考答案（Markdown 格式）。

        需求：14.3, 14.4, 14.5

        :param subject_id: 学科 ID
        :param user_id: 用户 ID
        :param question_types: 题型列表，如 ["选择题", "简答题"]
        :param count: 题目数量
        :param difficulty: 难度，如 "简单"/"中等"/"困难"
        :param topic: 指定考点/主题
        :return: Markdown 格式题目与答案
        """
        from database import get_session, Chunk

        # 查询学科文本块作为参考资料（最多取 20 块）
        with get_session() as session:
            chunk_rows = (
                session.query(Chunk)
                .filter(Chunk.subject_id == subject_id)
                .order_by(Chunk.chunk_index)
                .limit(20)
                .all()
            )
            chunks = [row.content for row in chunk_rows]

        context = "\n\n".join(chunks) if chunks else "（暂无学科资料，请根据题目要求出题）"
        types_str = "、".join(question_types) if question_types else "综合题型"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的出题助手。请根据提供的学科资料和要求，"
                    "生成高质量的题目和参考答案。\n\n"
                    "要求：\n"
                    "1. 严格按照指定题型、数量、难度和考点出题\n"
                    "2. 每道题附上详细的参考答案\n"
                    "3. 使用 Markdown 格式输出，题目和答案分开展示"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"题型：{types_str}\n"
                    f"数量：{count} 道\n"
                    f"难度：{difficulty}\n"
                    f"考点/主题：{topic}\n\n"
                    f"参考资料：\n{context}"
                ),
            },
        ]

        return self._llm_service.chat(messages)
