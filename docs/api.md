# Image Vector Search 接口文档

本文档面向外部调用方，说明当前服务实际暴露的 HTTP 接口、鉴权行为、请求参数与典型响应。

## 1. 基础信息

- 默认基地址：`http://<host>:8000`
- 数据格式：除图片文件流外，其他接口均使用 `application/json`
- 健康检查：`GET /healthz`
- 工具发现：`GET /api/tools`
- 工具调用：`POST /api/tools/{tool_name}`

面向外部系统和智能体的可编程入口是 `/api/tools/*`。

## 2. 鉴权说明

### 2.1 当前实现行为

如果配置了以下环境变量，前端管理界面会先走登录流程：

- `IMAGE_SEARCH_ADMIN_USERNAME`
- `IMAGE_SEARCH_ADMIN_PASSWORD`

对应接口：

- `GET /api/auth/me`
- `POST /api/auth/login`
- `POST /api/auth/logout`

但按照当前后端实现，其余 `/api/*` 路由并没有统一的服务端鉴权拦截。也就是说：

- 登录接口存在
- Session 会被写入 Cookie
- 但多数业务接口当前仍可直接访问

如果要对外网暴露，建议在反向代理或网关层额外加鉴权。

### 2.2 认证接口

#### `GET /api/auth/me`

返回当前会话是否已认证。

响应示例：

```json
{
  "authenticated": true
}
```

#### `POST /api/auth/login`

请求体：

```json
{
  "username": "admin",
  "password": "secret"
}
```

成功响应：

```json
{
  "ok": true
}
```

失败响应：

```json
{
  "detail": "Invalid credentials"
}
```

#### `POST /api/auth/logout`

响应：

```json
{
  "ok": true
}
```

## 3. 推荐给外部系统的接口

对于外部系统、脚本或 Agent，优先使用以下接口：

- `GET /healthz`
- `GET /api/tools`
- `POST /api/tools/{tool_name}`

相比后台管理接口，这组接口更稳定，也更接近产品能力本身。

### 3.1 `GET /healthz`

健康检查。

响应：

```json
{
  "status": "ok"
}
```

### 3.2 `GET /api/tools`

发现当前服务支持的工具及其输入参数模式。

响应示例：

```json
[
  {
    "name": "search_images",
    "description": "Search images by text description using semantic similarity",
    "parameters": {
      "type": "object",
      "properties": {
        "query": { "type": "string" },
        "top_k": { "type": "integer", "default": 5 },
        "min_score": { "type": "number", "default": 0.0 },
        "folder": { "type": "string", "default": null }
      },
      "required": ["query"]
    }
  }
]
```

当前默认可发现的工具有：

- `search_images`
- `search_similar`
- `manage_tags`
- `tag_images`
- `list_images`
- `get_image_info`
- `get_index_status`
- `trigger_index`

### 3.3 `POST /api/tools/{tool_name}`

按工具名执行能力，路径参数 `tool_name` 必须来自 `GET /api/tools` 返回列表。

通用错误语义：

- `400`：参数错误或业务校验失败
- `404`：工具不存在，或工具内部引用的文件/图片不存在
- `500`：工具执行异常

#### 3.3.1 `search_images`

按文本语义搜图。

请求体：

```json
{
  "query": "red flower in a garden",
  "top_k": 5,
  "min_score": 0.0,
  "folder": "nature"
}
```

响应示例：

```json
{
  "results": [
    {
      "content_hash": "abc123",
      "path": "/data/images/nature/rose.jpg",
      "score": 0.91,
      "width": 1024,
      "height": 768,
      "mime_type": "image/jpeg",
      "tags": []
    }
  ]
}
```

参数说明：

- `query`：必填，文本描述
- `top_k`：可选，默认 `5`
- `min_score`：可选，默认 `0.0`
- `folder`：可选，按图片根目录下的相对目录过滤

#### 3.3.2 `search_similar`

按图片路径做相似图搜索。

请求体：

```json
{
  "image_path": "/data/images/nature/rose.jpg",
  "top_k": 5,
  "min_score": 0.0,
  "folder": "nature"
}
```

说明：

- `image_path` 是服务端本机可访问路径，不是文件上传
- 容器部署时应传容器内路径，例如 `/data/images/...`

#### 3.3.3 `list_images`

列出已索引图片。

请求体：

```json
{
  "folder": "nature",
  "tag_id": 1
}
```

响应：

```json
{
  "images": [
    {
      "content_hash": "abc123",
      "canonical_path": "/data/images/nature/rose.jpg",
      "file_size": 204800,
      "mtime": 1710000000.0,
      "mime_type": "image/jpeg",
      "width": 1024,
      "height": 768,
      "is_active": true,
      "last_seen_at": "2026-04-08T10:00:00+00:00",
      "embedding_provider": "jina",
      "embedding_model": "jina-clip-v2",
      "embedding_version": "v2",
      "created_at": "2026-04-08T10:00:00+00:00",
      "updated_at": "2026-04-08T10:00:00+00:00",
      "tags": []
    }
  ]
}
```

