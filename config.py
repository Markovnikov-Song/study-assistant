"""
配置模块：从 st.secrets 读取所有配置项，启动时校验必需项。
不在模块导入时读取 secrets（避免 Streamlit 启动时报错）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# 必需配置项
_REQUIRED_KEYS = [
    "DATABASE_URL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_CHAT_MODEL",
    "LLM_EMBEDDING_MODEL",
]

# 可选配置项及默认值
_DEFAULTS = {
    "SIMILARITY_THRESHOLD": 0.3,
    "CHUNK_SIZE": 1000,
    "CHUNK_OVERLAP": 200,
    "TOP_K": 5,
}


@dataclass
class AppConfig:
    # 必需项
    DATABASE_URL: str
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_CHAT_MODEL: str
    LLM_EMBEDDING_MODEL: str
    # 可选项
    SIMILARITY_THRESHOLD: float = 0.3
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5


# 模块级缓存，首次调用 get_config() 时填充
_config: Optional[AppConfig] = None


def validate_config(secrets: dict) -> None:
    """
    校验必需配置项是否存在。
    缺失任意必需项时抛出包含键名的 ValueError。

    :param secrets: 类字典对象（如 st.secrets 或普通 dict）
    :raises ValueError: 当存在缺失的必需配置项时
    """
    missing = [key for key in _REQUIRED_KEYS if key not in secrets or not secrets[key]]
    if missing:
        raise ValueError(
            f"缺少必需的配置项：{', '.join(missing)}。"
            "请在 .streamlit/secrets.toml 中配置这些项目。"
        )


def get_config() -> AppConfig:
    """
    返回配置对象（懒加载：首次调用时才读取 st.secrets）。

    :raises ValueError: 当存在缺失的必需配置项时
    :return: AppConfig 实例
    """
    global _config
    if _config is None:
        import streamlit as st

        secrets = st.secrets
        validate_config(secrets)

        _config = AppConfig(
            DATABASE_URL=secrets["DATABASE_URL"],
            LLM_API_KEY=secrets["LLM_API_KEY"],
            LLM_BASE_URL=secrets["LLM_BASE_URL"],
            LLM_CHAT_MODEL=secrets["LLM_CHAT_MODEL"],
            LLM_EMBEDDING_MODEL=secrets["LLM_EMBEDDING_MODEL"],
            SIMILARITY_THRESHOLD=float(
                secrets.get("SIMILARITY_THRESHOLD", _DEFAULTS["SIMILARITY_THRESHOLD"])
            ),
            CHUNK_SIZE=int(secrets.get("CHUNK_SIZE", _DEFAULTS["CHUNK_SIZE"])),
            CHUNK_OVERLAP=int(secrets.get("CHUNK_OVERLAP", _DEFAULTS["CHUNK_OVERLAP"])),
            TOP_K=int(secrets.get("TOP_K", _DEFAULTS["TOP_K"])),
        )
    return _config


def reset_config() -> None:
    """重置缓存的配置（主要用于测试）。"""
    global _config
    _config = None
