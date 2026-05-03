# UI Contract

## Purpose
- 规范资源展示、交互事件与外部打开流程的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "view_mode": "list|waterfall|comic_grid",
  "data_source": {
    "resources": [
      {
        "resource_id": "string",
        "title": "string",
        "thumbnail_path": "string|null",
        "resource_type": "string",
        "path": "string",
        "cover_image_path": "string|null",
        "info_text": "string|null"
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

## Output Schema
```json
{
  "status": "success|partial|failed",
  "output": {
    "render_plan": {
      "view_mode": "list|waterfall|comic_grid",
      "visible_count": 0,
      "virtualized": true
    },
    "interaction_events": [
      {
        "event": "open_external|filter|sort|paginate|comic_favorite_toggle",
        "resource_id": "string|null",
        "timestamp": "ISO-8601"
      }
    ]
  },
  "errors": [],
  "trace_id": "string"
}
```

## Guarantees
- 保证 UI 不承担文件扫描职责。
- 保证列表/瀑布流模式共用统一字段。
- 保证关键交互事件可追踪。
- 保证 `comic_grid` 模式可展示 `info_text`。

## Error Shape
```json
{
  "code": "UI_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "view_mode": "string|null"
}
```
