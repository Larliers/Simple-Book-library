# Thumbnail Contract

## Purpose
- 规范封面候选、缩略图生成与缓存输出的数据契约。

## Input Schema
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

## Output Schema
```json
{
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

## Guarantees
- 保证返回可访问的本地 `thumbnail_path`。
- 保证延迟任务进入 `deferred_queue`。
- 保证缓存命中与生成统计可追踪。

## Error Shape
```json
{
  "code": "THUMBNAIL_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "resource_id": "string|null"
}
```
