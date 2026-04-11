# Image Vector Search 使用说明

本文档说明当前项目的实际使用方式，包括启动、配置、索引流程、工具调用方式，以及 Docker 使用注意事项。

## 1. 服务能力概览

当前服务提供以下能力：

- 本地图像目录扫描与索引
- 文本搜图：`search_images`
- 以图搜图：`search_similar`
- 后台管理界面
- 标签与分类管理
- 批量打标、批量分类、按目录批处理
- Embedding provider 在线切换与持久化配置

当前对外入口：

- 管理界面：`/`
- 健康检查：`/healthz`
- HTTP 工具发现：`GET /api/tools`
- HTTP 工具调用：`POST /api/tools/{tool_name}`

## 2. 启动前准备

### 2.1 环境要求

- Python 3.12+
- Node.js 20+（仅前端开发或重新构建前端时需要）
- 可访问的图片目录
- 可写的索引目录
- 至少一种 embedding provider 的可用 API key（Jina 或 Gemini）

### 2.2 初始化 `.env`

```bash
cp .env.example .env
mkdir -p ./data/images ./.data/config
```

常见做法：

- 本地调试：`IMAGE_SEARCH_IMAGES_ROOT=./data/images`
- 索引数据：`IMAGE_SEARCH_INDEX_ROOT=./.data/config`

你也可以把 `IMAGE_SEARCH_IMAGES_ROOT` 指向真实图片目录。

## 3. 配置规则

当前项目的 embedding 配置有两层来源：

1. 环境变量
2. 管理界面 `/settings` 中保存到 SQLite 的 provider / API key

实际生效规则：

- provider 和 API key 优先使用数据库中保存的值
- 如果数据库中没有对应值，则回退到环境变量
- 如果两边都没配置，服务仍可启动，但索引和搜索不会真正工作

这意味着：

- 可以先用 `.env` 启动
- 之后在后台页面修改 provider / key
- 修改后会持久化到 `metadata.db`

## 4. 运行方式

### 4.1 使用 `uv`

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
python -m image_vector_search
```

### 4.2 使用标准虚拟环境

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m image_vector_search
```

默认监听地址：

- `http://localhost:8000`

如果需要局域网访问，可在 `.env` 中设置：

```bash
IMAGE_SEARCH_HOST=0.0.0.0
```

## 5. 索引与搜索的典型流程

### 5.1 首次启动

1. 启动服务
2. 打开管理界面 `/`
3. 确认 embedding provider 与 key 已配置
4. 触发一次全量索引或增量索引

### 5.2 常用索引接口

- `POST /api/jobs/incremental`：增量索引
- `POST /api/jobs/rebuild`：全量重建
- `GET /api/jobs`：查看任务列表
- `GET /api/jobs/{job_id}`：查看任务详情
- `GET /api/status`：查看整体状态

`/api/status` 会返回：

- 磁盘图片数量
- 已索引图片数量
- 向量条目数量
- 当前 embedding provider / model / version
- 最近一次索引时间
- 最近一次错误摘要

## 6. HTTP 工具调用

### 6.1 发现可用工具

```bash
curl http://127.0.0.1:8000/api/tools
```

当前会返回至少两个工具：

- `search_images`
- `search_similar`

### 6.2 文本搜图

```bash
curl -X POST http://127.0.0.1:8000/api/tools/search_images \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "a red car parked on the street",
    "top_k": 5,
    "min_score": 0.0
  }'
```

可选参数：

- `query`
- `top_k`
- `min_score`
- `folder`

### 6.3 以图搜图

```bash
curl -X POST http://127.0.0.1:8000/api/tools/search_similar \
  -H 'Content-Type: application/json' \
  -d '{
    "image_path": "/absolute/path/to/image.jpg",
    "top_k": 5,
    "min_score": 0.0
  }'
```

说明：

- `image_path` 需要是服务端能访问到的真实路径
- 在 Docker 中通常应该使用容器内路径，例如 `/data/images/foo/bar.jpg`

## 7. 管理界面相关能力

### 7.1 认证

如果设置了以下环境变量，则后台管理需要登录：

- `IMAGE_SEARCH_ADMIN_USERNAME`
- `IMAGE_SEARCH_ADMIN_PASSWORD`

相关接口：

- `GET /api/auth/me`
- `POST /api/auth/login`
- `POST /api/auth/logout`

