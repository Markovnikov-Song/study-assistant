# 📚 学科学习助手

基于 RAG（检索增强生成）技术的 AI 学习辅助 Web 应用。上传你的教材、课件、笔记，即可进行智能问答、结构化解题、思维导图生成和 AI 出题。

🔗 **在线访问**：[https://study-assistant-markovnikov.streamlit.app](https://study-assistant-markovnikov.streamlit.app)

---

## 核心功能

- **智能问答**：基于已上传资料回答问题，可选择结合通用知识，支持上传/粘贴图片提问
- **结构化解题**：按「考点 → 解题思路 → 解题步骤 → 踩分点 → 易错点」输出，支持图片题目识别
- **思维导图**：分析全书知识结构，生成可交互的思维导图，支持折叠/展开
- **历年题管理**：上传历年试题（PDF/图片/Word），AI 自动识别题目结构
- **AI 出题**：基于历年题生成预测试卷，或按题型/难度/考点自定义出题
- **对话历史**：自动保存，支持导出为 Markdown / HTML / Word

---

## 上传资料说明

支持格式：**PDF、Word (.docx)、PPT (.pptx)、TXT、Markdown**

> ⚠️ **不支持扫描版 PDF**（图片扫描的 PDF，无法用鼠标选中文字的那种）
>
> 请先转换为文字版再上传：
> - [ilovepdf.com](https://www.ilovepdf.com/zh-cn/pdf_to_word) — 免费 PDF 转 Word
> - [smallpdf.com](https://smallpdf.com/cn/pdf-to-word) — 免费 PDF 转 Word

---

## 技术栈

- 前端/框架：Streamlit
- 数据库：Neon PostgreSQL + pgvector
- 向量存储：langchain-postgres PGVector
- LLM/Embedding：OpenAI 兼容接口（硅基流动）
