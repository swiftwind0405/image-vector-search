# 超大图片跳过向量化 & ImagesPage 全量显示

**日期**: 2026-04-11
**状态**: 待实施

## 背景

某些嵌入模型（如 Jina）对大图片会报错，影响批量索引的稳定性。当前 `ImagesPage` 只显示成功向量化的图片（`list_active_images_with_labels`），超大或失败的图片对用户不可见。

## 目标

1. 默认跳过 >2MB 图片的向量化（阈值可配置，`0` 表示不限制）。
2. `ImagesPage` 显示**所有**图片（包括未向量化、超大、inactive），每张图片显示其嵌入状态。
3. 用户可在后台选中超大图片，异步强制向量化（通过现有 `BackgroundJobWorker`）。

## 架构决策

### 1. 新增 `embedding_status` 列
`images` 表新增 `embedding_status TEXT NOT NULL DEFAULT 'pending'`，取值：

| 值 | 含义 |
|---|---|
| `embedded` | 已成功向量化 |
| `skipped_oversized` | 因超过阈值被跳过 |
| `failed` | 强制嵌入时失败 |
| `pending` | 尚未处理（新旧数据兼容用） |

**与 `is_active` 正交**：`is_active` 仍表示"磁盘上存在"，`embedding_status` 表示嵌入层面的状态。两者独立，inactive 清理流程不会影响超大图片列表。

### 2. 配置
`Settings.max_embedding_file_size_mb: int = Field(default=2, ge=0)`，对应环境变量 `IMAGE_SEARCH_MAX_EMBEDDING_FILE_SIZE_MB`。`0` 表示禁用阈值。

### 3. 异步强制向量化
复用 `JobRunner` + `BackgroundJobWorker`，新增 job 类型 `embed_selected`，payload 含 `content_hashes: list[str]`。

### 4. 迁移策略
使用运行时 `ALTER TABLE ADD COLUMN`（幂等，通过 `PRAGMA table_info` 检测）。迁移后立即执行：

```sql
UPDATE images SET embedding_status='embedded' WHERE embedding_status='pending';
```

因为旧库里所有已入库的记录都是成功嵌入过的，这样避免被误判为待处理。

## 任务分解

### 任务 1 — Schema & Domain 迁移

**文件**:
- `src/image_vector_search/repositories/schema.sql` — `images` CREATE TABLE 加 `embedding_status TEXT NOT NULL DEFAULT 'pending'`
- `src/image_vector_search/repositories/sqlite.py`:
  - 新增 `_ensure_embedding_status_column()`：在 `initialize_schema` 末尾，通过 `PRAGMA table_info(images)` 检查列是否存在，不存在则 `ALTER TABLE images ADD COLUMN embedding_status TEXT NOT NULL DEFAULT 'pending'`，然后执行一次性 `UPDATE images SET embedding_status='embedded' WHERE embedding_status='pending'`（仅在新加列时执行）
  - 更新 `_row_to_image` 读取 `embedding_status`
  - 更新 `upsert_image` 的 INSERT 和 ON CONFLICT 子句，写入 `embedding_status`
- `src/image_vector_search/domain/models.py`: `ImageRecord` 加 `embedding_status: str = "embedded"` 字段

**验证**:
- 手动：删除 `.data/config/**/milvus.db` 和 SQLite，启动服务确认新库正常建表
- 对现有库：备份后启动，确认已有记录被更新为 `embedded`
- 运行 `pytest tests/unit/` 全部通过

---

### 任务 2 — Config 新增阈值

**文件**:
- `src/image_vector_search/config.py`: 新增 `max_embedding_file_size_mb: int = Field(default=2, ge=0)`

**验证**:
- 单测：确认默认值为 `2`；通过环境变量 `IMAGE_SEARCH_MAX_EMBEDDING_FILE_SIZE_MB=10` 覆盖生效；`0` 被接受

---

### 任务 3 — IndexService 跳过超大文件

**文件**:
- `src/image_vector_search/services/indexing.py`:
  - `_process_path` 在获取 `stat` 后，若 `settings.max_embedding_file_size_mb > 0` 且 `stat.st_size > threshold_bytes`：
    - 计算 `content_hash`、读取图片元数据
    - 写入 `images`（`embedding_status='skipped_oversized'`, `is_active=True`）和 `image_paths`
    - **不**调用 embedding client，**不**写入 vector_index
    - `report.skipped_oversized += 1` 并 `return`
  - 其他路径调用 `upsert_image` 时显式传 `embedding_status='embedded'`
  - 新增公开方法 `force_embed_images(content_hashes: list[str]) -> dict`：
    - 对每个 hash 查 `ImageRecord`，定位 `canonical_path`
    - 调用 `_embed_image(Path(canonical_path))`
    - 成功：写入 vector_index，更新 `embedding_status='embedded'`
    - 失败：更新 `embedding_status='failed'`，记录 `last_error_summary`
    - 返回 `{"succeeded": int, "failed": int, "errors": [{hash, message}]}`
