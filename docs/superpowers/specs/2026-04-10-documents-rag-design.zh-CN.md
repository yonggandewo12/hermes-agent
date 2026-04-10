# Documents 文档知识库 MemoryProvider 设计文档

## 1. 概述

**名称**：`documents` MemoryProvider 插件  
**类型**：独立的可插拔 memory provider  
**目标**：为 Agent 提供本地文档知识库的自动召回能力，在对话前自动注入相关文档片段。  
**机制**：文档索引 → 独立 SQLite 存储 → `prefetch()` 混合检索召回。

`documents` provider 的职责边界如下：
- 负责固定目录 `~/.hermes/docs/` 的启动扫描
- 负责提供 `attach_document(path=...)` 工具，处理对话内即时上传并建立索引
- 负责文档解析、分块、建库、检索与 `prefetch()` 注入
- 不负责对话事实记忆，不消费 `sync_turn()` 对话内容，不处理 URL 抓取，不处理多模态内容

## 2. 架构

```text
固定目录扫描 / attach_document(path)
               │
               ▼
┌──────────────────────┐
│   DocumentIngester   │  ← 解析 PDF/MD/TXT，统一输出纯文本
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│     TextChunker      │  ← 优先按段落切分，超长再按字符数切分并保留 overlap
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      HRREncoder      │  ← token -> encode_atom(token) -> bundle -> normalize
└──────────┬───────────┘
           ▼
┌──────────────────────────────────────────────┐
│              DocumentsSQLiteStore            │
│  ┌─────────────┐   ┌───────────────┐         │
│  │  doc_meta   │   │   doc_chunks  │         │
│  │ doc_id      │   │ chunk_id      │         │
│  │ content_hash│   │ content       │         │
│  │ source_path │   │ hrr_vector    │         │
│  └─────────────┘   └───────────────┘         │
│               + doc_chunks_fts (FTS5)        │
└──────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                 DocRetriever                 │
│          FTS5 候选召回 + HRR 重排            │
└──────────────────────────────────────────────┘
                       │
                       ▼
            <memory-context> 注入给模型
```

## 3. 目录结构

```text
plugins/memory/documents/
├── __init__.py
├── plugin.yaml              # 插件注册配置
├── provider.py              # DocumentsMemoryProvider
├── store.py                 # SQLite schema / triggers / CRUD
├── ingest.py                # DocumentIngester + TextChunker
├── retrieval.py             # FTS5 初筛 + HRR 重排
└── utils.py                 # 文本归一化、PDF 提取辅助函数
```

## 4. 数据模型

### `doc_meta`

| 字段 | 类型 | 说明 |
|------|------|------|
| `doc_id` | TEXT PRIMARY KEY | 稳定文档标识 |
| `filename` | TEXT NOT NULL | 文件名 |
| `source_path` | TEXT | 原始路径 |
| `source_type` | TEXT NOT NULL | `directory` / `upload` |
| `content_hash` | TEXT NOT NULL | 当前文件内容哈希 |
| `indexed_at` | TEXT NOT NULL | ISO 时间戳 |

`doc_id` 生成规则：
- 目录文档：`sha256("directory:" + normalized_source_path)`
- 上传文档：`sha256("upload:" + filename + ":" + first_seen_at)`

### `doc_chunks`

| 字段 | 类型 | 说明 |
|------|------|------|
| `chunk_id` | INTEGER PRIMARY KEY AUTOINCREMENT | chunk 主键 |
| `doc_id` | TEXT NOT NULL | 关联 `doc_meta.doc_id` |
| `chunk_index` | INTEGER NOT NULL | 文档内顺序 |
| `content` | TEXT NOT NULL | chunk 文本 |
| `hrr_vector` | BLOB NOT NULL | HRR 向量序列化结果 |
| `created_at` | TEXT NOT NULL | ISO 时间戳 |

### `doc_chunks_fts`

采用 external-content FTS5：

```sql
CREATE VIRTUAL TABLE doc_chunks_fts
USING fts5(content, content=doc_chunks, content_rowid=chunk_id);
```

并通过 `AFTER INSERT/UPDATE/DELETE` triggers 自动同步 FTS 表。

## 5. 文本分块规则

- 优先按空行/段落边界切分
- 若段落超过 `chunk_size`，再按字符数切分
- `chunk_size` 与 `chunk_overlap` 都按字符计，不按 token 计
- 默认值：`chunk_size=500`，`chunk_overlap=50`
- PDF 提取后先做文本清洗：合并多余空白、去掉明显空行、保留正文顺序

