"""
思维导图服务：基于学科资料生成 Mermaid mindmap 格式的思维导图。
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
        根据文本块列表生成 Mermaid mindmap。

        :param chunks: 文本块列表
        :param subject_name: 学科名称（作为思维导图根节点）
        :raises ValueError: chunks 为空时
        :return: Mermaid mindmap 文本（以 mindmap 开头）
        """
        if not chunks:
            raise ValueError("所选资料暂无可用内容")

        # 最多取前 20 个块，避免超出 token 限制
        selected = chunks[:20]
        context = "\n\n".join(selected)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的知识结构分析助手。请分析以下学习资料，"
                    "提炼核心知识点和知识结构，以 Mermaid mindmap 格式输出思维导图。\n\n"
                    "输出要求：\n"
                    "1. 直接输出 Mermaid mindmap 代码，不要加 markdown 代码块标记\n"
                    "2. 第一行必须是 mindmap\n"
                    "3. 根节点使用学科名称\n"
                    "4. 层级清晰，使用缩进表示层级关系\n"
                    "5. 只输出 mindmap 代码，不要有任何其他说明文字"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"学科名称：{subject_name}\n\n"
                    f"学习资料内容：\n{context}"
                ),
            },
        ]

        result = self._llm_service.chat(messages)
        result = result.strip()

        # 若 LLM 返回了 markdown 代码块，提取其中内容
        if result.startswith("```"):
            lines = result.splitlines()
            # 去掉首行（```mermaid 或 ```）和末行（```）
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            result = "\n".join(inner).strip()

        return result

    def generate_from_subject(
        self, subject_id: int, doc_id: Optional[int] = None
    ) -> str:
        """
        从数据库查询文本块，生成思维导图。

        需求：12.1, 12.2, 12.4, 12.6

        :param subject_id: 学科 ID
        :param doc_id: 可选，指定文档 ID 过滤
        :return: Mermaid mindmap 文本
        :raises ValueError: 无可用内容时
        """
        from database import get_session, Chunk, Subject

        # 查询学科名称
        with get_session() as session:
            subject = session.get(Subject, subject_id)
            subject_name = subject.name if subject else f"学科 {subject_id}"

            # 查询文本块
            query = session.query(Chunk).filter(Chunk.subject_id == subject_id)
            if doc_id is not None:
                query = query.filter(Chunk.document_id == doc_id)
            chunk_rows = query.order_by(Chunk.chunk_index).all()
            chunks = [row.content for row in chunk_rows]

        return self.generate(chunks, subject_name)