- `src/image_vector_search/domain/models.py`: `IndexingReport` 加 `skipped_oversized: int = 0`

**验证**:
- 单测（mock 文件大小）：3MB 文件 → 记录入库为 `skipped_oversized`，vector_index 未被调用
- 单测：阈值设为 `0` → 不跳过，正常 embed
- 单测 `force_embed_images` 成功路径：mock embedding 返回向量，断言 status 变为 `embedded`、vector_index 被 upsert
- 单测 `force_embed_images` 失败路径：embedding 抛异常，断言 status 变为 `failed`
- `pytest tests/unit/test_indexing*.py` 全部通过

---

### 任务 4 — JobRunner 支持 `embed_selected`

**文件**:
- `src/image_vector_search/services/jobs.py`:
  - `JobRunner.enqueue(job_type, payload=None)` 接受可选 payload
  - 入队时把 payload 以 JSON 形式存进 `JobRecord.summary_json`（或新增字段，视现有实现而定 — 先查看文件再决定）
  - `BackgroundJobWorker` dispatch 逻辑：识别 `embed_selected` 类型，从 payload 取 `content_hashes`，调用 `index_service.force_embed_images(hashes)`，把结果写回 `summary_json`

**验证**:
- 单测：入队 `embed_selected` job，assert worker 调用 `index_service.force_embed_images` 且 job 最终状态为 `succeeded`
- 单测：`force_embed_images` 抛异常 → job 状态为 `failed`

---

### 任务 5 — Repository & StatusService 查询扩展

**文件**:
- `src/image_vector_search/repositories/sqlite.py`:
  - `list_all_images_with_labels(folder=None, images_root=None, embedding_status=None, tag_id=None, category_id=None, include_descendants=True)` — 与 `list_active_images_with_labels` 类似但**不**过滤 `is_active`，支持按 `embedding_status` 过滤
- `src/image_vector_search/services/status.py`:
  - `list_all_images_with_labels(...)` 包装
  - `list_oversized_images() -> list[ImageRecord]`：查 `embedding_status='skipped_oversized'`

**验证**:
- 单测：插入混合状态的图片（embedded + skipped_oversized + inactive），查询返回全部；按 `embedding_status` 过滤返回子集
- 单测：`list_oversized_images` 只返回超大记录

---

### 任务 6 — HTTP API

**文件**:
- `src/image_vector_search/api/admin_routes.py`:
  - 修改 `GET /api/images`：新增 query 参数 `include_inactive: bool = True`、`embedding_status: str | None = None`；`include_inactive=True` 时调用新的 `list_all_images_with_labels`，否则保持原行为以兼容其他前端页面（tag/category images）
  - 新增 `GET /api/images/oversized` → `list_oversized_images()`
  - 新增 `POST /api/images/oversized/embed`：body `{content_hashes: list[str]}`，调用 `job_runner.enqueue("embed_selected", payload={"content_hashes": ...})`，返回 `JobRecord`

**验证**:
- 集成测试（FastAPI TestClient）：
  - `GET /api/images?include_inactive=true` 返回所有图片
  - `GET /api/images?embedding_status=skipped_oversized` 只返回超大
  - `POST /api/images/oversized/embed` 返回 202 + job id
- `pytest tests/integration/` 通过

---

### 任务 7 — 前端类型 & API hooks

**文件**:
- `src/image_vector_search/frontend/src/api/types.ts`:
  - `ImageRecord` 加 `embedding_status: "embedded" | "skipped_oversized" | "failed" | "pending"`
- `src/image_vector_search/frontend/src/api/images.ts`:
  - `ImagesQueryOptions` 加 `includeInactive?: boolean`、`embeddingStatus?: string`
  - `useImages` 把上述参数拼进 URL
  - 新增 `useOversizedImages()`：GET `/api/images/oversized`
  - 新增 `useForceEmbedImages()` mutation：POST `/api/images/oversized/embed`，`onSuccess` invalidate `["images"]` 和 `["jobs"]`

**验证**:
- `cd src/image_vector_search/frontend && npm run build` 通过
- `npm run test`（若有 vitest）通过

---

### 任务 8 — ImagesPage 全量显示 + 强制向量化 UI

