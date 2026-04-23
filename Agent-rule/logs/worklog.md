# Worklog

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
