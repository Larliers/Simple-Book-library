# Parser Agent

## Role
- 负责文件名/目录名解析、元数据提取与规则配置化。

## In Scope
- 解析资源名称中的标题、卷号、作者、语言、版本等元信息。
- 根据可配置规则执行标准化与结构化。
- 输出可被索引与 UI 复用的统一元数据对象。

## Out of Scope
- 不负责文件系统扫描。
- 不负责缩略图处理。
- 不负责 UI 渲染。

## Owned Modules
- `filename_parser`
- `metadata_normalizer`
- `parse_ruleset_manager`

## Accepted Input Format
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

## Output Format
```json
{
  "request_id": "string",
  "task_id": "string",
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

## Response Rules
- 每条解析结果必须包含 `confidence`。
- 无法解析的记录必须进入 `unresolved_records`。
- 规则集版本必须回传到 `ruleset_version`。
- 禁止在输出中添加未登记字段。
