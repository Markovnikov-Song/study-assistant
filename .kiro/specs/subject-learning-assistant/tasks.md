# 实现计划：学科学习助手

## 概述

基于 RAG 技术的学科学习助手，采用纯 Streamlit + Neon PostgreSQL + pgvector + OpenAI 兼容接口（硅基流动）实现。按模块逐步构建，从基础设施到服务层再到页面层，最终完成集成。

## 任务

- [x] 1. 项目基础设施：配置与数据库模块
  - [x] 1.1 创建 `config.py`，从 `st.secrets` 读取所有配置项，启动时校验必需项并在缺失时抛出明确错误
    - 必需项：DATABASE_URL、LLM_API_KEY、LLM_BASE_URL、LLM_CHAT_MODEL、LLM_EMBEDDING_MODEL
    - 可选项含默认值：SIMILARITY_THRESHOLD=0.3、CHUNK_SIZE=1000、CHUNK_OVERLAP=200、TOP_K=5
    - _需求：9.1, 9.3_

  - [ ]* 1.2 为 `config.py` 编写属性测试
    - **属性 16：配置缺失错误提示**
    - **验证需求：9.3**

  - [x] 1.3 创建 `database.py`，实现 SQLAlchemy 懒加载 engine、session 工厂，以及所有表的 DDL（users、subjects、documents、chunks、conversation_sessions、conversation_history、past_exam_files、past_exam_questions）
    - engine 在首次调用 `get_engine()` 时才创建，模块导入时不建立连接
    - 使用 `pool_pre_ping=True` 保证连接健康
    - _需求：9.2, 3.4_

- [x] 2. 认证服务（`services/auth_service.py`）
  - [x] 2.1 实现 `AuthService`：`register`、`login`、`logout`、`get_current_user` 方法
    - `register`：bcrypt 加密密码，写入 users 表；用户名为空或密码 < 6 字符时返回字段级错误；用户名重复时返回"用户名已被占用"
    - `login`：验证密码，成功后写入 `session_state["user"]`；失败时不区分原因，返回统一提示
    - `logout`：清除 `session_state["user"]`
    - `get_current_user`：从 `session_state` 读取，返回 `Optional[User]`
    - _需求：1.2, 1.3, 1.4, 2.2, 2.3, 2.5_

  - [ ]* 2.2 为 `AuthService` 编写属性测试
    - **属性 1：密码哈希不可逆存储**
    - **验证需求：1.2**

  - [ ]* 2.3 为 `AuthService` 编写属性测试
    - **属性 2：注册输入验证**
    - **验证需求：1.3, 1.4**

  - [ ]* 2.4 为 `AuthService` 编写属性测试
    - **属性 3：登录验证与状态管理**
    - **验证需求：2.2, 2.3, 2.5**

  - [ ]* 2.5 为 `AuthService` 编写属性测试
    - **属性 4：登录状态持久性**
    - **验证需求：2.4**

- [ ] 3. 检查点 —— 确保所有测试通过，如有疑问请向用户确认

- [x] 4. LLM 与 Embedding 服务（`services/llm_service.py`、`services/embedding_service.py`）
  - [x] 4.1 实现 `LLMService`：`chat`、`chat_with_vision`、`stream_chat` 方法
    - 使用 `openai` 库，`base_url` 和 `api_key` 从 `config` 读取
    - LLM 调用失败时捕获异常，不保存历史，向上层返回错误
    - _需求：6.2, 7.2, 9.1_

  - [x] 4.2 实现 `EmbeddingService`：`embed_texts`、`embed_query` 方法
    - 调用 OpenAI 兼容接口，模型名从 `config.LLM_EMBEDDING_MODEL` 读取
    - _需求：4.3, 9.1_

- [x] 5. OCR 服务（`services/ocr_service.py`）
  - [x] 5.1 实现 `OCRService.extract_text`：优先调用 LLM 视觉能力，失败时降级到 pytesseract
    - LLM OCR 失败时静默降级，记录日志；两者均失败时向上层抛出异常
    - _需求：13.2_

