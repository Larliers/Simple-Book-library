# src 结构说明书（Simple-Book-library）

## 文档目标
- 本文件用于解释 `src` 目录的当前结构与职责分层。
- 说明方式以“字符串路径图 + 文件职责说明”为主，便于后续开发快速定位。
- 约定：`__pycache__/` 属于运行时缓存产物，不作为业务结构说明主体。

## 字符串路径图（2026-04-12）
```text
src/
├─ main.py
├─ assets/
│  └─ icons/
│     ├─ collections.svg
│     ├─ favorites.svg
│     ├─ library.svg
│     ├─ menu_vertical.svg
│     ├─ reading_now.svg
│     ├─ refresh.svg
│     ├─ search.svg
│     ├─ settings.svg
│     ├─ tools.svg
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
   └─ ui/
      ├─ __init__.py
      ├─ app_window.py
      ├─ dialogs/
      │  ├─ __init__.py
      │  ├─ add_tag_dialog.py
      │  └─ import_dialog.py
      ├─ models/
      │  ├─ __init__.py
      │  └─ resource.py
      ├─ pages/
      │  ├─ __init__.py
      │  ├─ library_page.py
      │  ├─ placeholder_page.py
      │  ├─ plugins_page.py
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
         └─ topbar.py
```

## 分层职责总览
- `src/main.py`：程序入口，启动 `QApplication` 并展示主窗口。
- `src/assets/icons/`：UI 使用的本地 SVG 图标资源，避免系统图标平台差异。
- `src/bookhub/i18n/`：语言切换与文案读取层（当前支持 `en` 与 `zh-cn` 资源文件）。
- `src/bookhub/ui/`：界面主层，按 `resources -> models/viewmodels -> widgets/pages/dialogs -> app_window` 组织。

## 启动链路（运行时）
```text
main.py
  -> AppWindow (ui/app_window.py)
    -> SidebarWidget / TopBarWidget
    -> LibraryPage / SettingsPage / PluginsPage / PlaceholderPage
    -> LibraryViewModel (提供页面状态与假数据)
    -> LanguageManager (文案翻译)
```

## 关键目录与文件说明

### 1) 入口层
- `src/main.py`
  - 创建 Qt 应用实例。
  - 创建并显示 `AppWindow`。
  - 负责事件循环生命周期返回值。

### 2) 静态资源层
- `src/assets/icons/*.svg`
  - 全局图标资产（侧边栏、TopBar、视图切换等）。
  - 由 `ui/resources/assets.py` 统一读取并转换为 `QIcon/QPixmap`。

### 3) 包根与国际化层（bookhub）
- `src/bookhub/__init__.py`
  - 包标记文件。
- `src/bookhub/i18n/language.py`
  - `LanguageManager`：维护当前语言、缓存词典、读取 `locales/*.json`。
  - `tr(key, english_text)`：统一翻译入口，未命中时回退英文默认文案。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 中文翻译词典，覆盖侧边栏、TopBar、Library、Settings、Plugins、标签弹窗文案。
- `src/bookhub/i18n/__init__.py`
  - 导出 `language_manager` 与 `tr`。

### 4) UI 主层（bookhub/ui）
- `src/bookhub/ui/app_window.py`
  - 主窗口编排器。
  - 组装侧边栏、顶部栏、页面堆栈（`QStackedWidget`）。
  - 管理页面切换、搜索联动、导入弹窗、语言重翻译。
- `src/bookhub/ui/resources/layout_config.py`
  - `UiLayoutConfig`：集中定义页面尺寸常量（侧边栏宽度、卡片尺寸、间距、封面比例等）。
- `src/bookhub/ui/resources/styles.py`
  - `APP_STYLE`：全局 QSS 样式令牌与组件样式规则。
- `src/bookhub/ui/resources/assets.py`
  - 图标路径与加载工具函数（`icon_path/load_icon/load_pixmap`）。
- `src/bookhub/ui/models/resource.py`
  - `ResourceItem`：图书资源数据模型（标题、作者、状态、标签、路径、封面路径等）。
- `src/bookhub/ui/viewmodels/library_viewmodel.py`
  - `UiState`：UI 状态容器（筛选、分页、搜索建议、选中项等）。
  - `LibraryViewModel`：维护视图模式、筛选逻辑、事件数据输入封装（`UiInputEnvelope`）与本地假数据。
- `src/bookhub/ui/widgets/sidebar.py`
  - 侧边栏导航组件，包含导航按钮、导入按钮、设置入口与自适应字体/图标缩放。
- `src/bookhub/ui/widgets/topbar.py`
  - 顶部栏组件，包含搜索框、建议下拉、导入按钮、刷新与菜单按钮。
- `src/bookhub/ui/widgets/book_card.py`
  - 图书卡片组件，负责封面展示、标题作者、状态与标签信息。
- `src/bookhub/ui/pages/library_page.py`
  - 核心书库页面。
  - 提供网格/列表双视图、右键菜单、标签弹窗、交互事件记录（`interaction_events`）。
- `src/bookhub/ui/pages/settings_page.py`
  - 设置页面骨架。
  - 提供启动项、语言切换、书库目录列表、扫描/元数据按钮等。
- `src/bookhub/ui/pages/plugins_page.py`
  - 插件管理页面骨架。
  - 提供插件列表、详情、描述与操作按钮展示。
- `src/bookhub/ui/pages/placeholder_page.py`
  - 占位页组件，用于 `collections/reading_now/favorites/trash` 等未实现页面。
- `src/bookhub/ui/dialogs/import_dialog.py`
  - 导入图书弹窗骨架，模拟文件浏览与文件类型选择流程。
- `src/bookhub/ui/dialogs/add_tag_dialog.py`
  - 添加标签弹窗，支持最近标签与自定义书单选择。
- `src/bookhub/ui/**/__init__.py`
  - 子包标记文件，维持包结构清晰。

## 当前实现边界（基于代码现状）
- 当前 `LibraryViewModel` 内置的是演示假数据，尚未接入真实扫描/索引链路。
- `ImportDialog` 以 UI 骨架为主，文件系统导入流程尚未打通。
- 多个页面属于“壳层完成、业务待接入”状态，符合当前项目的 UI 先行阶段目标。

## 维护约定（后续更新本文件时）
- 新增或删除 `src` 文件时，先更新“字符串路径图”，再更新“关键目录与文件说明”。
- 文案必须描述“文件在架构中的职责”，而非仅重复文件名。
- 每次任务结束时同步更新本文件，以保证结构说明与实际代码一致。
