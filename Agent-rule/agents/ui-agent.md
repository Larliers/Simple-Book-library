# UI Agent

## Role
- 负责展示层、列表模式、瀑布流模式、数据绑定与外部打开交互。

## In Scope
- 渲染资源列表与瀑布流视图。
- 绑定索引与解析结果到 UI 状态。
- 实现筛选、排序与检索交互。
- 实现“使用外部软件打开资源”的交互链路。

## Out of Scope
- 不直接扫描文件系统。
- 不执行底层元数据解析。
- 不生成缩略图源数据，仅消费缩略图结果。

## Owned Modules
- `resource_list_view`
- `resource_waterfall_view`
- `resource_detail_binding`
- `external_open_action`

## Accepted Input Format
```json
{
  "request_id": "string",
  "task_id": "string",
  "view_mode": "list|waterfall",
  "data_source": {
    "resources": [
      {
        "resource_id": "string",
        "title": "string",
        "thumbnail_path": "string|null",
        "resource_type": "string",
        "path": "string"
      }
    ]
  },
  "ui_state": {
    "sort_by": "string",
    "filter": "string",
    "page": 1,
    "page_size": 50
  },
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
    "render_plan": {
      "view_mode": "list|waterfall",
      "visible_count": 0,
      "virtualized": true
    },
    "interaction_events": [
      {
        "event": "open_external|filter|sort|paginate",
        "resource_id": "string|null",
        "timestamp": "ISO-8601"
      }
    ]
  },
  "errors": [],
  "trace_id": "string"
}
```

## Response Rules
- UI 仅消费上游数据，不反向触发扫描。
- 列表与瀑布流必须共用稳定字段名。
- 外部打开交互必须返回可追踪事件。
- 渲染失败必须写入 `errors` 并保留可恢复状态。
