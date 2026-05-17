# src 结构说明书（精简且完整）

更新时间：2026-05-17

## 1. 文档目标
- 保留字符串式文件路径结构。
- 给出每个代码组件（文件）的一句话用途。
- 作为 `src/` 结构与职责的当前事实文档。

## 2. 字符串式文件路径结构
```text
src/
├─ main.py
├─ sql/
│  └─ .gitkeep
├─ assets/
│  └─ icons/
│     ├─ collections.svg
│     ├─ favorites.svg
│     ├─ library.svg
│     ├─ menu_vertical.svg
│     ├─ refresh.svg
│     ├─ search.svg
│     ├─ settings.svg
│     ├─ trash.svg
│     ├─ view_grid.svg
│     └─ view_list.svg
└─ bookhub/
   ├─ __init__.py
   ├─ i18n/
   │  ├─ __init__.py
   │  ├─ language.py
   │  └─ locales/
   │     └─ zh-cn.json
   ├─ library/
   │  ├─ __init__.py
   │  ├─ metadata.py
   │  ├─ models.py
   │  ├─ repository.py
   │  ├─ scanner.py
   │  ├─ thumbnail_tasks.py
   │  ├─ thumbnail_worker.py
   │  └─ worker.py
   └─ ui/
      ├─ __init__.py
      ├─ app_window.py
      ├─ dialogs/
      │  ├─ __init__.py
      │  ├─ add_tag_dialog.py
      │  ├─ add_to_collection_dialog.py
      │  ├─ import_dialog.py
      │  └─ quick_add_dialog.py
      ├─ models/
      │  ├─ __init__.py
      │  └─ resource.py
      ├─ pages/
      │  ├─ __init__.py
      │  ├─ comic_page.py
      │  ├─ collections_page.py
      │  ├─ favorites_page.py
      │  ├─ library_page.py
      │  └─ settings_page.py
      ├─ resources/
      │  ├─ __init__.py
      │  ├─ assets.py
      │  ├─ layout_config.py
      │  └─ styles.py
      ├─ viewmodels/
      │  ├─ __init__.py
      │  └─ library_viewmodel.py
      └─ widgets/
         ├─ __init__.py
         ├─ book_card.py
         ├─ sidebar.py
         ├─ slide_toast.py
         └─ topbar.py
```

## 3. 每个代码组件的用处介绍

### 3.1 入口与运行目录
- `src/main.py`：应用入口；创建 Qt 应用并启动主窗口。
- `src/sql/.gitkeep`：运行数据目录占位，实际运行时生成 `library.db`、`scan_report.json`。

### 3.2 bookhub 包根
- `src/bookhub/__init__.py`：包标记与顶层命名空间。

### 3.3 国际化组件（bookhub/i18n）
- `src/bookhub/i18n/__init__.py`：国际化导出入口。
- `src/bookhub/i18n/language.py`：语言切换、词典加载、回退策略。
- `src/bookhub/i18n/locales/zh-cn.json`：中文文案键值表。

### 3.4 书库后端组件（bookhub/library）
- `src/bookhub/library/__init__.py`：后端模块导出入口。
- `src/bookhub/library/repository.py`：SQLite 读写中心；设置、书籍、书单、收藏、标签操作。
- `src/bookhub/library/scanner.py`：目录扫描与文件过滤；构建入库候选。
- `src/bookhub/library/metadata.py`：元数据提取与缩略图生成（WebP，`file://` 路径）。
- `src/bookhub/library/models.py`：扫描/任务的数据结构定义。
- `src/bookhub/library/worker.py`：扫描任务线程包装。
- `src/bookhub/library/thumbnail_tasks.py`：缩略图清理与重建任务实现。
- `src/bookhub/library/thumbnail_worker.py`：缩略图任务线程包装。

### 3.5 UI 主组件（bookhub/ui）
- `src/bookhub/ui/__init__.py`：UI 包导出入口。
- `src/bookhub/ui/app_window.py`：主窗口装配；连接 sidebar、topbar、pages 与后端任务。

### 3.6 对话框组件（bookhub/ui/dialogs）
- `src/bookhub/ui/dialogs/__init__.py`：对话框包入口。
- `src/bookhub/ui/dialogs/import_dialog.py`：导入相关对话框逻辑。
- `src/bookhub/ui/dialogs/add_tag_dialog.py`：添加标签对话框。
- `src/bookhub/ui/dialogs/add_to_collection_dialog.py`：旧版加入书单对话框（兼容保留）。
- `src/bookhub/ui/dialogs/quick_add_dialog.py`：快速添加标签/加入书单弹窗。

