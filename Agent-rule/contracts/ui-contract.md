# UI Contract

## Purpose
- 规范资源展示、交互事件与外部打开流程的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "view_mode": "list|waterfall|comic_grid|recommendation_grid",
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
      "view_mode": "list|waterfall|comic_grid|recommendation_grid",
      "visible_count": 0,
      "virtualized": true
    },
    "interaction_events": [
      {
        "event": "open_external|filter|sort|paginate|comic_favorite_toggle|reroll_recommendations",
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
- 保证随机推荐按 Library/Text Novel/Comic 三个来源分别返回最多 `recommendationItemsPerCategory` 个不重复且未缺失的资源；允许值为 3/6/9/12，默认 6。
- 保证每个推荐列携带 `sourcePage`，列内卡片继承该来源上下文；详情与打开动作必须使用该来源上下文。

## Random Recommendations Extension
```json
{
  "mode": "recommendations",
  "columns": [
    {"key": "books", "sourcePage": "library", "items": []},
    {"key": "novels", "sourcePage": "text_novel", "items": []},
    {"key": "comics", "sourcePage": "comic", "items": []}
  ]
}
```

## Resource Change Signal
```json
{
  "pages": {},
  "recommendationsInvalidated": false
}
```

- `recommendationsInvalidated=true` 仅表示推荐候选集合因扫描、资源根增删或资源删除而变化；标签、收藏、合集、排序、封面与缩略图更新必须保持 `false`。
- 前端收到 `true` 时必须淘汰进行中的旧推荐响应，并从最新候选集合整组重抽。
- settings payload 必须提供 `recommendationItemsPerCategory`（3/6/9/12，默认 6）与 `recommendationColumnsPerCategory`（1/2/3，默认 2）。数量变化使会话推荐缓存失效；内部列数变化只重排现有推荐。
- 外层固定三列；每类内部按行优先排列，设置列数仅为上限。容器宽度不足时按 120px 目标最小宽度从 3→2→1 列降级，卡片最大 260px、间距 18px，极窄时允许继续缩小且不得横向溢出。

## Error Shape
```json
{
  "code": "UI_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "view_mode": "string|null"
}
```
