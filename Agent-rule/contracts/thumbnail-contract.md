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

## Output Schema
```json
{
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

## Guarantees
- 保证返回可访问的本地 `thumbnail_path`。
- 保证延迟任务进入 `deferred_queue`。
- 保证缓存命中与生成统计可追踪。
- 保证 `comic_folder` 的 `cover_image_path` 与缩略图绑定。
- 保证 Text Novel 同名封面按 `.webp` → `.png` → `.jpg` → `.jpeg` 选择并输出 360×540 以内 WebP；手动封面不被自动扫描覆盖。
- Text Novel 同名封面在 `ScanWorker` 后台扫描阶段同步生成，不进入首屏 `deferred_queue`；失败写 `text_cover_generation_failed` 警告并继续入库文本。
- Settings 缩略图任务支持 `scope=text_novel`：`cleanup` 仅删除 `preview_root` 内受控缓存并清空 `thumbnail_path/cover_source/cover_fingerprint`；`regenerate` 保留有效 `manual` 封面，否则按当前同名 sidecar 重建，缺失时回退标题占位。

## Error Shape
```json
{
  "code": "THUMBNAIL_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "resource_id": "string|null"
}
```
