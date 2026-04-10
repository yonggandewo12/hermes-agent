# Documents 文档知识库 MemoryProvider 中文实施计划

## 目标

基于已确认的设计文档，实现一个独立的 `documents` MemoryProvider 插件，使 Hermes Agent 支持：

1. 启动时自动扫描 `~/.hermes/docs/` 下的 PDF/MD/TXT 文档并建立索引
2. 通过 `attach_document(path=...)` 工具在对话内即时上传并索引文档
3. 在每轮对话前通过 `prefetch()` 自动召回相关文档片段
4. 使用 FTS5 初筛 + HRR 重排完成混合检索

---

## 实施阶段拆分

### 阶段 1：插件骨架与注册

**目标**：让 `documents` provider 能被系统发现并初始化。

**任务**：
- 新建目录 `plugins/memory/documents/`
- 添加：
  - `__init__.py`
  - `plugin.yaml`
  - `provider.py`
- 在 `provider.py` 中实现 `MemoryProvider` 基本接口：
  - `name`
  - `is_available()`
  - `initialize()`
  - `prefetch()`
  - `get_tool_schemas()`
  - `handle_tool_call()`

**验收标准**：
- `memory.provider: documents` 时插件可正常注册
- 启动不会影响现有 builtin memory provider

---

### 阶段 2：SQLite 存储层

**目标**：实现文档元数据、chunk 数据与 FTS5 索引存储。

**任务**：
- 新建 `store.py`
- 定义并初始化：
  - `doc_meta`
  - `doc_chunks`
  - `doc_chunks_fts`
- 建立 `AFTER INSERT/UPDATE/DELETE` triggers，同步 FTS 表
- 实现基础 API：
  - upsert / replace 文档
  - 删除文档及其 chunks
  - 查询已有文档
  - 查询候选 chunks

**验收标准**：
- 可成功插入文档与 chunks
- 删除/更新后 FTS5 数据保持一致

---

### 阶段 3：文档解析与分块

**目标**：把 PDF/MD/TXT 解析为可索引文本块。

**任务**：
- 新建 `ingest.py`
- 实现：
  - `.txt/.md` 文本读取
  - `.pdf` 通过 `pymupdf` 提取文字
  - 文本清洗逻辑
  - 段落优先 + 字符回退的 chunking 规则
- 保证 `chunk_size` 与 `chunk_overlap` 可配置

**验收标准**：
- 三种文件类型都能输出稳定 chunk 列表
- 空文档、无文本 PDF 能正确处理

---

### 阶段 4：HRR 编码与检索器

**目标**：实现 query/chunk 同构编码与混合检索。

**任务**：
- 新建 `retrieval.py`
- 复用 `plugins/memory/holographic/holographic.py` 中的 HRR 能力
- 实现：
  - 文本归一化
  - token 化
  - token 级 `encode_atom`
  - `bundle` 生成文本向量
  - cosine similarity
- 实现检索流程：
  - FTS5 top 50 初筛
  - HRR 相似度重排
  - top K 返回

**验收标准**：
- 给定 query 能返回相关 chunk 列表
- 空 query / 无匹配场景返回空结果

---

### 阶段 5：provider 行为接入

**目标**：让 provider 真正具备启动扫描、对话前召回、上传索引能力。

**任务**：
- 在 `initialize()` 中扫描 `~/.hermes/docs/`
- 在 `prefetch()` 中返回 `<memory-context>` 文本块
- 在 `get_tool_schemas()` 中注册 `attach_document`
- 在 `handle_tool_call()` 中实现上传文档索引逻辑
- 明确：`sync_turn()` 不写入任何文档数据

**验收标准**：
- 启动时能自动建立目录索引
- 工具调用可即时导入文档
- 对话前能召回相关内容

---

### 阶段 6：配置与依赖接入

**目标**：使插件可通过配置启用，并具备运行依赖。

**任务**：
- 在配置中支持：
  - `documents.provider`
  - `knowledge_dir`
  - `retrieval_top_k`
  - `retrieval_candidate_count`
  - `chunk_size`
  - `chunk_overlap`
  - `supported_extensions`
- 补充依赖：
  - `pymupdf`
  - `numpy`（若未存在）

**验收标准**：
- 默认配置即可启动工作
- 自定义配置项能生效

---

### 阶段 7：测试

**目标**：补齐核心功能测试，确保检索和索引行为稳定。

**建议测试覆盖**：
- provider 注册与初始化
- SQLite schema 创建
- 文档插入 / 更新 / 删除
- chunking 规则正确性
- PDF 文本提取
- `attach_document` 成功与失败路径
- `prefetch()` 的无匹配 / 有匹配场景
- FTS5 + HRR 混合排序基本正确性

**验收标准**：
- 关键路径具备自动化测试
- 不引入现有 memory provider 回归问题

---

## 推荐实施顺序

1. 插件骨架与注册
2. SQLite 存储层
3. 文档解析与分块
4. HRR 编码与检索器
5. provider 行为接入
6. 配置与依赖接入
7. 自动化测试与验收

---

## 风险点

### 1. HRR 文本表示效果有限
当前方案不使用外部 embedding 模型，HRR 更像轻量语义重排。实际效果可能依赖 token 化与 chunk 质量。

**控制策略**：
- 保持 FTS5 为主召回
- HRR 只做重排
- 优先保证 chunking 质量

### 2. PDF 提取质量不稳定
不同 PDF 的文字层质量差异较大，可能导致抽取文本噪声高。

**控制策略**：
- 明确错误返回
- 对目录扫描采用“单文件失败不中断”策略

### 3. 上传文档状态管理复杂度扩张
如果后续增加删除、覆盖更新、来源过滤，状态模型会变复杂。

**控制策略**：
- 本期只支持“上传即新增”
- 删除/覆盖更新明确延后

---

## 本期完成标准

当以下条件全部满足时，可视为本期功能完成：

- `documents` provider 可配置启用
- `~/.hermes/docs/` 可在启动时自动扫描索引
- `attach_document(path=...)` 可导入 PDF/MD/TXT
- `prefetch()` 能自动返回相关文档片段
- 检索路径使用 FTS5 + HRR 重排
- 核心行为有自动化测试覆盖
- 不影响现有 memory provider 机制
