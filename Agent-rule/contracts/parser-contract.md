# Parser Contract

## Purpose
- 规范资源命名解析与元数据结构化输出的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "records": [
    {
      "resource_id": "string",
      "resource_type": "string",
      "path": "string",
      "name": "string"
    }
  ],
  "ruleset": "string",
  "trace_id": "string"
}
```

## Output Schema
```json
{
  "status": "success|partial|failed",
  "output": {
    "parsed_records": [
      {
        "resource_id": "string",
        "title": "string",
        "series": "string|null",
        "volume": "number|null",
        "author": "string|null",
        "language": "string|null",
        "tags": ["string"],
        "confidence": 0.0
      }
    ],
    "unresolved_records": ["string"],
    "ruleset_version": "string"
  },
  "errors": [],
  "trace_id": "string"
}
```

## Guarantees
- 保证每条 `parsed_records` 都有 `confidence`。
- 保证 `ruleset_version` 可追溯。
- 保证未解析记录进入 `unresolved_records`。

## Error Shape
```json
{
  "code": "PARSER_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "resource_id": "string|null"
}
```
