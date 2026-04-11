# Indexer Contract

## Purpose
- 规范目录扫描、资源识别与索引增量输出的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "scan_roots": ["string"],
  "scan_mode": "full|incremental",
  "resource_types": ["pdf|epub|txt|comic_folder"],
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
        "change_type": "created|updated|deleted"
      }
    ],
    "next_checkpoint": "ISO-8601",
    "scan_metrics": {
      "scanned_paths": 0,
      "detected_resources": 0,
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

## Error Shape
```json
{
  "code": "INDEXER_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "resource_path": "string|null"
}
```