- [x] 6. 文档服务（`services/document_service.py`）
  - [x] 6.1 实现文件解析器：`parse_file(tmp_path, filename) -> str`
    - `.pdf` → pdfplumber（扫描版触发 OCR）；`.docx` → python-docx；`.pptx` → python-pptx；`.txt`/`.md` → 直接读取
    - _需求：4.1_

  - [x] 6.2 实现 `chunk_text(text) -> List[str]`，按 CHUNK_SIZE/CHUNK_OVERLAP 分块
    - _需求：4.3_

  - [ ]* 6.3 为 `chunk_text` 编写属性测试
    - **属性 7：文本分块规则**
    - **验证需求：4.3**

  - [x] 6.4 实现 `upload_and_process(file, subject_id, user_id) -> Result`
    - 文件写入 `/tmp/{uuid}_{filename}`，使用 `try/finally` 确保临时文件始终删除
    - 流程：写 documents 记录（status=pending）→ 解析 → 分块 → 向量化 → 写 chunks → 更新 status=completed
    - 任一步骤失败时更新 status=failed 并写入 error 字段
    - _需求：4.2, 4.4, 4.5_

  - [ ]* 6.5 为文件处理流程编写属性测试
    - **属性 6：文件处理后临时文件清理**
    - **验证需求：4.2**

  - [ ]* 6.6 为文件处理流程编写属性测试
    - **属性 8：文档状态一致性**
    - **验证需求：4.4, 4.5**

  - [x] 6.7 实现 `list_documents`、`delete_document`，删除时同步清除 PGVector 中对应向量
    - _需求：5.1, 5.2, 5.3_

  - [ ]* 6.8 为防重复上传逻辑编写属性测试
    - **属性 9：防重复上传**
    - **验证需求：4.7**

- [ ] 7. 检查点 —— 确保所有测试通过，如有疑问请向用户确认

- [x] 8. RAG 流水线（`services/rag_pipeline.py`）
  - [x] 8.1 实现 `RAGPipeline.query`：向量检索 → 相关性评分 → 阈值判断 → LLM 调用 → 保存历史
    - 使用 langchain-postgres PGVector，collection 命名为 `subject_{subject_id}`
    - 检索 Top-K 文本块，计算 cosine similarity
    - 低于阈值时返回 `RAGResult(needs_confirmation=True)`，不调用 LLM
    - 问答模式 prompt：仅基于上下文回答，不引用外部知识
    - 解题模式 prompt：按"考点 → 解题思路 → 解题步骤 → 踩分点 → 易错点"结构化输出
    - _需求：6.1, 6.2, 6.3, 7.1, 7.2, 11.1, 11.2_

  - [ ]* 8.2 为 RAG 检索范围编写属性测试
    - **属性 10：RAG 检索范围隔离**
    - **验证需求：6.1, 10.2**

  - [ ]* 8.3 为相关性阈值判断编写属性测试
    - **属性 11：相关性阈值判断**
    - **验证需求：11.1, 11.2**

  - [x] 8.4 实现拓宽范围模式：用户选择后以 broad 模式调用 LLM，回答中标注"来自上传资料"/"来自通用知识"
    - 将 `scope_choice` 字段写入 `conversation_history`
    - _需求：11.5, 11.6, 11.7, 11.8_

  - [ ]* 8.5 为对话历史保存编写属性测试
    - **属性 12：对话历史完整保存**
    - **验证需求：6.5, 11.8**

- [x] 9. 思维导图服务（`services/mindmap_service.py`）
  - [x] 9.1 实现 `MindMapService.generate`：基于文本块调用 LLM 生成 Mermaid/markmap 格式思维导图
    - _需求：12.2, 12.4_

  - [x] 9.2 实现 `MindMapService.render`：调用 `st.markdown` 或 streamlit-markmap 渲染
    - _需求：12.3_

- [x] 10. 出题服务（`services/exam_service.py`）
  - [x] 10.1 实现 `ExamService.process_past_exam_file`：解析历年题文件，OCR 识别，按题目分割，写入 `past_exam_files` 和 `past_exam_questions` 表
    - 不向 `documents` 或 `chunks` 表写入任何记录
    - _需求：13.1, 13.2, 13.3, 13.4_

  - [ ]* 10.2 为历年题数据表隔离编写属性测试
    - **属性 13：历年题数据表隔离**
    - **验证需求：13.4**

  - [x] 10.3 实现 `ExamService.generate_predicted_paper`：基于历年题分析考点分布，结合学科资料生成预测试卷
    - 无历年题时返回提示，不调用 LLM
    - _需求：14.1, 14.2_

  - [x] 10.4 实现 `ExamService.generate_custom_questions`：按用户指定题型、数量、难度、考点范围出题
    - 无历年题时仍可基于学科资料出题
    - _需求：14.3, 14.4, 14.5_

