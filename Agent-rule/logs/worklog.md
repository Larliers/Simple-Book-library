# Worklog

## 最新记录
```json
{"log_id":"worklog-20260911-005","timestamp":"2026-09-11T13:05:00+08:00","actor":"ui-agent","task":"提交快捷键改动并触发远程 minor Release","changes":["提交快捷键、合集分键与侧键识别，不含 pyc","触发 GitHub Actions Release bump=minor，预期 v2.2.0"],"affected_files":[".github/workflows/release.yml"],"outputs":["origin/main 功能提交","workflow_dispatch Release"],"risks":["工作流会再提交 chore: release 并打 tag","Nuitka 远程构建可能超过一小时"],"next_actions":[]}
```

## 记录规则
- 每次任务执行后必须追加一条记录,该记录存放到logs文件夹下的history文件夹中，文件名以年-月-日进行命名，保存为md文档，本文件下方的内容仅为模板和实际参考
- 记录必须包含任务来源、影响范围、产出与风险。
- 字段名保持稳定，便于后续自动检索。

## 每次工作记录模板
```json
{
  "log_id": "worklog-YYYYMMDD-XXX",
  "timestamp": "ISO-8601",
  "actor": "master-agent|maintenance-agent|indexer-agent|parser-agent|thumbnail-agent|ui-agent",
  "task": "string",
  "changes": ["string"],
  "affected_files": ["string"],
  "outputs": ["string"],
  "risks": ["string"],
  "next_actions": ["string"]
}
```

## 初始启动记录
```json
{
  "log_id": "worklog-20260411-001",
  "timestamp": "2026-04-11T13:00:00Z",
  "actor": "maintenance-agent",
  "task": "初始化 Agent-rule 规则系统",
  "changes": [
    "创建标准目录结构",
    "初始化核心规则文件",
    "建立 agents/contracts/registry/logs 基线"
  ],
  "affected_files": [
    "Agent-rule/project-context.md",
    "Agent-rule/shared-rules.md",
    "Agent-rule/master-agent.md",
    "Agent-rule/maintenance-agent.md",
    "Agent-rule/handoff-spec.md"
  ],
  "outputs": ["v0.1.0 基线规则可用"],
  "risks": ["后续模块扩展需严格遵守字段稳定性"],
  "next_actions": ["执行首轮模块任务拆分并登记 registry"]
}
```

## 2026-09-11 - 提交并触发远程 Release

```json
{
  "log_id": "worklog-20260911-005",
  "timestamp": "2026-09-11T13:05:00+08:00",
  "actor": "ui-agent",
  "task": "提交快捷键改动并触发远程 minor Release",
  "changes": [
    "提交快捷键、合集分键与侧键识别，排除 pyc",
    "触发 GitHub Actions Release bump=minor"
  ],
  "affected_files": [".github/workflows/release.yml"],
  "outputs": ["origin/main 功能提交", "workflow_dispatch Release"],
  "risks": ["工作流会再提交 chore: release 并打 tag", "Nuitka 远程构建可能超过一小时"],
  "next_actions": []
}
```

## 2026-09-11 - 快捷键绑定识别鼠标侧键

