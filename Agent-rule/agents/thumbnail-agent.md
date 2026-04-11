# Thumbnail Agent

## Role
- 负责封面候选选择、缩略图生成、缓存策略与延迟生成流程。

## In Scope
- 从资源中挑选封面候选页或封面文件。
- 生成标准尺寸缩略图。
- 管理缩略图缓存键、过期与重建。
- 执行延迟生成与后台补全。

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
      "path": "string"
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
- 延迟任务必须写入 `deferred_queue`。
- 缩略图路径必须是可访问的本地路径。
- 失败项必须进入 `errors` 并给出 `retryable` 语义。
