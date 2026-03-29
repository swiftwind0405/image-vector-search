# 本地图像向量检索 Skills 说明文档

当前 `skills` 目录下包含的所有技能（Skills）旨在通过 HTTP API 对本地已建立索引的图像库进行检索和操作。

## 目录
- [Image Search 技能](#image-search-技能)
  - [前提条件](#前提条件)
  - [API 接口说明](#api-接口说明)
    - [1. 文本搜索 (Text Search)](#1-文本搜索-text-search)
    - [2. 相似图像搜索 (Similar Search)](#2-相似图像搜索-similar-search)
  - [响应格式](#响应格式)
  - [关联接口](#关联接口)
  - [使用技巧与建议](#使用技巧与建议)

---

## Image Search 技能

**技能名称:** `image-search`
**技能描述:** 通过 HTTP API 结合自然语言文本描述或者提供参考图像路径，对本地图库进行文本搜图或以图搜图。

该技能支持两种核心检索模式：
1. **文本搜索 (Text Search)** — 用自然语言描述你想要查找的图像内容。
2. **相似图像搜索 (Similar Search)** — 提供一张参考图像在磁盘上的路径，查找视觉上相似的图像。

### 前提条件

在此技能生效之前，`image-search-mcp` 服务必须处于运行状态，并且图像文件必须已经被系统成功建立了索引。

```bash
# 进入项目目录
cd /Users/stanley/Workspace/main/image-vector-search
# 启动 MCP 服务实例
python -m image_search_mcp
```

默认的服务基础 URL (Server base URL) 为：`http://localhost:8000`

### API 接口说明

#### 1. 文本搜索 (Text Search) — `POST /api/debug/search/text`

通过自然语言描述来搜索图像。

**请求体 (JSON 格式):**

| 字段名 | 类型 | 是否必填 | 默认值 | 描述 |
|-------------|------------------|----------|---------|--------------------------------------------------|
| `query` | `string` | 是 | — | 想要检索的图像的自然语言描述 |
| `top_k` | `int` | 否 | `5` | 返回结果的最大数量 (最小值: 1) |
| `min_score` | `float` | 否 | `0.0` | 相似度分数的最低阈值，分数低于此值的将不被包含在内 |
| `folder` | `string \| null` | 否 | `null` | 仅限定搜索范围在此文件目录路径之内 |

**请求示例:**

```bash
curl -X POST http://localhost:8000/api/debug/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset over the ocean", "top_k": 5}'
```

---

#### 2. 相似图像搜索 (Similar Search) — `POST /api/debug/search/similar`

查找与特定参考图像视觉上相近的图像。**请注意：** 作为参考对比的图像**必须已经生成过索引**，否则将会报错。

**请求体 (JSON 格式):**

| 字段名 | 类型 | 是否必填 | 默认值 | 描述 |
|--------------|------------------|----------|---------|---------------------------------------------------|
| `image_path` | `string` | 是 | — | 参考图像在本地电脑上的绝对文件路径 |
| `top_k` | `int` | 否 | `5` | 返回相似图像的最大数量 (最小值: 1) |
| `min_score` | `float` | 否 | `0.0` | 相似度分数的最低阈值 |
| `folder` | `string \| null` | 否 | `null` | 仅限定搜索范围在此文件目录路径之内 |

**请求示例:**

```bash
curl -X POST http://localhost:8000/api/debug/search/similar \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/data/images/photos/beach.jpg", "top_k": 10, "min_score": 0.5}'
```

**可能返回的错误状态码 (Error Responses):**
- `404` — `image_path` 提供的图像文件在磁盘上未找到。
- `400` — 该参考图像尚未被建立索引。

---

### 响应格式

不论是文本搜索还是相似图像搜索，检索成功后的返回体都将使用相同结构的 JSON 数据：

```json
{
  "results": [
    {
      "content_hash": "sha256...",
      "path": "/data/images/photos/sunset.jpg",
      "score": 0.82,
      "width": 1920,
      "height": 1080,
      "mime_type": "image/jpeg",
      "tags": [{"id": 1, "name": "landscape"}],
      "categories": [{"id": 2, "name": "nature"}]
    }
  ]
}
```

**返回值字段说明:**

| 字段名 | 类型 | 描述 |
|----------------|----------|--------------------------------------------|
| `content_hash` | `string` | 唯一标识此图像文件内容的 SHA-256 哈希值 |
| `path` | `string` | 匹配到的图像在本地存储的文件绝对路径 |
| `score` | `float` | 相似度得分（分数越高代表关联度或视觉相似度越高） |
| `width` | `int` | 图像的原始宽度（像素） |
| `height` | `int` | 图像的原始高度（像素） |
| `mime_type` | `string` | MIME 类型（例如：`image/jpeg`） |
| `tags` | `array` | 系统为该图像关联的标签列表（若有） |
| `categories` | `array` | 系统为该图像关联的分类类别列表（若有） |

### 关联接口

其他一些可能会在管理或浏览检索结果时需要用到的常用接口：

| HTTP 方法 | 请求路径 (Path) | 描述 |
|--------|---------------------------------------|--------------------------|
| `GET` | `/api/images/{content_hash}/file` | 根据给定的哈希值下载获取完整的原始图像文件 |
| `GET` | `/api/images/{content_hash}/thumbnail?size=120` | 获取该文件的 JPEG 格式缩略图（可通过 query params 指定缩略图尺寸）|
| `GET` | `/api/status` | 获取系统的当前运行状态、数据库和向量表索引统计等信息 |

### 使用技巧与建议

1. **更精准的文本检索:** 在进行文本搜索时，使用描述性强、完整的短语（如 "a cat sitting on a red sofa 坐在红色沙发上的猫"）往往比只使用单个关键词（如 "cat 猫"）能获得更好、更符合预期的匹配结果。
2. **过滤低质量匹配项:** 可以将 `min_score` 阈值设定在 `0.2` 到 `0.3` 这一区间内，有助于过滤掉相似判断置信度较低的干扰匹配项。
3. **搜图结果自动排他:** 在执行以图搜图（相似性检索）时，系统会自动在返回的结果数组中排除掉您用作参考对比的那个图像本身。
4. **重建或增量索引触发:** 只有已被索引的图像才会出现在搜索结果中。如果本地源文件夹里新增了图像，可以通过请求 `POST /api/jobs/incremental` 接口来触发后台异步的增量建立索引任务。
