"""
OCR 服务：优先使用 LLM 视觉能力识别图片文字，失败时降级到 pytesseract。
支持直接识别图片文件，以及将 PDF 指定页转为图片后识别。
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OCRService:
    """OCR 识别服务，优先 LLM 视觉，备选 pytesseract。"""

    def __init__(self) -> None:
        from services.llm_service import LLMService
        self._llm_service = LLMService()

    def extract_text(self, image_path: str) -> str:
        """
        从图片文件中提取文字。

        优先调用 LLM 视觉能力（chat_with_vision），失败时静默降级到
        pytesseract（lang='chi_sim+eng'）。两者均失败时抛出 RuntimeError。

        :param image_path: 图片文件路径
        :raises RuntimeError: LLM 和 pytesseract 均失败时
        :return: 识别出的文字内容
        """
        # 1. 尝试 LLM OCR
        try:
            return self._llm_ocr(image_path)
        except Exception as e:
            logger.warning("LLM OCR 失败，降级到 pytesseract：%s", e)

        # 2. 降级到 pytesseract
        try:
            return self._tesseract_ocr(image_path)
        except Exception as e:
            raise RuntimeError(f"OCR 识别失败（LLM 和 pytesseract 均不可用）：{e}") from e

    def extract_text_from_pdf_page(self, pdf_path: str, page_num: int) -> str:
        """
        将 PDF 指定页转为图片后提取文字。

        优先使用 pdf2image 将页面转为图片再调用 extract_text；
        若 pdf2image 不可用，则直接用 pytesseract 处理 PDF。

        :param pdf_path: PDF 文件路径
        :param page_num: 页码（从 0 开始）
        :raises RuntimeError: 所有方式均失败时
        :return: 识别出的文字内容
        """
        # 1. 尝试 pdf2image 转图片后 OCR
        try:
            return self._pdf_via_image(pdf_path, page_num)
        except ImportError:
            logger.warning("pdf2image 不可用，降级到 pytesseract 直接处理 PDF")
        except Exception as e:
            logger.warning("pdf2image 转换失败，降级到 pytesseract 直接处理 PDF：%s", e)

        # 2. 降级：pytesseract 直接处理 PDF
        try:
            return self._tesseract_pdf(pdf_path, page_num)
        except Exception as e:
            raise RuntimeError(f"PDF 第 {page_num} 页 OCR 失败：{e}") from e

    # ------------------------------------------------------------------
    # 私有辅助方法
    # ------------------------------------------------------------------

    def _llm_ocr(self, image_path: str) -> str:
        """读取图片为 base64，调用 LLM 视觉接口识别文字。"""
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的 OCR 助手，请准确识别图片中的所有文字，保持原有格式。",
            }
        ]
        return self._llm_service.chat_with_vision(messages, image_b64)

    def _tesseract_ocr(self, image_path: str) -> str:
        """使用 pytesseract 识别图片文字（中英文）。"""
        import pytesseract
        from PIL import Image

        image = Image.open(image_path)
        return pytesseract.image_to_string(image, lang="chi_sim+eng")

    def _pdf_via_image(self, pdf_path: str, page_num: int) -> str:
        """使用 pdf2image 将 PDF 指定页转为图片，再调用 extract_text。"""
        import tempfile
        import os
        from pdf2image import convert_from_path

        # convert_from_path 页码从 1 开始
        pages = convert_from_path(
            pdf_path,
            first_page=page_num + 1,
            last_page=page_num + 1,
        )
        if not pages:
            raise RuntimeError(f"PDF 第 {page_num} 页转换结果为空")

        page_image = pages[0]
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            page_image.save(tmp_path, format="PNG")
            return self.extract_text(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _tesseract_pdf(self, pdf_path: str, page_num: int) -> str:
        """直接用 pytesseract 处理 PDF（pdf2image 不可用时的降级方案）。"""
        import pytesseract
        from PIL import Image

        # Pillow 可以直接打开 PDF（需要 Ghostscript），按页读取
        image = Image.open(pdf_path)
        image.seek(page_num)
        return pytesseract.image_to_string(image, lang="chi_sim+eng")