```json
{
  "log_id": "worklog-20260911-004",
  "timestamp": "2026-09-11T13:10:00+08:00",
  "actor": "ui-agent",
  "task": "修复快捷键绑定无法识别鼠标侧键",
  "changes": [
    "JS 识别 button/which/buttons、BrowserBack 与 keyCode 166/167，并在 pointerdown/mousedown/mouseup/auxclick 去重录入",
    "ShortcutWebView 过滤 Chromium 子控件上的 Back/Forward",
    "Windows 原生过滤 WM_XBUTTONDOWN 与 WM_APPCOMMAND"
  ],
  "affected_files": [
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web_window.py",
    "src/tests/js/test_shortcuts.js",
    "src/tests/test_web_bridge_smoke.py",
    "Agent-rule/contracts/ui-contract.md",
    "Agent-rule/registry/module-registry.md"
  ],
  "outputs": [
    "侧键三条通道归一为 MouseBack/MouseForward",
    "专项测试覆盖映射、子控件与 auxclick 去重"
  ],
  "risks": [
    "Chromium 独立 HWND 仍可能不进 Qt 消息泵",
    "应用内未绑定的侧键不再触发网页前进/后退"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 合集退出/进入拆分与按页记忆

```json
{
  "log_id": "worklog-20260911-003",
  "timestamp": "2026-09-11T12:55:00+08:00",
  "actor": "ui-agent",
  "task": "把合集导航从单一切换拆成退出与进入最近系列，并按合集页独立记忆",
  "changes": [
    "新增 exit_collection 与 reopen_recent_collection，移除 toggle_recent_collection",
    "State.recentCollections 按 collections/novel_collections/comic_collections 分记",
    "非合集页、列表态退出、详情态进入分别提示"
  ],
  "affected_files": [
    "src/bookhub/library/repository.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/js/test_shortcuts.js",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/test_cover_grid_settings.py"
  ],
  "outputs": [
    "设置导航组显示进入最近系列与退出当前系列",
    "专项测试覆盖三类独立记忆与删除失效"
  ],
  "risks": [
    "已保存的 toggle_recent_collection 绑定不会迁移",
    "全量测试仍有两个既有非法整型失败"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 关闭 open_resource 可追踪交互事件

```json
{
  "log_id": "worklog-20260911-002",
  "timestamp": "2026-09-11T12:45:00+08:00",
  "actor": "ui-agent",
  "task": "接管 Codex 快捷键 WIP 并补齐审查未结案的外部打开事件",
  "changes": [
    "openResource 成功解析到存在的目标后发出 event/resource_id/timestamp",
    "缺失资源或缺失文件不发出成功事件，仍走原有 toast",
    "同步 Shortcut 合同、shortcut_action_dispatcher 输出与 Bridge 冒烟断言"
  ],
  "affected_files": [
    "src/bookhub/ui/web_bridge.py",
    "src/tests/test_web_bridge_smoke.py",
    "Agent-rule/contracts/ui-contract.md",
    "Agent-rule/registry/module-registry.md"
  ],
  "outputs": [
    "interactionEvent 信号可被测试连接断言",
    "Repository/Bridge 专项 47 项通过"
  ],
  "risks": [
    "全量测试仍有 2 个既有非法整型设置容错失败",
    "Vaporwave 仍有 2 个既有 SpaceMono 字体 404"
  ],
  "next_actions": []
}
```

## 2026-09-09 - 新增随机推荐页面

```json
{
  "log_id": "worklog-20260909-003",
  "timestamp": "2026-09-09T13:10:10+08:00",
  "actor": "ui-agent",
  "task": "新增图书、小说、漫画三列随机推荐页面及会话缓存",
  "changes": [
    "新增 random_recommendations 导航、只读 Bridge 接口与三列推荐视图",
    "推荐卡所有详情和资源动作继承列级 sourcePage",
    "仅扫描、资源新增/删除使缓存失效，并用 request id 阻止旧回调写回",
    "补齐 Glass/Vaporwave 样式、中文文案、行为测试与实际 GUI 验收"
  ],
  "affected_files": [
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/ui/web_window.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web/css/base.css",
    "src/bookhub/ui/web/css/skins/glass/components.css",
    "src/bookhub/ui/web/css/skins/vaporwave/components.css",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/js/test_random_recommendations.js"
  ],
  "outputs": [
    "每类最多 3 项且来源隔离的会话级推荐",
    "可执行的前端缓存、重抽、并发与来源路由行为测试",
    "Agent-rule/logs/evidence/2026-09-09-random-recommendations-gui.md"
  ],
  "risks": [
    "全量测试仍有 2 个既有非法整型设置容错失败",
    "Vaporwave 仍有 2 个既有 SpaceMono 字体 404"
  ],
  "next_actions": []
}
```


---

## 2026-04-13 - Collections & Favorites 模块实现

### 任务
完善 Collections 和 Favorites 模块（自定义书单），以及配套的右键菜单功能。

### 实现内容

**新增文件**:
1. `src/bookhub/ui/pages/collections_page.py`
   - `CollectionsPage` - 主书单列表页，网格展示，支持增删改
   - `CollectionCard` - 书单卡片（彩色首字母封面）
   - `CollectionDetailPage` - 书单内书籍列表

2. `src/bookhub/ui/pages/favorites_page.py`
   - `FavoritesPage` - 收藏书籍展示页
   - `FavoriteBookCard` - 收藏书籍卡片

3. `src/bookhub/ui/dialogs/add_to_collection_dialog.py`
   - `AddToCollectionDialog` - 添加到书单对话框
   - 支持搜索书单、复选框批量选择、新建书单

**修改文件**:
4. `src/bookhub/library/repository.py`
   - 新增 SQLite 表：collections, collection_books, favorite_books
   - 新增 15 个 CRUD 方法支持书单和收藏功能

5. `src/bookhub/ui/widgets/book_card.py`
   - 新增 `install_book_context_menu()` 函数
   - 右键菜单：添加/移除收藏、添加到书单

6. `src/bookhub/ui/app_window.py`
   - 将 Collections 和 Favorites PlaceholderPage 替换为真实页面

### 技术栈
- PySide6 (UI framework)
- SQLite (通过现有 LibraryRepository._connection() 扩展)
- hashlib (书单封面颜色哈希)

### 设计决策
- 书单封面使用书单名称的 MD5 哈希选取颜色，显示首字母缩写（类似 Google Material Design）
- 右键菜单通过 `install_book_context_menu()` 函数在外部安装，不侵入 BookCardWidget 原有结构
- 收藏和书单使用独立 SQLite 表，与现有 books 表通过 book_id 关联
- 懒初始化 DB 表（首次调用时创建），不修改 _init_db 方法

### 后续
- 在 library_page.py 中调用 `install_book_context_menu(card, repository)` 后，右键菜单即可生效

---

## 2026-04-23 - QuickAddDialog 顶部白色层问题留档（仅记录）

### 任务
用户反馈右键弹窗中“添加标签”文字下方仍有白色层，本次仅做问题留档，不继续改代码。

### 现象
- 已移除书名条样式层与书单左侧 LIST 列后，顶部区域仍存在层级感（白色/浅色层视觉）。

### 初步判断
- 问题更可能来自 `titleBar` 容器样式而非 `bookLabel` 文本自身。
- 重点关注：
  - `QWidget#titleBar` 的 `background-color`
  - `QWidget#titleBar` 的 `border-bottom`

### 影响文件（观察范围）
- `src/bookhub/ui/dialogs/quick_add_dialog.py`
- `src/bookhub/ui/resources/styles.py`（如需排查全局样式覆盖）

### 风险
- 若直接调整标题栏样式，可能影响弹窗边界层次感与关闭按钮可见性，需要视觉回归确认。

### 后续建议
1. 将 `titleBar` 背景与 `dialogBody` 统一；
2. 去除 `titleBar` 下边框分割线；
3. 若问题仍在，排查全局 QSS 通配规则优先级。

---

## 2026-05-03 - Settings 路径删除按钮遮挡修复

### 任务
修复 Settings 页面中 Library/Comic 路径列表右侧 Delete 按钮被遮挡的问题。

### 实现内容

**修改文件**:
1. `src/bookhub/ui/pages/settings_page.py`
   - 引入 `Qt` 与 `QAbstractItemView`。
   - `folders` 与 `comic_folders` 统一设置滚动策略：
     - 关闭横向滚动条 `ScrollBarAlwaysOff`
     - 垂直滚动模式 `ScrollPerPixel`
     - 垂直滚动条 `ScrollBarAsNeeded`
   - 路径行构建重构为共享方法 `_append_root_row(...)`，避免 Library/Comic 两套逻辑漂移。
   - 路径标签改为单行显示（`setWordWrap(False)`），并保留文本可选中与 tooltip。
   - Delete 按钮设置最小宽度 `72` 且右对齐，行右侧内边距增加到 `12`，保证窄宽度下不被遮挡。

2. `src_construction.md`
   - 在 `settings_page.py` 条目中插入本次修复说明，更新当前事实文档。

### 风险与验证
- 风险较低：仅调整设置页路径行布局与列表滚动策略，不涉及扫描/存储逻辑。
- 验证标准：窄窗口宽度下 Delete 按钮完整可见且可点击；Library/Comic 两个列表行为一致。