**文件**:
- `src/image_vector_search/frontend/src/components/ImageBrowser.tsx`（或新增 `ImagesPage` 专用 wrapper）:
  - `ImagesPage` 对应场景下调用 `useImages({ includeInactive: true })`；其他场景（tag/category）保持默认行为
  - 在列表行和 gallery 卡片上显示状态 badge：
    - `embedded` → 绿色"已向量化"
    - `skipped_oversized` → 橙色"超大 (xx.x MB)"
    - `failed` → 红色"嵌入失败"
    - `pending` → 灰色"待处理"
  - 顶部新增 embedding_status 下拉筛选器
  - 选中行支持批量操作"强制向量化"（调用 `useForceEmbedImages`），调用成功后 toast + invalidate 查询
  - 单张操作：在 `skipped_oversized` / `failed` 的行上显示小按钮"重新向量化"

**验证**:
- 手动 E2E：
  1. 准备一张 >2MB 图片放进 images root，跑增量索引
  2. 打开 ImagesPage，确认图片出现且 badge 为"超大"
  3. 勾选后点击"强制向量化"，确认弹 toast、jobs 页面出现新 job
  4. 刷新 ImagesPage，确认状态变为"已向量化"（若 embedding 服务不拒绝的话）

---

### 任务 9 — 后端 cursor 分页

**动机**: 当前 `GET /api/images` 一次性返回全部记录；图片规模在万级以上会导致响应慢、前端渲染卡顿。改成 cursor-based 分页，为 ImagesPage 无限滚动提供后端支持。

**文件**:
- `src/image_vector_search/repositories/sqlite.py`:
  - 在 `list_all_images_with_labels` 和 `list_active_images_with_labels`（或底层 `list_active_images` / 新增的 `list_all_images`）新增参数 `limit: int | None = None`、`cursor: str | None = None`
  - 游标定义：上一页最后一条记录的 `canonical_path`（已有索引和 ORDER BY）
  - SQL 追加 `AND canonical_path > ?` + `LIMIT ?`，保持 `ORDER BY canonical_path ASC` 不变
  - **所有现有筛选都必须兼容分页**：folder 前缀、`embedding_status`、`is_active`、tag_id、category_id
    - folder/status/is_active 已是 SQL 侧过滤，天然兼容
    - tag_id / category_id 目前是"先查全量再用 set 过滤"的方式（见 `list_active_images` 中的 `allowed_hashes`），这与 `LIMIT` 不兼容 —— 需要改成 SQL JOIN（`JOIN image_tags ON ...`）或子查询，把筛选下推到数据库层，才能正确分页
- `src/image_vector_search/services/status.py`:
  - `list_all_images_with_labels` / `list_active_images_with_labels` 透传 `limit`/`cursor`
- `src/image_vector_search/domain/models.py`:
  - 新增 `PaginatedImages` 响应模型：`{items: list[ImageRecordWithLabels], next_cursor: str | None}`
  - `next_cursor` 为 `None` 表示到末尾

**验证**:
- 单测：插入 10 条图片，`limit=4` 分 3 次拉取，断言无重复无遗漏、顺序正确、最后一页 `next_cursor is None`
- 单测：带 `folder` 筛选 + 分页
- 单测：带 `tag_id` 筛选 + 分页（验证 JOIN 下推正确）
- 单测：带 `category_id` + `include_descendants` 筛选 + 分页
- 单测：带 `embedding_status` 筛选 + 分页
- 现有 `list_active_images` 不带分页参数的用例仍然全量返回（向后兼容）

---

### 任务 10 — API 支持分页参数

**文件**:
- `src/image_vector_search/api/admin_routes.py`:
  - `GET /api/images` 新增 query 参数 `limit: int | None = None`（默认不限制保持兼容，前端会显式传 200）、`cursor: str | None = None`
  - 响应格式调整：若传了 `limit`，返回 `{items: [...], next_cursor: "..."}`；不传 `limit` 时返回裸数组（保持旧行为，避免破坏 tag/category 页面）
  - 或者：统一改为对象格式，同步修改所有前端调用点（简单但涉及面广）—— **选后者**，值得一次性清理

**验证**:
- 集成测试（FastAPI TestClient）：
  - `GET /api/images?limit=50` 返回 `{items, next_cursor}`
  - 用返回的 `next_cursor` 再请求，确认无重复
  - 带 `folder` + `limit` 组合
  - 带 `tag_id` + `limit` 组合
- 修改现有涉及 `/api/images` 的集成测试以适配新响应格式

---

### 任务 11 — 前端 `useInfiniteQuery` + 无限滚动

**文件**:
- `src/image_vector_search/frontend/src/api/types.ts`:
  - 新增 `PaginatedImages` 类型
