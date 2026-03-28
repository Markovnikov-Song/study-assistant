"""
LLM 服务：封装 OpenAI 兼容客户端，支持普通对话、视觉（OCR）和流式输出。
客户端懒加载，首次调用时才初始化。
"""

from __future__ import annotations

import base64
from typing import Generator, List, Optional

from openai import OpenAI


class LLMService:
    """封装 OpenAI 兼容 API 的 LLM 服务。"""

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
        return get_config().LLM_CHAT_MODEL

    def chat(self, messages: List[dict], **kwargs) -> str:
        """
        调用 chat completions，返回回答文本。

        :param messages: OpenAI 格式的消息列表
        :param kwargs: 额外参数（如 temperature、max_tokens 等）
        :raises RuntimeError: LLM 调用失败时
        :return: 模型回答文本
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._get_model(),
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"AI 服务暂时不可用，请稍后重试。（{e}）") from e

    def chat_with_vision(self, messages: List[dict], image_b64: str) -> str:
        """
        将 base64 图片嵌入消息，调用支持视觉的模型（用于 OCR）。

        :param messages: 基础消息列表（通常包含 system prompt）
        :param image_b64: base64 编码的图片字符串
        :raises RuntimeError: LLM 调用失败时
        :return: 模型识别文本
        """
        try:
            client = self._get_client()
            vision_messages = list(messages) + [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": "请识别并提取图片中的所有文字内容。",
                        },
                    ],
                }
            ]
            response = client.chat.completions.create(
                model=self._get_model(),
                messages=vision_messages,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"AI 视觉服务暂时不可用，请稍后重试。（{e}）") from e

    def stream_chat(self, messages: List[dict]) -> Generator[str, None, None]:
        """
        流式返回 token。

        :param messages: OpenAI 格式的消息列表
        :raises RuntimeError: LLM 调用失败时
        :yields: 每个流式 token 文本片段
        """
        try:
            client = self._get_client()
            stream = client.chat.completions.create(
                model=self._get_model(),
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            raise RuntimeError(f"AI 流式服务暂时不可用，请稍后重试。（{e}）") from e
