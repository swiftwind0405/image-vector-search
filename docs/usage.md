# Image Search MCP 使用文档

这是一个本地图像语义搜索服务，提供两种操作界面：
- **MCP 工具（供智能体使用）**：`search_images`，`search_similar`
- **Admin Web 控制台**：用于查看服务状态、触发索引任务以及调试搜索

服务将图像元数据存储在 SQLite 中，将向量嵌入（Embeddings）存储在本地 Milvus Lite 数据库中。图像路径始终使用容器内的路径：其中 `/data/images` 挂载为只读，`/data/index` 挂载为读写。

## 环境要求

- Python 3.12+ (推荐使用 [uv](https://docs.astral.sh/uv/) 进行依赖管理)
- 用于获取 Jina embeddings 的 `JINA_API_KEY`
- 挂载在 `/data/images` 的图像库目录
- 挂载在 `/data/index` 的可写索引目录

## 环境变量配置

**必填项：**
- `IMAGE_SEARCH_JINA_API_KEY`

**可选项：**
- `IMAGE_SEARCH_IMAGES_ROOT` （默认：`/data/images`）
- `IMAGE_SEARCH_INDEX_ROOT` （默认：`/data/index`）
- `IMAGE_SEARCH_HOST`
- `IMAGE_SEARCH_PORT`
- `IMAGE_SEARCH_DEFAULT_TOP_K`
- `IMAGE_SEARCH_MAX_TOP_K`
- `IMAGE_SEARCH_MIN_SCORE`
- `IMAGE_SEARCH_EMBEDDING_PROVIDER`
- `IMAGE_SEARCH_EMBEDDING_MODEL`
- `IMAGE_SEARCH_EMBEDDING_VERSION`
- `IMAGE_SEARCH_VECTOR_INDEX_COLLECTION_NAME`
- `IMAGE_SEARCH_VECTOR_INDEX_DB_FILENAME`

## 本地运行指南

首先，创建 `.env` 文件和所需的目录：

```bash
cp .env.example .env
# 在 .env 文件中填入你的实际配置值
mkdir -p ./data/images ./data/index
```

### 使用 uv 运行（推荐）

```bash
uv run --env-file .env uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

或者手动导出环境变量运行：

```bash
export IMAGE_SEARCH_IMAGES_ROOT=./data/images
export IMAGE_SEARCH_INDEX_ROOT=./data/index
export IMAGE_SEARCH_JINA_API_KEY=your_api_key_here
uv run uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 传统方式运行

```bash
source .venv/bin/activate
export IMAGE_SEARCH_IMAGES_ROOT=./data/images
export IMAGE_SEARCH_INDEX_ROOT=./data/index
export IMAGE_SEARCH_JINA_API_KEY=your_api_key_here
uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

## Docker 运行指南

构建镜像：

```bash
docker build -t image-search-mcp:test .
```

使用 Docker Compose 启动：

```bash
export IMAGE_SEARCH_JINA_API_KEY=your-key
docker compose up --build
```

Compose 示例暴露了以下端口：
- Admin Web 控制台：`http://localhost:8000/`
- MCP 传输挂载点：`http://localhost:8000/mcp`

## API 与功能接口

### Admin HTTP 路由

- `GET /`：Web 控制台首页
- `GET /api/status`：获取服务状态
- `POST /api/jobs/incremental`：触发增量构建索引任务
- `POST /api/jobs/rebuild`：触发全量重建索引任务
- `GET /api/jobs`：获取任务列表
- `GET /api/jobs/{job_id}`：获取指定任务详情
- `POST /api/debug/search/text`：调试文本搜索功能
- `POST /api/debug/search/similar`：调试相似图像搜索功能

### MCP 工具 (Tools)

- `search_images`：根据文本搜索图像
- `search_similar`：搜索相似的图像

## 数据持久化

服务将在以下路径保存数据：
- SQLite 元数据：`/data/index/metadata.db`
- Milvus Lite 向量数据：`/data/index/milvus.db`

建议定期备份 `/data/index` 目录，以保存历史任务记录、元数据以及向量索引。
