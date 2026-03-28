"""
嵌入服务：封装 OpenAI 兼容 Embedding API，支持批量和单条向量生成。
客户端懒加载，首次调用时才初始化。
"""

from __future__ import annotations

from typing import List, Optional

from openai import OpenAI


class EmbeddingService:
    """封装 OpenAI 兼容 API 的 Embedding 服务。"""

    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """懒加载：首次调用时初始化 OpenAI 客户端。"""
        if self._client is None:
            from config import get_config
            cfg = get_config()
            self._client = OpenAI(
                api_key=cfg.LLM_API_KEY,
                base_url=cfg.LLM_BASE_URL,
            )
        return self._client

    def _get_model(self) -> str:
        from config import get_config
        return get_config().LLM_EMBEDDING_MODEL

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本向量。

        :param texts: 待向量化的文本列表
        :raises RuntimeError: Embedding 调用失败时
        :return: 每条文本对应的向量列表
        """
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self._get_model(),
                input=texts,
            )
            # 按原始顺序返回向量
            return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        except Exception as e:
            raise RuntimeError(f"向量化服务暂时不可用，请稍后重试。（{e}）") from e

    def embed_query(self, text: str) -> List[float]:
        """
        生成单条查询文本的向量。

        :param text: 查询文本
        :raises RuntimeError: Embedding 调用失败时
        :return: 查询向量
        """
        results = self.embed_texts([text])
        return results[0]