## 6. 检索与编码流程

### 文本编码

query 和 chunk 使用同构编码流程：
1. 文本归一化：转小写、合并多余空白、移除明显标点噪音
2. token 化：按非字母数字边界切分，丢弃长度为 1 的 token
3. 对每个 token 执行 `encode_atom(token, dim=1024)`
4. 对所有 token 向量执行 `bundle`
5. 对结果做归一化，得到文本向量

### 检索流程

每次 Agent 发起 API 调用前，provider 的 `prefetch(query)` 执行：
1. 对 query 生成 HRR 向量
2. 从 `doc_chunks_fts` 用 FTS5/BM25 召回 top 50 个候选 chunk
3. 对候选 chunk 计算 query-vector 与 chunk-vector 的 cosine similarity
4. 使用混合分数重排：

```text
score = 0.6 * fts_score + 0.4 * hrr_score
```

5. 返回 top K（默认 5）个 chunk，拼接成 `<memory-context>` 块
6. 无匹配时返回空字符串，不影响正常对话

HRR 在本设计中只用于重排，不单独承担初次召回。

## 7. 摄入流程

### 固定目录扫描（启动时）

provider 在 `initialize()` 时扫描 `~/.hermes/docs/` 下所有支持的文档。

对每个目录文档：
1. 计算稳定 `doc_id`
2. 计算当前 `content_hash`
3. 按 `source_path` 查已有文档
4. 若文件已不存在：删除旧 `doc_meta` 和对应 `doc_chunks`
5. 若 `content_hash` 未变化：跳过
6. 若 `content_hash` 变化：整篇删除后重建索引

单文件失败只记录日志，不中断整个扫描流程。  
空文档或提取后无文本时跳过并记录原因。

### 对话内上传：`attach_document(path=...)`

`documents` provider 暴露工具：

```text
attach_document(path: string)
```

处理逻辑：
1. 检查路径是否存在
2. 检查扩展名是否受支持
3. 解析文本 → 分块 → 生成 HRR 向量 → 入库
4. `source_type='upload'`
5. 上传文档每次视为新文档，不做覆盖更新
6. 返回确认信息：文件名、chunk 数、是否索引成功

## 8. 支持格式

- `.txt` / `.md`：直接读取文本
- `.pdf`：使用 `pymupdf`（fitz）提取文字

若 PDF 解析失败，则返回明确错误；本期不设计 `pdftotext` fallback。

## 9. 错误处理

- 单个目录文件解析失败：记录日志，继续处理其他文件
- `attach_document` 传入不存在路径：返回显式错误
- 不支持的扩展名：返回显式错误
- 文档解析后无可用文本：返回显式错误或跳过（目录扫描场景）
- SQLite 单次写入失败：当前文档索引失败，不影响已有索引

## 10. 依赖

新增依赖：
- `pymupdf`：PDF 文字提取
- `numpy`：HRR 向量运算（若项目已存在则无需新增）

## 11. 配置

```yaml
documents:
  provider: documents
  knowledge_dir: ~/.hermes/docs
  retrieval_top_k: 5
  retrieval_candidate_count: 50
  chunk_size: 500
  chunk_overlap: 50
  supported_extensions:
    - .pdf
    - .md
    - .txt
```

## 12. 关键设计决策

| 决策 | 理由 |
|------|------|
| 独立 `documents` provider | 文档知识库与对话记忆分离，便于独立演进 |
| provider 自己暴露 `attach_document` | 明确对话内上传入口，避免职责不清 |
| `doc_id` 与 `content_hash` 分离 | 同时支持稳定标识与可靠更新判断 |
| external-content FTS5 + triggers | 与现有 holographic store 设计风格一致，避免手工维护 rowid |
| FTS5 初筛 + HRR 重排 | 在不引入外部 embedding 模型的前提下提升相关性 |
| token 级 `encode_atom` 后 bundle | 比整段文本直接 encode 更接近可解释的文本 HRR 表示 |
| 目录文档可更新，上传文档不覆盖 | 简化上传语义，降低状态复杂度 |

## 13. 本期不做

- 网页 URL 抓取入库
- 多模态文档（图片、表格结构）
- 按来源、标签、文档集合过滤召回结果
- 上传文档的覆盖更新或删除工具
- 复杂 NLP 分词、实体抽取、摘要生成
