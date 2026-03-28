# 需求文档

## 简介

学科学习助手是一个基于 RAG（检索增强生成）技术的 Web 应用，帮助学生和自学者将学习资料（PDF/Word/PPT/TXT/Markdown）上传至系统，并通过自然语言问答和结构化解题功能，仅基于已上传资料进行智能辅导。系统采用 Python + Streamlit 构建前端，Supabase PostgreSQL + pgvector 存储向量数据，OpenAI 兼容接口（支持硅基流动）提供 LLM 和 Embedding 能力。

---

## 词汇表

- **系统（System）**：学科学习助手 Web 应用整体
- **用户（User）**：已注册并登录的使用者
- **学科（Subject）**：用户创建的学习主题单元，包含名称、分类、描述
- **资料（Document）**：用户上传的学习文件（PDF/Word/PPT/TXT/Markdown）
- **文本块（Chunk）**：资料经解析和分块后的最小文本单元，附带向量嵌入
- **向量存储（VectorStore）**：基于 langchain-postgres PGVector 的向量检索组件，按 subject_id 隔离 collection
- **会话（Session）**：一次连续的问答或解题交互记录
- **RAG 流水线（RAG_Pipeline）**：检索增强生成流程，包含向量检索和 LLM 调用
- **嵌入服务（Embedding_Service）**：调用 OpenAI 兼容接口生成文本向量的组件
- **LLM 服务（LLM_Service）**：调用 OpenAI 兼容接口生成自然语言回答的组件
- **认证模块（Auth_Module）**：负责注册、登录、会话状态管理的组件
- **数据库（Database）**：Supabase PostgreSQL 实例，通过 SQLAlchemy 懒加载连接
- **思维导图（MindMap）**：以可视化层级结构展示知识点及其关联关系的图形，由 LLM 分析资料后生成，采用 Mermaid 或 markmap 格式渲染
- **历年题（PastExam）**：用户上传的历年考试试题文件，与普通学习资料分开存储，关联到对应学科
- **OCR 服务（OCR_Service）**：对图片格式或扫描版 PDF 进行光学字符识别，将图像中的文字转换为可处理文本的组件
- **预测试卷（PredictedPaper）**：由 AI 根据历年题的考点分布、题型比例和学科资料自动生成的模拟试卷

---

## 需求

### 需求 1：用户注册

**用户故事：** 作为访客，我希望能够注册账号，以便使用学科学习助手的全部功能。

#### 验收标准

1. THE 系统（System）SHALL 提供用户名和密码的注册表单。
2. WHEN 用户提交注册表单时，THE Auth_Module SHALL 使用 bcrypt 对密码进行哈希加密后存入 users 表。
3. IF 用户名已存在，THEN THE Auth_Module SHALL 向用户显示"用户名已被占用"的错误提示。
4. IF 用户名为空或密码长度小于 6 个字符，THEN THE Auth_Module SHALL 向用户显示具体的字段校验错误信息。
5. WHEN 注册成功后，THE System SHALL 自动将用户登录并跳转至主界面。

---

### 需求 2：用户登录与登出

**用户故事：** 作为注册用户，我希望能够登录和登出，以便安全地管理我的学习数据。

#### 验收标准

1. THE System SHALL 提供用户名和密码的登录表单。
2. WHEN 用户提交正确的用户名和密码时，THE Auth_Module SHALL 将用户信息写入 Streamlit session_state，并跳转至主界面。
3. IF 用户名不存在或密码错误，THEN THE Auth_Module SHALL 向用户显示"用户名或密码错误"的提示，不区分具体原因。
4. WHILE 用户处于登录状态时，THE System SHALL 在所有页面持久保持登录状态，不因 Streamlit rerun 而丢失。
5. WHEN 用户点击登出时，THE Auth_Module SHALL 清除 session_state 中的用户信息并跳转至登录页。

---

### 需求 3：学科管理

**用户故事：** 作为登录用户，我希望能够创建和删除学科，以便按主题组织我的学习资料。

#### 验收标准

