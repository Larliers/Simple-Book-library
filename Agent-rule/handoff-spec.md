# Handoff Spec

## Handoff Packet 定义
- Handoff Packet 是上游 Agent 向下游 Agent 下发任务的标准载体。
- 字段必须完整且字段名固定。

```json
{
  "packet_id": "string",
  "request_id": "string",
  "task_id": "string",
  "from_agent": "string",
  "to_agent": "string",
  "intent": "string",
  "priority": "P0|P1|P2",
  "scope": ["string"],
  "input": {},
  "constraints": ["string"],
  "expected_output": ["string"],
  "contracts": ["string"],
  "deadline": "ISO-8601",
  "trace_id": "string"
}
```

## Agent Output Envelope 定义
- Agent Output Envelope 是任务执行结果的统一回包结构。

```json
{
  "packet_id": "string",
  "request_id": "string",
  "task_id": "string",
  "from_agent": "string",
  "to_agent": "string",
  "status": "success|partial|failed",
  "summary": "string",
  "output": {},
  "errors": [
    {
      "code": "string",
      "message": "string",
      "retryable": true
    }
  ],
  "metrics": {
    "duration_ms": 0,
    "items_processed": 0
  },
  "produced_modules": ["string"],
  "log_refs": ["string"],
  "next_actions": ["string"],
  "trace_id": "string"
}
```

## 统一字段名
- 必选字段：`request_id`、`task_id`、`from_agent`、`to_agent`、`trace_id`。
- 任务意图字段固定为 `intent`，禁止使用同义替代字段。
- 输入输出根字段固定为 `input` / `output`。
- 错误集合字段固定为 `errors`，元素结构固定为 `code`、`message`、`retryable`。

## 示例：master-agent 下发 indexer-agent

```json
{
  "packet_id": "pkt-20260411-001",
  "request_id": "req-library-bootstrap",
  "task_id": "task-index-full-scan",
  "from_agent": "master-agent",
  "to_agent": "indexer-agent",
  "intent": "build_or_refresh_index",
  "priority": "P0",
  "scope": ["F:/Books", "F:/Comics"],
  "input": {
    "scan_mode": "incremental",
    "resource_types": ["pdf", "epub", "txt", "comic_folder"],
    "last_checkpoint": "2026-04-10T20:00:00Z"
  },
  "constraints": [
    "skip_hidden_paths",
    "max_depth=8",
    "do_not_block_ui"
  ],
  "expected_output": [
    "resource_index_delta",
    "scan_metrics",
    "error_list"
  ],
  "contracts": ["contracts/indexer-contract.md"],
  "deadline": "2026-04-11T18:00:00Z",
  "trace_id": "trace-idx-20260411-001"
}
```

## 示例：parser-agent 返回结果

```json
{
  "packet_id": "pkt-20260411-017",
  "request_id": "req-library-bootstrap",
  "task_id": "task-parse-batch-01",
  "from_agent": "parser-agent",
  "to_agent": "master-agent",
  "status": "success",
  "summary": "完成 240 个文件名与目录名的元数据解析",
  "output": {
    "parsed_count": 240,
    "normalized_records": 236,
    "unresolved_records": 4,
    "ruleset_version": "name-rule-v1"
  },
  "errors": [],
  "metrics": {
    "duration_ms": 1820,
    "items_processed": 240
  },
  "produced_modules": ["filename_parser"],
  "log_refs": ["logs/worklog.md#parse-20260411-01"],
  "next_actions": ["send_unresolved_to_manual_queue"],
  "trace_id": "trace-parse-20260411-017"
}
```
