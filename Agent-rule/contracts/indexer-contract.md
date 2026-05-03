# Indexer Contract

## Purpose
- 规范目录扫描、资源识别与索引增量输出的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "scan_roots": ["string"],
  "comic_roots": ["string"],
  "scan_mode": "full|incremental",
  "resource_types": ["pdf|epub|txt|comic_folder"],
  "comic_max_depth": 5,
  "last_checkpoint": "ISO-8601|null",
  "constraints": ["string"],
  "trace_id": "string"
}
```

## Output Schema
```json
{
  "status": "success|partial|failed",
  "output": {
    "resource_index_delta": [
      {
        "resource_id": "string",
        "resource_type": "string",
        "path": "string",
        "comic_root": "string|null",
        "cover_image_path": "string|null",
        "image_count": 0,
        "info_text": "string|null",
        "change_type": "created|updated|deleted"
      }
    ],
    "next_checkpoint": "ISO-8601",
    "scan_metrics": {
      "scanned_paths": 0,
      "detected_resources": 0,
      "detected_comic_folders": 0,
      "duration_ms": 0
    }
  },
  "errors": [],
  "trace_id": "string"
}
```

## Guarantees
- 保证输出 `next_checkpoint`。
- 保证 `resource_index_delta` 仅包含本次变化。
- 保证 `resource_id` 在单次输出内唯一。
- 保证 `comic_folder` 单元的 `cover_image_path` 与 `image_count` 可追踪。

## Error Shape
```json
{
  "code": "INDEXER_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "resource_path": "string|null"
}
```
