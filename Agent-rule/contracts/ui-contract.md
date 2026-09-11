# UI Contract

## Purpose
- 规范资源展示、交互事件与外部打开流程的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "view_mode": "list|grid|cover_grid|waterfall|comic_grid|recommendation_grid",
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
      "view_mode": "list|grid|cover_grid|waterfall|comic_grid|recommendation_grid",
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
- 保证 Text Novel 的 `grid` 显示封面和标题，`list` 不渲染封面列；两种模式复用详情、打开和右键交互。
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
- settings payload 必须提供 `textNovelViewMode`（`grid|list`，默认 `grid`）；Text Novel 顶部切换后立即持久化，Library 的现有视图状态不受影响。
- Settings 的缩略图管理必须分别提供 Library、Comic 与 Text Novel 的清空/重建入口；Text Novel 两个入口通过 `scope=text_novel` 调用既有任务通道。
- 外层固定三列；每类内部按行优先排列，设置列数仅为上限。容器宽度不足时按 120px 目标最小宽度从 3→2→1 列降级，卡片最大 260px、间距 18px，极窄时允许继续缩小且不得横向溢出。

## Shortcut Bindings Extension

settings payload 必须提供完整的 `shortcutBindings`，八个固定动作即使未绑定也必须返回空字符串：

```json
{
  "shortcutBindings": {
    "exit_collection": "",
    "reopen_recent_collection": "",
    "open_resource": "",
    "open_folder": "",
    "quick_add": "",
    "edit_cover": "",
    "remove_from_collection": "",
    "remove_from_library": ""
  }
}
```

`setShortcutBinding(actionId, inputToken)` 返回：

```json
{
  "ok": true,
  "error": "",
  "conflictAction": "",
  "bindings": {}
}
```

- `inputToken` 使用 `KeyboardEvent.code` 与固定修饰键顺序 `Ctrl+Alt+Shift+Meta+Code`，或 `MouseBack` / `MouseForward`；空字符串表示清除。
- 一个动作仅允许一个输入，一个输入仅允许一个动作；冲突返回 `error=duplicate` 与占用动作，不覆盖原绑定。
- `nativeShortcutInput(inputToken)` 与键盘事件进入同一分发器；原生视图必须在自身及 Chromium 子控件上过滤并吞掉鼠标侧键的按下和释放事件，避免网页历史前进/后退。
- 侧键录入与触发还必须接受页面 `button=3/4`、`which=4/5`、`buttons` 的 X1/X2 位、系统 `BrowserBack`/`BrowserForward`/`keyCode` 166/167，以及 Windows `WM_XBUTTONDOWN` / `WM_APPCOMMAND`，并规范化为 `MouseBack`/`MouseForward`。
- 同一侧键在 `mousedown` / `mouseup` / `auxclick` / `pointerdown` 上只消费一次，避免重复录入。
- 快捷键仅在应用聚焦时生效；输入/下拉/可编辑区域、普通模态框及 Text Rules 面板开启时暂停，录入状态除外。
- 统一动作上下文必须包含当前选中资源的真实页面来源、资源、合集详情标记与合集 ID；无选择或不可用动作必须提示，危险动作继续确认。
- `open_resource` 必须经 Bridge 在成功解析到可打开目标后发出 `open_external` 交互事件（`event`、`resource_id`、`timestamp`）；资源或文件不存在时不得发出成功事件。
- 合集导航拆成 `exit_collection`（退出当前系列）与 `reopen_recent_collection`（进入最近系列），语义对应后退/前进；仅在当前合集页生效，书籍/小说/漫画合集各自只记本页最近一次成功打开项。
- 最近系列仅保存于当前前端会话；成功打开或退出详情时更新对应合集页，重启不恢复；目标删除后只清空该页记忆并提示。

## Error Shape
```json
{
  "code": "UI_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "view_mode": "string|null"
}
```