#### 3.3.4 `get_image_info`

读取单张图片详情。

请求体：

```json
{
  "content_hash": "abc123"
}
```

返回图片基础元数据，并尽量附带 `tags`。

#### 3.3.5 `get_index_status`

读取索引状态与最近任务。

请求体：

```json
{}
```

响应示例：

```json
{
  "status": {
    "images_on_disk": 120,
    "total_images": 120,
    "active_images": 118,
    "inactive_images": 2,
    "vector_entries": 118,
    "embedding_provider": "jina",
    "embedding_model": "jina-clip-v2",
    "embedding_version": "v2",
    "last_incremental_update_at": "2026-04-08T09:50:00+00:00",
    "last_full_rebuild_at": null,
    "last_error_summary": null
  },
  "recent_jobs": [
    {
      "id": "job-1",
      "job_type": "incremental",
      "status": "queued",
      "requested_at": "2026-04-08T09:50:00+00:00",
      "started_at": null,
      "finished_at": null,
      "summary_json": null,
      "error_text": null
    }
  ]
}
```

#### 3.3.6 `trigger_index`

触发索引任务。

请求体：

```json
{
  "mode": "incremental"
}
```

`mode` 只支持：

- `incremental`
- `full_rebuild`

#### 3.3.7 `manage_tags`

统一的标签管理工具。

`action` 支持：

- `create`
- `rename`
- `delete`
- `list`

示例，请求创建标签：

```json
{
  "action": "create",
  "name": "featured"
}
```

#### 3.3.8 `tag_images`

对单张图片增删标签。

`action` 支持：

- `add_tag`
- `remove_tag`
- `list_tags`

## 4. 后台管理 HTTP API

这组接口主要服务于管理后台，但当前同样对外暴露。若外部系统需要更细粒度控制，也可以直接调用。

## 4.1 状态与任务

### `GET /api/status`

返回索引状态。

核心字段：

- `images_on_disk`
- `total_images`
- `active_images`
- `inactive_images`
- `vector_entries`
- `embedding_provider`
- `embedding_model`
- `embedding_version`
- `last_incremental_update_at`
- `last_full_rebuild_at`
- `last_error_summary`

### `POST /api/jobs/incremental`

发起增量索引任务，返回 `202 Accepted`。

### `POST /api/jobs/rebuild`

发起全量重建任务，返回 `202 Accepted`。

### `GET /api/jobs`

返回最近 20 条任务记录。

### `GET /api/jobs/{job_id}`

返回单个任务详情。

未找到时：

```json
{
  "detail": "Job not found"
}
```

## 4.2 图片查询与调试

### `GET /api/images`

查询已索引且活跃的图片列表。

查询参数：

- `folder`：目录过滤
- `tag_id`：标签过滤

返回值是图片数组，每项结构等同 `ImageRecordWithLabels`。

### `GET /api/images/inactive`

返回已失活图片列表。

### `POST /api/images/inactive/purge`

永久清理失活图片及其向量。

请求体：

```json
{
  "content_hashes": ["hash1", "hash2"]
}
```

响应：

```json
{
  "ok": true,
  "affected": 2
}
```

注意：

- 仅允许传失活图片的 `content_hash`
- 如果传入活跃图片或不存在的 hash，会返回 `400`

### `POST /api/debug/search/text`

调试版文本搜图接口。

请求体：

```json
{
  "query": "red flower",
  "top_k": 5,
  "min_score": 0.0,
  "folder": "nature"
}
```

响应格式：

```json
{
  "results": []
}
```

当 embedding 服务不可连接时返回 `503`。

### `POST /api/debug/search/similar`

调试版相似图搜索。

请求体：

```json
{
  "image_path": "/data/images/nature/rose.jpg",
  "top_k": 5,
  "min_score": 0.0,
  "folder": "nature"
}
```

错误语义：

- `404`：图片路径不存在
- `400`：请求参数或路径不合法

### `GET /api/images/{content_hash}/file`

按内容哈希返回原图文件流。

- 成功时返回图片二进制内容
- `Cache-Control: max-age=86400`
- 找不到图片或文件时返回 `404`

### `GET /api/images/{content_hash}/thumbnail`

按内容哈希返回 JPEG 缩略图。

查询参数：

- `size`：范围 `50` 到 `500`，默认 `120`

错误语义：

- `422`：`size` 超出范围
- `404`：原图不存在或缩略生成失败

## 4.3 Embedding 配置

### `GET /api/settings/embedding`

返回当前 embedding 配置状态，但不会返回明文 API key。

响应示例：

```json
{
  "provider": "jina",
  "jina_api_key_configured": true,
  "google_api_key_configured": false,
  "using_environment_fallback": false
}
```

### `PUT /api/settings/embedding`