如果未配置用户名和密码，则后台默认为免登录模式。

### 7.2 图片与调试接口

- `GET /api/images`
- `GET /api/images/inactive`
- `POST /api/images/inactive/purge`
- `GET /api/images/{content_hash}/file`
- `GET /api/images/{content_hash}/thumbnail`
- `POST /api/debug/search/text`
- `POST /api/debug/search/similar`

### 7.3 标签与分类

标签接口：

- `POST /api/tags`
- `GET /api/tags`
- `PUT /api/tags/{tag_id}`
- `DELETE /api/tags/{tag_id}`
- `POST /api/tags/batch-delete`

分类接口：

- `POST /api/categories`
- `GET /api/categories`
- `GET /api/categories/{category_id}/children`
- `PUT /api/categories/{category_id}`
- `DELETE /api/categories/{category_id}`
- `POST /api/categories/batch-delete`

图片与标签/分类关联：

- `POST /api/images/{content_hash}/tags`
- `DELETE /api/images/{content_hash}/tags/{tag_id}`
- `GET /api/images/{content_hash}/tags`
- `POST /api/images/{content_hash}/categories`
- `DELETE /api/images/{content_hash}/categories/{category_id}`
- `GET /api/images/{content_hash}/categories`

### 7.4 批量操作

- `GET /api/folders`
- `POST /api/bulk/tags/add`
- `POST /api/bulk/tags/remove`
- `POST /api/bulk/categories/add`
- `POST /api/bulk/categories/remove`
- `POST /api/bulk/folder/tags/add`
- `POST /api/bulk/folder/tags/remove`
- `POST /api/bulk/folder/categories/add`
- `POST /api/bulk/folder/categories/remove`

本地文件联动：

- `POST /api/files/open`
- `POST /api/files/reveal`

这些接口会校验路径必须位于 `IMAGE_SEARCH_IMAGES_ROOT` 下。

## 8. Embedding Provider 说明

当前支持：

- `jina`
- `gemini`

相关环境变量：

- `IMAGE_SEARCH_EMBEDDING_PROVIDER`
- `IMAGE_SEARCH_EMBEDDING_MODEL`
- `IMAGE_SEARCH_EMBEDDING_VERSION`
- `IMAGE_SEARCH_JINA_API_KEY`
- `IMAGE_SEARCH_GOOGLE_API_KEY`
- `IMAGE_SEARCH_GEMINI_BASE_URL`
- `IMAGE_SEARCH_EMBEDDING_OUTPUT_DIMENSIONALITY`
- `IMAGE_SEARCH_EMBEDDING_BATCH_SIZE`
- `IMAGE_SEARCH_JINA_RPM`
- `IMAGE_SEARCH_JINA_MAX_CONCURRENCY`

切换 provider / model / version 时要注意：

- 它们共同定义同一个 embedding space
- 不同维度的向量不能混写进同一个 collection
- 最稳妥做法是清空旧索引目录，或切换新的 `IMAGE_SEARCH_VECTOR_INDEX_COLLECTION_NAME`

## 9. Docker 使用说明

### 9.1 构建镜像

```bash
docker build -t image-vector-search:test .
```

### 9.2 使用 Compose 启动

```bash
docker compose up --build
```

当前 Compose 默认约定：

- 图片目录挂载到 `/data/images`
- 索引目录挂载到 `/data/config`
- provider 默认为 `jina`
- 如果没有提供任一 provider 的 key，容器仍会启动，但需要后续在后台页面补充配置

### 9.3 当前 Docker 检查结论

本次检查中，项目层面的两个构建阶段都已单独验证：

- 前端 `npm run build` 成功
- Python 包安装流程没有发现仓库结构性错误，但受当前本地禁网环境影响，无法完整模拟 Docker 内部的依赖下载

发现并已修正的实际问题：

- Docker 构建上下文未充分忽略前端 `node_modules`、本地构建产物和虚拟环境缓存，导致上下文体积过大

如果你在本机执行 `docker build` 仍失败，请先确认 Docker daemon 已启动。

## 10. 持久化目录

`IMAGE_SEARCH_INDEX_ROOT` 下会保存：

- `metadata.db`：元数据、任务记录、已保存的 provider/key 配置
- `milvus.db`：向量索引

如果需要保留系统状态，请整体备份索引目录。
