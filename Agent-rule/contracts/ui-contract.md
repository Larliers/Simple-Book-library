# UI Contract

## Purpose
- 规范资源展示、交互事件与外部打开流程的数据契约。

## Input Schema
```json
{
  "request_id": "string",
  "task_id": "string",
  "view_mode": "list|grid|cover_grid|waterfall|comic_grid|recommendation_grid|tag_index|tag_detail",
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
      "view_mode": "list|grid|cover_grid|waterfall|comic_grid|recommendation_grid|tag_index|tag_detail",
      "visible_count": 0,
      "virtualized": true
    },
    "interaction_events": [
      {
        "event": "open_external|filter|sort|paginate|comic_favorite_toggle|reroll_recommendations|open_tag",
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
- 保证 Text Novel 主页与小说合集详情提供四档排序：`file_mtime_desc` / `file_mtime_asc` / `title_asc` / `title_desc`；主页与合集分键持久化，默认 `file_mtime_desc`；合集详情按所选 SQL 排序。图书馆、书籍合集与随机推荐不受影响。
- 保证随机推荐按 Library/Text Novel/Comic 三个来源分别返回最多 `recommendationItemsPerCategory` 个不重复且未缺失的资源；允许值为 3/6/9/12，默认 6。
- 保证每个推荐列携带 `sourcePage`，列内卡片继承该来源上下文；详情与打开动作必须使用该来源上下文。
- 保证标签目录和详情仅统计当前 `tagManagerScopes` 纳入的未缺失资源；混合卡片携带真实 `sourcePage` 并复用来源动作。

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
  "recommendationsInvalidated": false,
  "tagCatalogInvalidated": false
}
```

- `recommendationsInvalidated=true` 仅表示推荐候选集合因扫描、资源根增删或资源删除而变化；标签、收藏、合集、排序、封面与缩略图更新必须保持 `false`。
- 前端收到 `true` 时必须淘汰进行中的旧推荐响应，并从最新候选集合整组重抽。
- `tagCatalogInvalidated=true` 仅表示标签候选集合因扫描、资源删除或标签增删而变化；收藏、合集、封面与缩略图更新保持 `false`。前端必须用 request id 丢弃旧目录/详情响应。
- settings payload 必须提供 `recommendationItemsPerCategory`（3/6/9/12，默认 6）与 `recommendationColumnsPerCategory`（1/2/3，默认 2）。数量变化使会话推荐缓存失效；内部列数变化只重排现有推荐。
- settings payload 必须提供 `textNovelViewMode`（`grid|list`，默认 `grid`）；Text Novel 顶部切换后立即持久化，Library 的现有视图状态不受影响。
- Text Novel 主页 payload 必须提供 `sort`（`file_mtime_desc|file_mtime_asc|title_asc|title_desc`，默认 `file_mtime_desc`），对应设置键 `text_novel_sort_order_main`；小说合集详情另用 `text_novel_sort_order_fav`，成员列表必须按所选排序。
- Settings 的缩略图管理必须分别提供 Library、Comic 与 Text Novel 的清空/重建入口；Text Novel 两个入口通过 `scope=text_novel` 调用既有任务通道。
- 外层固定三列；每类内部按行优先排列，设置列数仅为上限。容器宽度不足时按 120px 目标最小宽度从 3→2→1 列降级，卡片最大 260px、间距 18px，极窄时允许继续缩小且不得横向溢出。

## Tag Management Extension

settings payload 必须提供三个互斥来源开关，默认全选且至少一项为 `true`：

```json
{
  "tagManagerScopes": {
    "library": true,
    "text_novel": true,
    "comic": true
  }
}
```

- `setTagManagerScopes(payloadJson)` 仅接受上述三个布尔字段，原子校验后返回 `{ok,error,scopes}`；全关时返回 `error=empty_scope` 且不写入。
- `getTagCatalog(order)` 返回 `mode=tag_index`、`order=asc|desc`、唯一标签总数和字母分组；中文按完整拼音排序并以拼音首字母分组，英文忽略大小写排序，数字/符号进入始终置尾的 `#`。
- 降序同时反转字母组与组内标签顺序，排序只保留在当前会话。
- `getTagResources(tag)` 返回 `mode=tag_detail`、精确大小写标签名及按 Library/Text Novel/Comic 稳定来源顺序排列的混合资源；每项必须包含 `sourcePage`。
- 用户从目录进入标签详情时，Bridge 必须发出 `open_tag` 交互事件（`event`、`resource_id`=精确标签名、`timestamp`）；空/空白标签不发，空详情仍发。`getTagResources`、改范围、改排序、失效重载和返回目录后重载不得发出。
- `addResourceTag(page,resourceId,tag)` / `removeResourceTag(...)` 支持三类来源；旧两参数 `addTag` / `removeTag` 只作为 Library 兼容入口保留。
- 标签页禁用顶部搜索，不提供全局重命名或删除；空详情仍保留标题、返回入口和空状态。
- 目录与快捷添加候选必须截掉早期元数据字段标签：`author:` / `publisher:` / `language:` / `series:`（允许空格与全角冒号）。作者、出版社、语言继续走独立列，不再写入 `tags_json`。
- `exit_collection` / `reopen_recent_collection` 在标签管理页同样表示后退/前进：详情态退出并记住本次会话最近标签，目录态重开；不新增动作 ID。

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
- 合集导航拆成 `exit_collection`（退出当前系列）与 `reopen_recent_collection`（进入最近系列），语义对应后退/前进；在合集页按三类合集独立记忆，在标签管理页改为退出/重开最近标签。
- 最近系列与最近标签仅保存于当前前端会话；成功打开或退出详情时更新，重启不恢复；合集目标删除后只清空该页记忆并提示。

## Error Shape
```json
{
  "code": "UI_ERROR_CODE",
  "message": "string",
  "retryable": true,
  "view_mode": "string|null"
}
```