更新 embedding provider 与 API key，并尝试热重载 embedding client。

请求体：

```json
{
  "provider": "gemini",
  "jina_api_key": null,
  "google_api_key": "your-google-api-key"
}
```

字段约束：

- `provider` 仅支持 `jina` 或 `gemini`
- 切换到目标 provider 时，必须能拿到该 provider 的有效 key
- key 可来自本次请求、数据库已存值、或环境变量回退

错误语义：

- `422`：目标 provider 没有可用 key
- `500`：配置已保存，但 embedding client 热重载失败

## 4.4 标签

### 标签接口

#### `POST /api/tags`

请求体：

```json
{
  "name": "featured"
}
```

响应：

```json
{
  "id": 1,
  "name": "featured",
  "created_at": "2026-04-08T10:00:00+00:00",
  "image_count": 0
}
```

#### `GET /api/tags`

返回标签数组。

#### `PUT /api/tags/{tag_id}`

请求体：

```json
{
  "name": "new-name"
}
```

响应：

```json
{
  "ok": true
}
```

#### `DELETE /api/tags/{tag_id}`

成功返回 `204 No Content`。

#### `POST /api/tags/batch-delete`

请求体：

```json
{
  "tag_ids": [1, 2, 3]
}
```

响应：

```json
{
  "deleted": 3
}
```

批量删除上限为 `500`。

### 图片与标签关系

#### `POST /api/images/{content_hash}/tags`

请求体：

```json
{
  "tag_id": 1
}
```

成功返回：

```json
{
  "ok": true
}
```

#### `DELETE /api/images/{content_hash}/tags/{tag_id}`

成功返回 `204 No Content`。

#### `GET /api/images/{content_hash}/tags`

返回当前图片的标签列表。

## 4.5 批量操作与文件联动

### `GET /api/folders`

返回去重后的目录列表，例如：

```json
["nature", "urban"]
```

### 批量标签接口

以下接口返回结构一致：

```json
{
  "ok": true,
  "affected": 2
}
```

按图片选择批量处理：

- `POST /api/bulk/tags/add`
- `POST /api/bulk/tags/remove`

请求体分别为：

```json
{
  "content_hashes": ["aaa", "bbb"],
  "tag_id": 1
}
```

约束：

- `content_hashes` 最大数量为 `500`

按目录批量处理：

- `POST /api/bulk/folder/tags/add`
- `POST /api/bulk/folder/tags/remove`

请求体示例：

```json
{
  "folder": "nature",
  "tag_id": 1
}
```

### `POST /api/files/open`

请求操作系统打开图片文件。

请求体：

```json
{
  "path": "/data/images/nature/rose.jpg"
}
```

约束：

- 路径必须位于 `IMAGE_SEARCH_IMAGES_ROOT` 之下
- 文件必须存在

错误语义：

- `400`：路径越界
- `404`：文件不存在
- `500`：调用系统打开命令失败

### `POST /api/files/reveal`

请求在系统文件管理器中定位图片。

请求体与校验规则同 `POST /api/files/open`。

## 5. 常见数据结构

### 5.1 `Tag`

```json
{
  "id": 1,
  "name": "featured",
  "created_at": "2026-04-08T10:00:00+00:00",
  "image_count": 3
}
```

### 5.2 `SearchResult`

```json
{
  "content_hash": "abc123",
  "path": "/data/images/nature/rose.jpg",
  "score": 0.91,
  "width": 1024,
  "height": 768,
  "mime_type": "image/jpeg",
  "tags": []
}
```

### 5.3 `ImageRecordWithLabels`

```json
{
  "content_hash": "abc123",
  "canonical_path": "/data/images/nature/rose.jpg",
  "file_size": 204800,
  "mtime": 1710000000.0,
  "mime_type": "image/jpeg",
  "width": 1024,
  "height": 768,
  "is_active": true,
  "last_seen_at": "2026-04-08T10:00:00+00:00",
  "embedding_provider": "jina",
  "embedding_model": "jina-clip-v2",
  "embedding_version": "v2",
  "created_at": "2026-04-08T10:00:00+00:00",
  "updated_at": "2026-04-08T10:00:00+00:00",
  "tags": []
}
```

### 5.4 `JobRecord`

```json
{
  "id": "job-1",
  "job_type": "incremental",
  "status": "queued",
  "requested_at": "2026-04-08T09:50:00+00:00",
  "started_at": null,
  "finished_at": null,
  "summary_json": null,
  "error_text": null
}
```

## 6. 调用建议

- 外部 Agent 优先走 `/api/tools/*`
- 运维或后台集成可使用 `/api/status`、`/api/jobs/*`、`/api/settings/embedding`
- 若需稳定的公网访问，请在网关层补鉴权，因为当前后端未对大多数 `/api/*` 接口强制校验登录态
- `search_similar` 和 `/api/debug/search/similar` 依赖服务端本地文件路径，不支持直接上传图片二进制