1. WHEN 用户提交包含名称、分类、描述的学科创建表单时，THE System SHALL 将学科记录写入 subjects 表并关联当前用户 ID。
2. IF 学科名称为空，THEN THE System SHALL 向用户显示"学科名称不能为空"的错误提示。
3. THE System SHALL 仅展示当前登录用户创建的学科列表，不显示其他用户的学科。
4. WHEN 用户确认删除某学科时，THE System SHALL 级联删除该学科下的所有资料、文本块、会话及对话历史记录。
5. IF 删除操作失败，THEN THE System SHALL 向用户显示错误信息并保持数据不变。

---

### 需求 4：资料上传与向量化

**用户故事：** 作为登录用户，我希望能够上传学习资料，以便系统将其向量化后用于问答检索。

#### 验收标准

1. THE System SHALL 支持上传 PDF、Word（.docx）、PPT（.pptx）、TXT、Markdown 格式的文件。
2. WHEN 用户上传文件时，THE System SHALL 将文件临时保存至 /tmp 目录，处理完成后立即删除，不依赖持久化文件系统。
3. WHEN 文件上传后，THE System SHALL 解析文件文本内容，按不超过 1000 字符（含 200 字符重叠）进行分块，调用 Embedding_Service 生成向量，并将文本块和向量存入 VectorStore 的对应 subject_id collection。
4. THE System SHALL 仅在数据库写入和向量化均成功完成后，将 documents 表中该文件的 status 字段更新为 "completed"。
5. IF 文件解析或向量化过程中发生错误，THEN THE System SHALL 将 documents 表中该文件的 status 字段更新为 "failed"，并将错误信息写入 error 字段。
6. WHILE 文件正在处理时，THE System SHALL 在界面上显示处理进度状态，防止用户重复提交同一文件。
7. IF 用户在同一 Streamlit session 中重复上传相同文件名的文件，THEN THE System SHALL 通过 session_state 标记已处理文件，避免重复向量化。

---

### 需求 5：资料列表与删除

**用户故事：** 作为登录用户，我希望能够查看和删除已上传的资料，以便管理学科内容。

#### 验收标准

1. THE System SHALL 在学科详情页展示该学科下所有已上传资料的列表，包含文件名、上传时间、处理状态。
2. WHEN 用户确认删除某资料时，THE System SHALL 从 documents 表删除该记录，并从 VectorStore 中删除该文件对应的所有文本块向量。
3. IF 删除操作失败，THEN THE System SHALL 向用户显示错误信息并保持数据不变。

---

### 需求 6：学科内问答（RAG）

**用户故事：** 作为登录用户，我希望能够在学科内提问，以便基于已上传资料获得智能回答。

#### 验收标准

1. WHEN 用户在某学科内提交问题时，THE RAG_Pipeline SHALL 从该学科的 VectorStore collection 中检索最相关的 5 个文本块。
2. WHEN 检索完成后，THE LLM_Service SHALL 将检索到的文本块作为上下文，结合用户问题调用 LLM 生成回答，回答中不得引用上传资料以外的知识。
3. THE System SHALL 在回答中标注所引用的资料来源（文件名和文本块片段）。
4. IF 该学科下没有已完成向量化的资料，THEN THE System SHALL 向用户显示"该学科暂无可用资料，请先上传学习材料"的提示，不调用 LLM。
5. WHEN 问答完成后，THE System SHALL 将问题和回答自动保存至 conversation_history 表，关联当前会话 ID。
6. WHEN RAG_Pipeline 检索到的文本块与用户问题的相关性不足时，THE System SHALL 依照需求 11 所定义的智能知识范围识别流程处理该问答请求。

---

### 需求 7：学科内解题

**用户故事：** 作为登录用户，我希望能够提交题目获得结构化解题过程，以便系统性地理解解题思路。

#### 验收标准

1. WHEN 用户在某学科内提交题目时，THE RAG_Pipeline SHALL 从该学科的 VectorStore collection 中检索最相关的 5 个文本块作为参考资料。
2. WHEN 检索完成后，THE LLM_Service SHALL 基于检索到的文本块，按照"考点 → 解题思路 → 解题步骤 → 踩分点 → 易错点"的结构化格式生成解题过程。
3. THE System SHALL 以分区块的方式在界面上展示结构化解题结果的每个部分。
4. IF 该学科下没有已完成向量化的资料，THEN THE System SHALL 向用户显示"该学科暂无可用资料，请先上传学习材料"的提示，不调用 LLM。
5. WHEN 解题完成后，THE System SHALL 将题目和结构化解题结果自动保存至 conversation_history 表，关联当前会话 ID。
6. WHEN RAG_Pipeline 检索到的文本块与用户题目的相关性不足时，THE System SHALL 依照需求 11 所定义的智能知识范围识别流程处理该解题请求。