### 3.7 UI 数据模型（bookhub/ui/models）
- `src/bookhub/ui/models/__init__.py`：模型包入口。
- `src/bookhub/ui/models/resource.py`：UI 层 `ResourceItem` 资源模型。

### 3.8 页面组件（bookhub/ui/pages）
- `src/bookhub/ui/pages/__init__.py`：页面包入口。
- `src/bookhub/ui/pages/comic_page.py`：Comic/Comic Fav 页面；仅 grid 视图；封面双击外部打开；右键添加/移除收藏。
- `src/bookhub/ui/pages/library_page.py`：Library/Missed 页面；grid/list；右侧详情栏；单/双击交互。
- `src/bookhub/ui/pages/collections_page.py`：书单页与书单详情页；详情支持 grid/list 视图与侧键返回上一级。
- `src/bookhub/ui/pages/favorites_page.py`：收藏页；支持 grid/list 视图与排序持久化。
- `src/bookhub/ui/pages/settings_page.py`：设置页（扫描、匹配策略、卡片间距、缩略图任务、错误日志）；导航仅保留 General 与 Error logs；Library/Comic 路径列表项统一为“左侧单行路径+右侧固定删除按钮”布局，关闭横向滚动并确保窄宽度下删除按钮不被遮挡。

### 3.9 UI 资源组件（bookhub/ui/resources）
- `src/bookhub/ui/resources/__init__.py`：资源包入口。
- `src/bookhub/ui/resources/assets.py`：图标/资源加载。
- `src/bookhub/ui/resources/layout_config.py`：布局尺寸与间距配置。
- `src/bookhub/ui/resources/styles.py`：全局 QSS 样式。

### 3.10 视图模型组件（bookhub/ui/viewmodels）
- `src/bookhub/ui/viewmodels/__init__.py`：视图模型包入口。
- `src/bookhub/ui/viewmodels/library_viewmodel.py`：Library 查询过滤、视图模式、搜索建议状态。

### 3.11 小部件组件（bookhub/ui/widgets）
- `src/bookhub/ui/widgets/__init__.py`：小部件包入口。
- `src/bookhub/ui/widgets/sidebar.py`：左侧导航栏组件。
- `src/bookhub/ui/widgets/topbar.py`：顶部搜索栏与建议浮层。
- `src/bookhub/ui/widgets/book_card.py`：书籍卡片组件（常规卡片、cover-only 卡片）。
- `src/bookhub/ui/widgets/slide_toast.py`：右下角滑入提示组件。

## 4. 当前关键实现（简要）
- 缩略图：WebP 落盘，DB 保存 `file://` URL。
- 数据能力：Collections、Favorites、Tags 已接入。
- Library 展示：主区双栏，右侧详情栏常驻且可拖拽宽度。
- Favorites/CollectionDetail 展示：支持与 Library 一致的 grid/list 切换；主区接入右侧详情栏；详情页主区布局采用与 Library 相同的伸展策略，避免分栏贴底；grid 卡片采用 cover-only 样式并支持选中态；模式持久化到 `app_settings`。
- Settings 导航：仅保留 General 与 Error logs 两项；移除顶部搜索框、Shortcuts、Manage Metadata 占位区域。
- Reading Now 与 Tools 占位页已下线：主窗口不再注册对应页面，侧栏仅保留可用功能入口；底层 `status` 字段与数据结构保持不变。
- TopBar：移除右侧 IMPORT/NEW LIST/刷新/菜单占位区，搜索栏填充顶部可用宽度。
- TopBar：搜索框支持最小高度与字号放大；搜索输入与建议下拉字号可在 Settings 调节并持久化（默认 15px）。
- 网格布局：Library/Missed/Favorites/CollectionDetail 的书籍网格统一左内边距 12px，避免左侧贴边溢出观感。
- 交互规则：单击看详情（无门控延迟）、双击外部打开。

## 5. 边界与约束
- 当前导入粒度：目录导入（不支持单文件导入）。
- 当前支持格式：PDF、EPUB。
- 外部打开：依赖系统默认关联程序。

## 6. 维护要求
- 每次 `src/` 结构变化后，必须更新本文件。
- 每次开发后，必须在 `Agent-rule/logs/history/YYYY-MM-DD.md` 追加留档。
- 文档保持“当前事实”，历史细节放 `logs/history`，不在本文件堆叠。
