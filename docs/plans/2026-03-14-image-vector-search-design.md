# Image Vector Search Design

## 1. Goal

在现有 [`docs/image-vector-search.md`](../image-vector-search.md) 的基础上，实现一个运行在 QNAP 单容器内的本地图片语义检索服务。

对外分成两类入口：

- Agent 入口：MCP，只暴露 `search_images` 和 `search_similar`
- 人工管理入口：Web 管理页 + HTTP API，负责状态查看、增量更新、全量重建、任务历史和检索调试

首版技术栈固定为 `Python + FastAPI + FastMCP + SQLite + Milvus Lite + pytest`。

## 2. Implementation Assumptions

以下实现假设已按官方文档核对：

- FastMCP 可以通过 `http_app()` 生成 ASGI 应用，再挂到 FastAPI 上；若 FastAPI 自己也有 lifespan，需要组合 lifespan。
- Milvus Lite 通过 `pymilvus` 直接连接本地文件路径即可使用，适合当前这种轻量单机场景。
- Milvus 在 `COSINE` 度量下返回的分值越大表示越相似，因此应用层可直接把它作为 `score` 暴露。

参考：

- [FastMCP FastAPI integration](https://gofastmcp.com/integrations/fastapi)
- [FastMCP installation / versioning](https://gofastmcp.com/getting-started/installation)
- [Milvus Lite local file usage](https://milvus.io/docs/milvus_lite.md/)
- [Milvus metric types](https://milvus.io/docs/metric.md)
- [Milvus vector search scoring](https://blog.milvus.io/docs/v2.5.x/single-vector-search.md)

## 3. High-Level Architecture

单进程服务同时承载三类能力：

1. FastMCP：给 agent 提供检索工具
2. FastAPI：提供管理 API 和管理页面
3. 内部服务层：统一封装索引、搜索、状态和后台任务

```text
┌──────────────────────────────┐
│ Agent via MCP                │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ image-search-mcp (single Python process)               │
│                                                         │
│  FastMCP tools      FastAPI web/admin      Job worker   │
│        │                    │                    │       │
│        └────────────┬───────┴────────────┬───────┘       │
│                     ▼                    ▼               │
│             SearchService          IndexService          │
│                     │                    │               │
│                     ├────────────┬───────┤               │
│                     ▼            ▼                       │
│            EmbeddingClient   MetadataRepository          │
│                     │            (SQLite)                │
│                     ▼                                    │
│                VectorIndex (Milvus Lite)                 │
└─────────────────────────────────────────────────────────┘
```

## 4. Project Layout

建议目录结构：

```text
src/image_search_mcp/
  __init__.py
  app.py
  config.py
  domain/
    models.py
  adapters/
    embedding/
      base.py
      jina.py
    vector_index/
      base.py
      milvus_lite.py
  repositories/
    schema.sql
    sqlite.py
  scanning/
    files.py
    image_metadata.py
    hashing.py
  services/
    search.py
    indexing.py
    status.py
    jobs.py
  mcp/
    server.py
  web/
    routes.py
    templates/
      index.html
    static/
      app.js
      styles.css
tests/
  unit/
  integration/
.github/workflows/
```

## 5. Key Boundaries

### 5.1 MCP boundary

MCP 只暴露两个工具：

- `search_images`
- `search_similar`

索引和运维动作不通过 MCP 暴露，避免 agent 误触发重扫/重建，也让人工管理页成为唯一维护入口。

### 5.2 Embedding abstraction

Embedding 必须独立抽象成一层，业务服务不得直接调用 Jina HTTP API。

建议接口：

- `embed_texts(texts: list[str]) -> list[list[float]]`
- `embed_images(paths: list[Path]) -> list[list[float]]`
- `vector_dimension() -> int`
- `provider_name() -> str`
- `model_name() -> str`
- `version_name() -> str`

首版只实现 `JinaEmbeddingClient`，但 `SearchService`、`IndexService` 仅依赖接口，确保后续替换 embedding 模型时变更面收敛在 adapter 层与配置层。

### 5.3 Vector index abstraction

Milvus Lite 也只通过窄接口访问：

- `ensure_collection(dimension, embedding_key)`
- `upsert_embeddings(records)`
- `search(vector, limit)`
- `has_embedding(content_hash, embedding_key)`
- `count(embedding_key)`

这样后续即使迁移到独立 Milvus，也不需要重写服务层。

## 6. Data Model

### 6.1 SQLite tables

#### `images`

按内容身份存一行：

- `content_hash` TEXT PRIMARY KEY
- `canonical_path` TEXT NOT NULL
- `file_size` INTEGER NOT NULL
- `mtime` REAL NOT NULL
- `mime_type` TEXT NOT NULL
- `width` INTEGER NOT NULL
- `height` INTEGER NOT NULL
- `is_active` INTEGER NOT NULL
- `last_seen_at` TEXT NOT NULL
- `embedding_provider` TEXT NOT NULL
- `embedding_model` TEXT NOT NULL
- `embedding_version` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

#### `image_paths`

按路径追踪文件状态。为了支撑便宜的增量比对，这里额外保存路径级 `file_size` 和 `mtime`：

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `content_hash` TEXT NOT NULL
- `path` TEXT NOT NULL UNIQUE
- `file_size` INTEGER NOT NULL
- `mtime` REAL NOT NULL
- `is_active` INTEGER NOT NULL
- `last_seen_at` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

#### `jobs`

用于 Web 管理页显示后台任务：

- `id` TEXT PRIMARY KEY
- `job_type` TEXT NOT NULL
- `status` TEXT NOT NULL
- `requested_at` TEXT NOT NULL
- `started_at` TEXT
- `finished_at` TEXT
- `summary_json` TEXT
- `error_text` TEXT

#### `system_state`

保存最近状态和当前活动 embedding 配置：

- `key` TEXT PRIMARY KEY
- `value` TEXT NOT NULL

关键 key：

- `last_incremental_update_at`
- `last_full_rebuild_at`
- `last_error_summary`
- `active_embedding_provider`
- `active_embedding_model`
- `active_embedding_version`

### 6.2 Milvus collection

Milvus Lite collection 只保留最小检索字段：

- `content_hash`
- `embedding`
- `embedding_provider`
- `embedding_model`
- `embedding_version`

collection 名称可固定为 `image_embeddings`，embedding 版本作为 metadata 字段参与逻辑隔离。

## 7. Search Design

### 7.1 Common rules

- 检索结果单位是图片内容，不是路径
- 只返回 `images.is_active = true`
- 只返回当前活动 embedding 空间的数据
- 当有 `folder` 过滤时，应用层先过采样向量结果，再回 SQLite 做路径过滤，避免直接拿 `top_k` 后过滤导致结果不足

建议过采样规则：

- `candidate_limit = min(max(top_k * 5, 20), 200)`

### 7.2 `search_images`

流程：

1. 校验 `top_k` 和 `min_score`
2. 用当前活动 `EmbeddingClient` 对文本生成向量
3. 从 `VectorIndex` 检索候选 `content_hash`
4. 批量回查 SQLite 元数据
5. 应用 `is_active`、`folder`、`min_score` 过滤
6. 截断到 `top_k` 返回

### 7.3 `search_similar`

流程：

1. 校验 `image_path` 必须落在 `images_root` 下且文件存在
2. 计算查询文件 `content_hash`
3. 对该图片生成查询向量
4. 检索候选 `content_hash`
5. 排除与查询图相同的 `content_hash`
6. 回查 SQLite、应用过滤并返回

该流程不要求查询图必须已入库。

## 8. Indexing Design

### 8.1 Incremental update

目标：优先复用已有 embedding，尽量不重复付费。

流程：

1. 扫描 `/data/images` 下受支持的图片文件
2. 对每个路径先读当前 `file_size` 和 `mtime`
3. 若路径未出现过，或路径级 `file_size/mtime` 发生变化，则重算 `content_hash`
4. 若 `content_hash` 已存在：
   - 更新 `image_paths`
   - 更新 `images.last_seen_at`
   - 若主路径失效或当前路径更合适，刷新 `canonical_path`
   - 不重新生成 embedding
5. 若 `content_hash` 不存在：
   - 读取元数据
   - 调用 embedding client
   - 写入 Milvus Lite
   - 写入 `images` 和 `image_paths`
6. 对本轮未再次出现的路径标记 `is_active = false`
7. 对失去所有活跃路径的图片将 `images.is_active = false`
8. 更新 `system_state`

### 8.2 Full rebuild

默认行为不是 destructive reset，而是：

1. 全目录扫描
2. 重建 SQLite 中的活动视图
3. 尽量复用已有 `content_hash`
4. 仅对缺失向量的图片重新嵌入
5. 清理无效路径和状态
6. 更新 `last_full_rebuild_at`

### 8.3 Canonical path policy

- 优先保留仍然有效的旧 `canonical_path`
- 若旧主路径失效，从活跃路径中按字典序选第一个
- 若无活跃路径，则将图片标记为非活跃

## 9. Job Execution Model

索引任务不走同步 HTTP 调用，而是走单进程内的串行后台 worker：

- 前端点击按钮后写入 `jobs`
- worker 从内存队列取任务
- 执行时更新 `jobs.status`
- 前端轮询任务状态
- 同一时间只允许一个索引任务运行

这样可以避免：

- 浏览器请求超时
- 增量更新和全量重建并发写 SQLite / Milvus
- 为单机场景引入额外队列中间件

## 10. Web Admin Scope

管理页做成单页控制台，包含四个区块：

1. 状态概览
   - 总图片数
   - 活跃图片数
   - 非活跃图片数
   - 向量条目数
   - 当前 embedding provider/model/version
   - 最近增量更新时间
   - 最近全量重建时间

2. 操作区
   - 触发增量更新
   - 触发全量重建
   - 全量重建需要二次确认

3. 任务历史
   - 最近任务列表
   - 最近一次任务统计摘要
   - 错误摘要

4. 检索调试
   - 文本搜图表单
   - 以图搜图表单（输入容器内路径）

前端选型固定为 `Jinja2 + HTMX + 少量原生 JS`，避免首版引入单独前端构建链。

## 11. Error Handling

- Jina 请求失败：最多 3 次指数退避重试，单张图片失败只计入错误数，不中断整批任务
- 失效路径：检索时不返回；增量/重建时更新 `is_active`
- 非法路径：`search_similar` 和调试接口直接 400
- Milvus/SQLite 初始化失败：应用启动失败，避免带病运行
- 后台任务失败：`jobs.status = failed`，写 `error_text`，同时更新 `system_state.last_error_summary`

## 12. Testing Strategy

测试分三层：

1. 单元测试
   - 设置解析
   - 路径校验
   - canonical path 选择
   - 任务状态流转
   - 文件过滤逻辑

2. 服务测试
   - `SearchService`
   - `IndexService`
   - `StatusService`
   - fake embedding client / fake vector index

3. 集成测试
   - 临时图片目录
   - 临时 SQLite 文件
   - 临时 Milvus Lite 文件
   - 覆盖新增、重命名复用、重复文件、删除失效、搜索过滤、后台任务执行

## 13. Deployment Deliverables

首版交付物包括：

- Python 应用代码
- `pytest` 测试
- `Dockerfile`
- `docker-compose.yml` 示例
- `.github/workflows/publish.yml`，构建并发布镜像到 GHCR

容器运行约束：

- `/data/images` 只读挂载
- `/data/index` 读写挂载
- 敏感信息通过环境变量注入，至少包括 `JINA_API_KEY`

## 14. Out of Scope

首版不做：

- 自动定时扫描
- 文件系统事件监听
- 多 worker 并发索引
- 面向公网的鉴权体系
- 图像预览或复杂图库 UI
