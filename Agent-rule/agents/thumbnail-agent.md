# Thumbnail Agent

## Role
- 负责封面候选选择、缩略图生成、缓存策略与延迟生成流程。

## In Scope
- 从资源中挑选封面候选页或封面文件。
- 生成标准尺寸缩略图。
- 管理缩略图缓存键、过期与重建。
- 执行延迟生成与后台补全。
- 对 `comic_folder` 执行自然序首图封面选择（`jpg/png/webp/jpeg`）。
- 对 `text_novel` 将同目录同 stem 封面压缩为最长边不超过 360×540 的 WebP 缓存。

## Out of Scope
- 不负责目录扫描与索引建立。
- 不负责语义元数据解析。
- 不负责 UI 组件实现。

## Owned Modules
- `cover_candidate_selector`
- `thumbnail_generator`
- `thumbnail_cache_manager`

## Accepted Input Format
```json
{
  "request_id": "string",
  "task_id": "string",
  "resources": [
    {
      "resource_id": "string",
      "resource_type": "string",
      "path": "string",
      "cover_image_path": "string|null"
    }
  ],
  "thumbnail_profile": {
    "width": 0,
    "height": 0,
    "format": "jpg|png|webp"
  },
  "generation_mode": "eager|lazy",
  "trace_id": "string"
}
```

## Output Format
```json
{
  "request_id": "string",
  "task_id": "string",
  "status": "success|partial|failed",
  "output": {
    "thumbnails": [
      {
        "resource_id": "string",
        "thumbnail_path": "string",
        "cover_image_path": "string|null",
        "cache_key": "string",
        "generated_at": "ISO-8601"
      }
    ],
    "deferred_queue": ["string"],
    "metrics": {
      "generated": 0,
      "cached_hit": 0,
      "duration_ms": 0
    }
  },
  "errors": [],
  "trace_id": "string"
}
```

## Response Rules
- 首次展示场景优先返回可用缓存结果。
- Library/Comic 延迟任务必须写入 `deferred_queue`；Text Novel sidecar 在 `ScanWorker` 后台扫描阶段直接缓存，不占用首屏队列。
- 缩略图路径必须是可访问的本地路径。
- 失败项必须进入 `errors` 并给出 `retryable` 语义。
- `comic_folder` 必须返回用于双击外部打开的 `cover_image_path`。
- Text Novel 手动封面优先于扫描得到的 `sidecar` 封面；自动封面删除后清理受控缓存并回退标题占位。