- [ ] 11. 检查点 —— 确保所有测试通过，如有疑问请向用户确认

- [x] 12. 数据隔离与安全
  - [x] 12.1 在 `document_service.py`、`rag_pipeline.py`、`exam_service.py` 的所有数据库查询中强制过滤 `user_id`
    - _需求：10.1_

  - [ ]* 12.2 为用户数据隔离编写属性测试
    - **属性 5：用户数据隔离**
    - **验证需求：3.3, 8.1, 10.1**

  - [x] 12.3 实现未登录访问拦截装饰器或工具函数，在所有需要认证的页面入口处调用
    - 未登录时跳转至登录页，不返回任何数据
    - _需求：10.3_

  - [ ]* 12.4 为未登录访问拦截编写属性测试
    - **属性 15：未登录访问拦截**
    - **验证需求：10.3**

- [x] 13. 页面层：登录/注册页（`pages/login.py`）
  - [x] 13.1 实现登录表单和注册表单，调用 `AuthService`，成功后跳转主界面
    - 注册成功后自动登录
    - _需求：1.1, 1.5, 2.1_

- [x] 14. 页面层：学科管理页（`pages/subjects.py`）
  - [x] 14.1 实现学科列表展示（仅当前用户）、创建表单、删除确认
    - 删除时级联清理所有关联数据
    - _需求：3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 14.2 为级联删除完整性编写属性测试
    - **属性 14：级联删除完整性**
    - **验证需求：3.4**

- [x] 15. 页面层：学科详情页（`pages/subject_detail.py`）
  - [x] 15.1 实现资料上传组件：文件选择、防重复检查（`session_state["uploaded_files"]`）、处理进度展示、资料列表与删除
    - _需求：4.6, 4.7, 5.1, 5.2, 5.3_

  - [x] 15.2 实现问答组件：输入框、调用 `RAGPipeline.query`、展示回答与来源引用、相关性不足时展示确认选项
    - _需求：6.1, 6.2, 6.3, 6.4, 11.3, 11.4, 11.5, 11.6, 11.7, 11.9_

  - [x] 15.3 实现解题组件：输入框、调用 `RAGPipeline.query(mode="solve")`、分区块展示结构化解题结果
    - _需求：7.1, 7.2, 7.3, 7.4_

- [x] 16. 页面层：对话历史页（`pages/history.py`）
  - [x] 16.1 实现会话列表（按 conversation_sessions 分组）、会话详情展示、删除确认、Markdown 导出下载
    - _需求：8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 17. 页面层：思维导图页（`pages/mindmap.py`）
  - [x] 17.1 实现资料选择（单份或全部）、触发生成、渲染展示、Mermaid 格式导出下载
    - 无可用文本块时显示提示，不调用 LLM
    - _需求：12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 18. 页面层：历年题管理页（`pages/past_exams.py`）
  - [x] 18.1 实现历年题文件上传、处理状态展示、题目列表查看、删除确认
    - _需求：13.1, 13.5, 13.6, 13.7_

- [x] 19. 页面层：AI 出题页（`pages/exam_generator.py`）
  - [x] 19.1 实现预测试卷生成触发、AI 出题参数表单（题型/数量/难度/考点）、结果展示、Markdown 导出下载
    - 结果保存至 conversation_history
    - _需求：14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

- [x] 20. 应用入口（`app.py`）
  - [x] 20.1 创建 `app.py`，配置 `st.navigation` 或侧边栏页面路由，初始化时调用 `config` 校验，未登录时强制跳转登录页
    - _需求：9.3, 10.3_

- [ ] 21. 最终检查点 —— 确保所有测试通过，如有疑问请向用户确认

## 备注

- 标有 `*` 的子任务为可选测试任务，可跳过以加快 MVP 进度
- 每个任务均引用了对应需求条款，便于追溯
- 属性测试使用 Hypothesis 库，每个属性最少运行 100 次迭代
- 属性测试注释格式：`# Feature: subject-learning-assistant, Property {N}: {property_text}`
- 所有配置从 `st.secrets` 读取，不硬编码任何密钥或连接串
