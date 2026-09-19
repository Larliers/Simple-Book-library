# UI Agent

## Role
- 负责展示层、封面网格、列表模式、瀑布流模式、数据绑定与外部打开交互。

## In Scope
- 渲染资源列表与瀑布流视图。
- 绑定索引与解析结果到 UI 状态。
- 实现筛选、排序与检索交互。
- 实现“使用外部软件打开资源”的交互链路。
- 渲染独立 `Comic` 页与漫画合集详情（仅 grid 视图）。
- 渲染 Text Novel 独立持久化的 Grid/List；Grid 展示封面和标题，List 不展示封面列。
- 渲染 Text Novel 主页与小说合集详情的十档排序下拉；List 模式的标题/作者/标签/路径表头可点击切换升降序，并与下拉共享后端持久化状态。
- 渲染 Library 主页与书籍合集详情的持久化排序；Library List 保留封面列，四个文本表头与下拉共享后端状态，书籍合集另保留加入时间升降序。
- 在漫画详情侧栏展示同级 `txt` 拼接文本（位于缩略图下方）。
- 渲染随机推荐三列封面页，并按资源的 `sourcePage` 复用详情、外部打开与合集交互。
- 渲染标签目录与标签详情混合封面网格，维护会话排序、请求失效和来源感知交互。
- 维护可持久化快捷键设置页、统一资源动作分发器、原生鼠标侧键输入和会话内最近系列导航。
- 维护三类资源共用的 Quick Add 合集交互；批量保存成员关系、快捷创建同 kind 合集，并定向回写而不重建当前资源列表。

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
- `tag_management_view`
- `shortcut_action_dispatcher`
- `quick_add_collection_membership`

## Accepted Input Format
```json
{
  "request_id": "string",
  "task_id": "string",
  "view_mode": "list|cover_grid|waterfall|comic_grid|recommendation_grid|tag_index|tag_detail",
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
      "view_mode": "list|cover_grid|waterfall|comic_grid|recommendation_grid|tag_index|tag_detail",
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

## Response Rules
- UI 仅消费上游数据，不反向触发扫描。
- 列表与瀑布流必须共用稳定字段名。
- 外部打开交互必须返回可追踪事件。
- 渲染失败必须写入 `errors` 并保留可恢复状态。
- 漫画页面禁止展示 list 切换入口，仅允许 `comic_grid`。
- Text Novel 首次默认 `grid`，设置 `textNovelViewMode` 仅允许 `grid|list` 并跨启动恢复。
- Library 主页默认 `title_asc`，书籍合集详情默认 `added_desc`；两页分别持久化。主页支持十档字段排序，合集另支持 `added_asc|added_desc`，List 保留封面列并提供可访问的表头升降序按钮。
- 随机推荐页面外层固定三列，每类按设置返回最多 3/6/9/12 项（默认 6）；数量不足时不得重复或跨类补位。
- 每类内部按行优先布局，最大列数可设 1/2/3（默认 2）；依据分类容器实际宽度自动降列，卡片目标宽度 120–260px、间距 18px，禁止横向溢出。
- 推荐结果仅在当前应用会话内缓存，数据源变化或用户重新推荐时失效。
- 标签目录按中文拼音/英文 A–Z 分组，`#` 始终置尾；A→Z/Z→A 仅会话保存，目录与详情请求用 request id 拒绝旧响应。
- 用户从标签目录进入详情时发出 `open_tag`；`getTagResources`、改范围、改排序、失效重载和返回目录后重载不发。
- 标签详情固定按 Library/Text Novel/Comic 来源顺序混排，每张卡必须用真实 `sourcePage` 路由详情、双击、右键和快捷操作；两套皮肤及 1120px 响应式不得横向溢出。
- 设置页标签范围为 Library/Text Novel/Comic 三个独立复选项，至少保留一个；范围变化立即刷新当前标签目录或详情。
- 右键菜单和快捷键必须通过相同动作 ID 执行；当前资源上下文从页面选择解析，随机推荐继承列级 `sourcePage`。
- 快捷键录入使用 `KeyboardEvent.code` 或 `MouseBack`/`MouseForward`，拒绝冲突与保留按键；非录入状态在输入控件、模态框及 Text Rules 内不得触发。
- 合集导航拆成退出当前系列与进入最近系列两个动作，语义对应后退/前进；书籍/小说/漫画合集各自只保留本次启动中该页最后一次成功打开项；同一动作在标签管理页退出/重开最近标签；重启不恢复；失效目标必须清除并提示。
- 标签目录不展示 `author:` / `publisher:` / `language:` / `series:` 字段前缀标签。
- Quick Add 合集提交必须经 `applyCollectionQuickAdd` 一次完成；成功后只更新对应合集页缓存与当前详情。仅从当前打开合集移除可见资源时允许保存滚动位置后重绘该合集详情。