---

### 需求 8：对话历史管理

**用户故事：** 作为登录用户，我希望能够查看、删除和导出对话历史，以便回顾和整理学习记录。

#### 验收标准

1. THE System SHALL 按会话（conversation_sessions）分组展示当前用户的对话历史列表，每条记录显示会话标题、学科名称、创建时间。
2. WHEN 用户点击某会话时，THE System SHALL 展示该会话下的完整对话记录，包含问题、回答、时间戳。
3. WHEN 用户确认删除某会话时，THE System SHALL 从 conversation_sessions 表和 conversation_history 表中删除该会话及其所有对话记录。
4. WHEN 用户点击导出某会话时，THE System SHALL 将该会话的完整对话记录格式化为 Markdown 文本，并提供文件下载。
5. IF 删除操作失败，THEN THE System SHALL 向用户显示错误信息并保持数据不变。

---

### 需求 9：配置管理

**用户故事：** 作为系统管理员，我希望所有敏感配置从 Streamlit Secrets 读取，以便安全地部署应用。

#### 验收标准

1. THE System SHALL 从 Streamlit Secrets 读取以下配置项：DATABASE_URL、LLM_API_KEY、LLM_BASE_URL、LLM_CHAT_MODEL、LLM_EMBEDDING_MODEL。
2. THE Database SHALL 采用 SQLAlchemy 懒加载模式，仅在首次实际使用时建立数据库连接，不在模块导入时建立连接。
3. IF 任意必需配置项缺失，THEN THE System SHALL 在启动时向用户显示明确的配置缺失错误信息，并终止初始化流程。
4. THE VectorStore SHALL 使用 langchain-postgres 包的 PGVector 实现，不使用已废弃的 langchain-community PGVector。

---

### 需求 10：数据隔离与安全

**用户故事：** 作为登录用户，我希望我的数据与其他用户完全隔离，以便保护学习隐私。

#### 验收标准

1. THE System SHALL 在所有数据库查询中强制过滤 user_id，确保用户只能访问自己的学科、资料和对话历史。
2. THE VectorStore SHALL 按 subject_id 创建独立的 PGVector collection，确保不同学科的向量数据互不干扰。
3. WHILE 用户未登录时，THE System SHALL 拒绝所有资料上传、问答、解题和历史查询请求，并跳转至登录页。

---

### 需求 11：智能知识范围识别

**用户故事：** 作为登录用户，当已上传资料与我的问题或题目关联度不足时，我希望系统能主动提示并允许我选择是否拓宽知识范围，以便在资料不足时仍能获得有效帮助。

#### 验收标准

1. WHEN RAG_Pipeline 完成检索后，THE System SHALL 计算检索到的文本块与用户输入的相关性得分，并与预设阈值进行比较。
2. WHEN 所有检索到的文本块的相关性得分均低于预设阈值时，THE System SHALL 判定为"资料相关性不足"，不直接调用 LLM 生成回答。
3. WHEN 系统判定资料相关性不足时，THE System SHALL 向用户展示提示信息，说明已上传资料中未找到与该问题/题目高度相关的内容，并询问用户是否拓宽知识范围。
4. THE System SHALL 向用户提供以下两个明确选项：① 仅基于已上传资料回答；② 拓宽范围，结合通用知识回答。
5. WHEN 用户选择"仅基于已上传资料"时，THE LLM_Service SHALL 仅以检索到的文本块为上下文生成回答，保持与需求 6、需求 7 的原有行为一致。
6. WHEN 用户选择"拓宽范围，结合通用知识"时，THE LLM_Service SHALL 结合检索到的文本块与 LLM 自身的通用知识共同生成回答。
7. WHEN LLM_Service 基于拓宽范围模式生成回答时，THE System SHALL 在回答中明确区分并标注每段内容的来源，注明"来自上传资料"或"来自通用知识"。
8. THE System SHALL 将用户的知识范围选择及最终回答一并保存至 conversation_history 表，关联当前会话 ID。
9. IF 用户未作出选择即关闭提示，THEN THE System SHALL 取消本次问答或解题请求，不调用 LLM。