- `src/image_vector_search/frontend/src/api/images.ts`:
  - 新增 `useImagesInfinite(options)`，基于 `useInfiniteQuery`：
    - `queryFn` 传 `pageParam` 作为 `cursor`
    - `getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined`
    - `initialPageParam: undefined`
    - URL 拼接 `limit=200`（默认 page size，可后续调）
  - 保留 `useImages` 供非分页场景（TagImagesPage 等）使用，但改为也走新响应格式并取 `items`
- `src/image_vector_search/frontend/src/components/ImageBrowser.tsx`（或新的 `InfiniteImageBrowser` 变体）:
  - `ImagesPage` 场景切换到 `useImagesInfinite`
  - 把 `data.pages.flatMap(p => p.items)` 作为列表源
  - 在列表/gallery 底部放一个哨兵元素，用 `IntersectionObserver`（或现成 hook 如 `react-intersection-observer`）检测进入视口 → 调用 `fetchNextPage()`
  - 显示 loading spinner 和"已加载全部"尾状态
  - `isFetchingNextPage` 期间禁用再次触发
  - 顶部的 folder/status 筛选变更时重置分页（react-query 默认行为，依赖 queryKey 即可）
- **注意**：现有前端"选中全部"批量操作在无限滚动下语义变化 —— 应改为"选中已加载的全部" + 提示用户；或者提供"按当前筛选全选"的 server-side 批量 API（任务外）。本任务只保留前者。

**验证**:
- 手动 E2E：
  1. 准备 300+ 张图片（可复制小图）
  2. 打开 ImagesPage，初始只加载 200 张
  3. 滚动到底部，确认自动加载下一页
  4. 切换 folder 筛选，确认重置并从头加载
  5. 切换 embedding_status 筛选，确认分页正常
- `npm run build` 类型检查通过

---

### 任务 12 — 文档

**文件**:
- `README.md` / `docs/usage.md`（择其一）：
  - 记录环境变量 `IMAGE_SEARCH_MAX_EMBEDDING_FILE_SIZE_MB`
  - 简要描述新的 UI 能力
- `docs/api.md`：记录新增/修改的 API 端点（含 `limit`/`cursor`/分页响应结构）

---

## 依赖关系

```
任务1 (schema/domain) ──┬─► 任务3 (indexing skip)  ──► 任务4 (job runner)
                         │                              │
任务2 (config) ──────────┘                              │
                                                        ▼
任务1 ───────────────────► 任务5 (repo/status query) ──► 任务6 (API basic)
                                                             │
                                                             ▼
任务5 ───────────────────► 任务9 (repo 分页) ──────────► 任务10 (API 分页)
                                                             │
                                                             ▼
                                                        任务7 (前端 API)
                                                             │
                                      ┌──────────────────────┤
                                      ▼                      ▼
                                任务8 (前端页面 +       任务11 (前端无限
                                状态 badge/强制嵌入)     滚动)
                                      │                      │
                                      └──────────┬───────────┘
                                                 ▼
                                            任务12 (文档)
```

## 风险 & 注意事项

1. **旧库迁移**：`ALTER TABLE ADD COLUMN` 的 DEFAULT 对已有行生效，配合一次性 `UPDATE ... WHERE embedding_status='pending'` 把它们标为 `embedded`，避免被当成"待处理"。
2. **force_embed 真的失败**：Jina 对超大图片本就会报错，这是用户知情的选择，只需把错误落库到 `embedding_status='failed'` 并在前端展示。
3. **ImagesPage 数据量**：万级规模下必须分页，详见任务 9–11。
4. **兼容性**：`GET /api/images` 默认保持 `include_inactive=True`，但 `TagImagesPage`/`CategoryImagesPage` 通过 tag_id/category_id 过滤，可能需要确认它们是否也要显示 inactive。保守起见：`useImages` 在 tag/category 场景下显式传 `includeInactive: false` 保持旧行为。
5. **分页 + tag/category 过滤**：现有 `list_active_images` 的 tag/category 过滤是先拉全量再在 Python 层用 set 取交集 —— 这套逻辑与 SQL `LIMIT` 不兼容。任务 9 必须把这些过滤改成 SQL JOIN 下推，否则分页会返回错误结果。这是该任务最主要的风险点。
6. **API 响应格式变更**：任务 10 选择"统一改为 `{items, next_cursor}` 对象格式"，会破坏现有调用 `/api/images` 的前端代码和测试，必须在同一个 PR 里同步修改所有调用点。

## 未决问题

- 需要确认 `services/jobs.py` 的现有 payload 机制 — 若当前 `enqueue` 不支持 payload，任务 4 需要先扩展签名并检查所有调用点。
