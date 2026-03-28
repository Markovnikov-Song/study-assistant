# 📚 学科学习助手

基于 RAG（检索增强生成）技术的学习辅助 Web 应用，支持上传学习资料后进行智能问答、结构化解题、思维导图生成和 AI 出题。

🔗 **在线访问**：[https://study-assistant-markovnikov.streamlit.app](https://study-assistant-markovnikov.streamlit.app)

---

## 功能

- **问答**：基于已上传资料回答问题，可选择结合通用知识
- **解题**：结构化输出（考点 → 解题思路 → 解题步骤 → 踩分点 → 易错点）
- **思维导图**：分析资料知识结构，生成可视化思维导图
- **历年题管理**：上传历年试题，AI 识别题目结构
- **AI 出题**：基于历年题生成预测试卷，或按需自定义出题
- **对话历史**：自动保存，支持导出为 Markdown / HTML / Word

---

## 上传资料说明

支持格式：**PDF、Word (.docx)、PPT (.pptx)、TXT、Markdown**

> ⚠️ **不支持扫描版 PDF**（即图片扫描的 PDF，无法用鼠标选中文字的那种）
>
> 如果你的 PDF 是扫描版，请先转换为文字版再上传：
> - [ilovepdf.com](https://www.ilovepdf.com/zh-cn/pdf_to_word) — 免费 PDF 转 Word
> - [smallpdf.com](https://smallpdf.com/cn/pdf-to-word) — 免费 PDF 转 Word
>
> 转换后上传 `.docx` 文件效果最佳。

---

## 技术栈

- 前端/框架：Streamlit
- 数据库：Neon PostgreSQL + pgvector
- 向量存储：langchain-postgres PGVector
- LLM/Embedding：OpenAI 兼容接口（硅基流动）
