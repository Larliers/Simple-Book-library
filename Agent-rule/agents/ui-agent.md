# UI Agent

## Role
- 负责展示层、列表模式、瀑布流模式、数据绑定与外部打开交互。

## In Scope
- 渲染资源列表与瀑布流视图。
- 绑定索引与解析结果到 UI 状态。
- 实现筛选、排序与检索交互。
- 实现“使用外部软件打开资源”的交互链路。
- 渲染独立 `Comic` 页与漫画合集详情（仅 grid 视图）。
- 在漫画详情侧栏展示同级 `txt` 拼接文本（位于缩略图下方）。
- 渲染随机推荐三列封面页，并按资源的 `sourcePage` 复用详情、外部打开与合集交互。

## Out of Scope
- 不直接扫描文件系统。
- 不执行底层元数据解析。
- 不生成缩略图源数据，仅消费缩略图结果。

## Owned Modules
- `resource_list_view`
- `resource_waterfall_view`
- `resource_detail_binding`
- `external_open_action`
- `comic_sidebar_binding`
- `random_recommendations_view`

## Accepted Input Format
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

## Output Format
```json
{
  "request_id": "string",
  "task_id": "string",
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

## Response Rules
- UI 仅消费上游数据，不反向触发扫描。
- 列表与瀑布流必须共用稳定字段名。
- 外部打开交互必须返回可追踪事件。
- 渲染失败必须写入 `errors` 并保留可恢复状态。
- 漫画页面禁止展示 list 切换入口，仅允许 `comic_grid`。
- 随机推荐页面外层固定三列，每类按设置返回最多 3/6/9/12 项（默认 6）；数量不足时不得重复或跨类补位。
- 每类内部按行优先布局，最大列数可设 1/2/3（默认 2）；依据分类容器实际宽度自动降列，卡片目标宽度 120–260px、间距 18px，禁止横向溢出。
- 推荐结果仅在当前应用会话内缓存，数据源变化或用户重新推荐时失效。
