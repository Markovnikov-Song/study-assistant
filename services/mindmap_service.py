"""
思维导图服务：基于学科资料生成 markmap 格式的思维导图。
"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class MindMapService:
    """思维导图生成服务。"""

    def __init__(self) -> None:
        from services.llm_service import LLMService
        self._llm_service = LLMService()

    def generate(self, chunks: List[str], subject_name: str) -> str:
        """
        根据文本块列表生成 markmap 格式思维导图（Markdown 标题层级）。

        :param chunks: 文本块列表
        :param subject_name: 学科名称（作为根节点）
        :raises ValueError: chunks 为空时
        :return: markmap Markdown 文本
        """
        if not chunks:
            raise ValueError("所选资料暂无可用内容")

        selected = chunks[:20]
        context = "\n\n".join(selected)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的知识结构分析助手。请分析以下学习资料，"
                    "提炼核心知识点，以 Markdown 标题层级格式输出思维导图（markmap 格式）。\n\n"
                    "输出要求：\n"
                    "1. 使用 Markdown 标题语法（# ## ### ####）表示层级\n"
                    "2. 第一行用 # 作为根节点，内容为学科名称\n"
                    "3. 二级节点用 ##，三级用 ###，最多四级\n"
                    "4. 每个节点简洁，不超过 15 个字\n"
                    "5. 只输出 Markdown 内容，不要有任何代码块标记或说明文字\n"
                    "6. 示例格式：\n"
                    "# 学科名称\n"
                    "## 第一章\n"
                    "### 核心概念\n"
                    "#### 定义\n"
                    "#### 性质\n"
                    "### 重要定理\n"
                    "## 第二章\n"
                ),
            },
            {
                "role": "user",
                "content": f"学科名称：{subject_name}\n\n学习资料内容：\n{context}",
            },
        ]

        result = self._llm_service.chat(messages)
        result = result.strip()

        # 去除可能的代码块包裹
        if result.startswith("```"):
            lines = result.splitlines()
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            result = "\n".join(inner).strip()

        return result

    def generate_from_subject(
        self, subject_id: int, doc_id: Optional[int] = None
    ) -> str:
        from database import get_session, Chunk, Subject

        with get_session() as session:
            subject = session.get(Subject, subject_id)
            subject_name = subject.name if subject else f"学科 {subject_id}"
            query = session.query(Chunk).filter(Chunk.subject_id == subject_id)
            if doc_id is not None:
                query = query.filter(Chunk.document_id == doc_id)
            chunk_rows = query.order_by(Chunk.chunk_index).all()
            chunks = [row.content for row in chunk_rows]

        return self.generate(chunks, subject_name)