---

### 需求 12：课本分析与思维导图

**用户故事：** 作为登录用户，我希望能够对已上传的资料生成思维导图，以便直观地理解知识结构和章节层级。

#### 验收标准

1. THE System SHALL 允许用户选择某个已上传资料或某学科下的全部资料，作为思维导图的生成来源。
2. WHEN 用户触发思维导图生成时，THE LLM_Service SHALL 基于所选资料的文本块，分析章节层级、核心概念及知识点之间的关联关系，生成 Mermaid 或 markmap 格式的思维导图内容。
3. WHEN 思维导图内容生成完成后，THE System SHALL 在界面上以可视化方式渲染并展示该思维导图。
4. THE System SHALL 在思维导图中体现章节层级、核心概念以及知识点之间的关联关系。
5. WHEN 用户点击导出时，THE System SHALL 将思维导图内容以 Markdown/Mermaid 格式提供文件下载。
6. IF 所选资料下没有已完成向量化的文本块，THEN THE System SHALL 向用户显示"所选资料暂无可用内容，请先完成资料上传与处理"的提示，不调用 LLM。

---

### 需求 13：历年题上传与 OCR 识别

**用户故事：** 作为登录用户，我希望能够上传历年试题文件并让系统自动识别和结构化题目内容，以便后续进行考点分析和 AI 出题。

#### 验收标准

1. THE System SHALL 支持上传 PDF、图片（JPG/PNG）、Word（.docx）格式的历年试题文件。
2. WHEN 用户上传图片格式文件或扫描版 PDF 时，THE OCR_Service SHALL 对文件内容进行光学字符识别，将图像中的文字转换为可处理的文本。
3. WHEN OCR 识别完成后，THE System SHALL 对识别文本进行清洗，并按题目进行分割，将每道题结构化存储为包含题号、题目内容、答案/解析（如有）的记录。
4. THE System SHALL 将历年题数据存储在独立于普通学习资料的数据表中，并关联到对应学科。
5. THE System SHALL 在学科详情页展示该学科下已上传的历年题列表，包含文件名、上传时间、处理状态。
6. WHEN 用户确认删除某份历年题文件时，THE System SHALL 从历年题数据表中删除该文件及其所有关联题目记录。
7. IF 文件解析或 OCR 识别过程中发生错误，THEN THE System SHALL 将该文件的状态标记为"处理失败"，并向用户显示具体错误信息。

---

### 需求 14：预测试卷与 AI 出题

**用户故事：** 作为登录用户，我希望能够基于历年题和学科资料让 AI 生成预测试卷或按需出题，以便高效备考。

#### 验收标准

1. WHEN 用户触发预测试卷生成时，THE LLM_Service SHALL 基于该学科已上传的历年题，分析高频考点、题型分布和难度分布，结合学科资料自动生成一套模拟试卷。
2. IF 用户触发预测试卷生成时该学科下没有已上传的历年题，THEN THE System SHALL 向用户显示"预测试卷功能需要先上传历年题，请先上传历年试题文件"的提示，不调用 LLM。
3. WHEN 用户使用 AI 出题功能时，THE System SHALL 允许用户指定题型（选择题/填空题/简答题/计算题）、题目数量、难度等级和考点范围。
4. WHEN 用户提交 AI 出题请求时，THE LLM_Service SHALL 按照用户指定的参数生成对应题目及参考答案。
5. THE System SHALL 在没有上传历年题的情况下仍允许用户使用 AI 出题功能，基于学科资料生成题目。
6. WHEN 试卷或题目生成完成后，THE System SHALL 将生成结果保存至 conversation_history 表，关联当前会话 ID。
7. WHEN 用户点击导出时，THE System SHALL 将生成的试卷或题目以 Markdown 格式提供文件下载。
