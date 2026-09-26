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

## Collection Rule Matcher Extension

- 新规则为 `{"version":2,"matchMode":"all|any","conditions":[{"field":"source_name|title|author|publisher|language|tags|series","operator":"contains|not_contains|starts_with|ends_with|equals","value":"string","caseSensitive":false}]}`；version 1 条件按 `source_name` 读取。
- Book 字段为来源原名、标题、作者、出版社、语言、标签；Text Novel 另有系列；Comic 为来源原名、标题、标签。跨 kind 字段在预览与保存时拒绝。
- 来源原名：普通文件去除完整扩展名，图片书/漫画文件夹取目录名，CBZ 取 stem；只裁剪关键词首尾空白，内部空格、括号、标点和连字符原样匹配。空字段对所有操作符均不命中；标签逐项匹配，`not_contains` 要求非空标签列表中全部不含关键词。
- 启用规则至少一条非空条件；匹配器只返回布尔结果，不写数据库，也不调用 Text Rules。Text Rules 提取的系列由扫描器持久化后供集合规则读取。

## Error Shape
```json
{
  "code": "PARSER_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "resource_id": "string|null"
}
```
