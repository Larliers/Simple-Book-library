# src 结构说明书（Simple-Book-library）

## 文档目标
- 解释 `src` 目录当前结构、职责分层与关键运行链路。
- 采用"字符串路径图 + 职责说明"形式，便于快速定位。
- 运行缓存（如 `__pycache__/`）不作为业务结构主体。

## 字符串路径图（2026-04-12）
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
         ├─ slide_toast.py
         └─ topbar.py
```

## 分层职责总览
- `main.py`：程序入口，启动 `QApplication` 并以默认最大化方式打开主窗口。
- `assets/icons/`：本地 SVG 图标资源。
- `sql/`：运行期 SQLite 与扫描报告目录（当前用 `.gitkeep` 占位）。
- `bookhub/i18n/`：语言管理与文案词典加载。
- `bookhub/library/`：书库后端核心层（SQLite 存储、扫描、元数据提取、缩略图生成、后台 worker）。
- `bookhub/ui/`：界面与交互层，消费 `library` 层输出。

## 启动链路（运行时）
```text
main.py
  -> AppWindow (ui/app_window.py)
  -> showMaximized() 默认最大化显示
    -> LibraryRepository (library/repository.py)
    -> LibraryViewModel (ui/viewmodels/library_viewmodel.py)
    -> Sidebar/TopBar/Pages
    -> SettingsPage 信号（Add/Remove Path、扫描深度、哈希策略、立即扫描）
    -> ScanWorker (library/worker.py, QThread)
      -> scan_roots (library/scanner.py)
        -> metadata/thumbnail (library/metadata.py)
        -> sqlite 持久化 + scan_report.json
    -> ThumbnailTaskWorker (library/thumbnail_worker.py, QThread)
      -> cleanup_all_thumbnails / regenerate_all_thumbnails (library/thumbnail_tasks.py)
```

## 关键目录与文件说明

### 1) 入口与运行目录
- `src/main.py`
  - 创建 Qt 应用并挂载 `AppWindow`。
  - 启动时调用 `showMaximized()`，避免默认小窗口启动。
- `src/sql/.gitkeep`
  - 运行数据目录占位文件。
  - 实际运行时会生成 `library.db` 与 `scan_report.json`（均已被 `.gitignore` 忽略）。

### 2) 国际化层
- `src/bookhub/i18n/language.py`
  - `LanguageManager` 负责语言切换、词典缓存、回退逻辑。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 中文文案词典，覆盖 Sidebar、Library、Settings、扫描提示等键。

### 3) 书库后端层（bookhub/library）
- `repository.py`
  - SQLite 初始化与表结构维护。
  - 维护设置项（扫描深度、哈希策略）、书库目录、书籍索引、Missed 状态、扫描历史摘要。
- `scanner.py`
  - 按目录与深度扫描文件系统。
  - 仅导入 `pdf/epub`，忽略不支持格式并记录。
  - 执行重名冲突检查（同文件名+同后缀）与默认跳过策略。
  - 命中 Missed 指纹时自动恢复书籍。
- `metadata.py`
  - PDF（PyMuPDF）与 EPUB（OPF）元数据提取。
  - 封面/首图缩略图生成，写入项目根目录 `img_preview/`。
  - **格式 WebP quality=80**（取代旧版 PNG），体积约缩减 80-90%；图片与 JSON 完全解耦，不嵌入任何 JSON。
  - `_save_thumbnail_image()` 返回 `file:// URL` 字符串，不再返回裸路径；DB 字段 `thumbnail_path` 统一存 URL。
  - 三种指纹计算：`sha256`、`size_mtime`、`quick(4MB)`。
- `models.py`
  - 扫描请求、扫描结果、冲突项、元数据/指纹结构定义。
  - 缩略图维护任务结果结构定义（清理/重建）。
- `worker.py`
  - `QThread` 扫描执行器，避免 UI 阻塞。
- `thumbnail_tasks.py`
  - 实现"清理所有缩略图（删文件+清空 DB 路径）"与"按主库记录重新生成缩略图"。
  - 清理任务同时处理旧 `.png` 与新 `.webp` 文件（向后兼容）。
  - `build_thumbnail_output_path()` 输出 `.webp` 扩展名。
- `thumbnail_worker.py`
  - 缩略图维护任务 `QThread`，提供进度与完成回调。

### 4) UI 层（bookhub/ui）
- `app_window.py`
  - 主窗口编排与事件接线中心。
  - 接管 Import 按钮目录导入、Settings 的 Add/Remove Path、扫描触发、扫描结果弹窗。
  - 页面路由包含 `library` 与 `missed`（替代旧 `trash`）。
- `viewmodels/library_viewmodel.py`
  - 管理资源集合、检索词、建议词、list/waterfall 切换。
  - 支持 `include_missing` 过滤（Library/Missed 共用）。
- `models/resource.py`
  - UI 书籍模型，扩展 `publisher/language/is_missing/file_name/extension`。
- `pages/settings_page.py`
  - General 页支持：
    - Add Path（目录选择）
    - 路径行级 Delete
    - 扫描深度（1~3）
    - Missed 匹配策略（3种）
    - 卡片间距（全局统一，Library/Collections/Favorites 共用）
    - 扫描摘要与支持格式说明
    - 缩略图维护双按钮：清理所有缩略图、重新生成缩略图
    - 任务展开区进度条（第X个/共X个）与完成状态文案
- `pages/library_page.py`
  - 一套页面逻辑支持 Library 与 Missed 两种模式。
  - 网格/列表双视图，消费真实索引数据。
- `widgets/sidebar.py`
  - 侧栏 `trash` 导航改为 `missed`。
- `widgets/book_card.py`
  - `_render_cover()` 同时支持 `file://` URL（新格式）和旧裸路径（向后兼容）。

## 当前实现边界（基于代码现状）
- 仅支持目录导入，不支持单文件导入。
- PDF 真实缩略图依赖 `PyMuPDF`；依赖缺失时会在扫描结果中报错。
- PDF 重新生成缩略图同样依赖 `PyMuPDF`；缺失时 PDF 项进入重建失败统计。
- 缩略图以 **WebP（quality=80）** 单独存放于 `img_preview/`，DB 存 `file:// URL`，图片二进制不嵌入任何 JSON。
- 元数据策略为"仅文件内 metadata，缺失置空"；手工补录后续迭代实现。
- 重名冲突当前为"扫描后汇总提示 + 默认跳过新文件"。

## 维护约定
- 任何新增/删除 `src` 文件后，必须同步更新本说明书路径图与职责段落。
- 文档描述必须强调"架构职责"，避免只罗列文件名。
- 与书库后端相关能力变更时，需同步检查：
  - `src/sql` 运行数据约定
  - `img_preview` 缩略图落盘约定（`.webp`，`file://` URL 写 DB）
  - UI 与 `library` 层接口字段一致性（`thumbnail_path` 存 `file://` URL，`BookCardWidget._render_cover` 同时支持 URL 和旧裸路径）


## 新增模块 - Collections & Favorites (2026-04-13)

### src/bookhub/ui/pages/collections_page.py
**用途**: 书单（Collections）页面
- `CollectionCard` - 书单卡片小部件，封面**优先展示书单内第一本书的真实缩略图**（同时支持 `file://` URL 和旧裸路径），无缩略图时兜底为彩色首字母；名称和书籍数量。
- `CollectionDetailPage` - 书单详情页，显示书单内的书籍（真实缩略图，同时支持 `file://` URL 和旧裸路径），支持移除书籍
- `CollectionsPage` - 主页面，网格展示所有书单，支持创建/删除/重命名，点击进入详情

### src/bookhub/ui/pages/favorites_page.py
**用途**: 收藏书籍页面（Favorites）
- `FavoritesPage` - 以单本书卡片展示收藏内容（非书单），直接消费 `favorite_books` 关联数据。
- 复用 `BookCardWidget` 呈现封面与元数据，支持双击外部打开。
- 卡片右键菜单支持「外部打开」和「从收藏中移除」。
- 切换到页面时自动 `refresh()`，与 Library 右键添加收藏保持实时一致。
- 标题右侧提供排序下拉（添加时间新到旧/旧到新），并持久化到 `app_settings.favorites_sort_order`。
- 网格布局固定为左上对齐，避免少量卡片时出现横向拉散。

### src/bookhub/ui/dialogs/add_to_collection_dialog.py
**用途**: 添加到书单的弹出对话框（旧版，保留兼容）
- `AddToCollectionDialog` - 显示现有书单列表（复选框），支持搜索和新建书单

### src/bookhub/ui/dialogs/quick_add_dialog.py ★新增
**用途**: 右键快速添加弹窗（匹配 鼠标右键的菜单.html 设计）
- `_TagChip` - 可切换选中状态的标签芯片按钮
- `_CollectionRow` - 书单列表行（单行「添加/已添加」按钮）
- `_FlowLayout` - 自定义流式布局，用于标签芯片自动换行
- `QuickAddDialog` - 主对话框：标签区（搜索/创建/选择）+ 书单区（搜索/新建/加入）+ 确认/取消
  - 确认时批量写入标签变更和书单成员变更

### src/bookhub/library/repository.py (新增方法)
**新增**: Collections & Favorites 的数据库操作
- `_init_collections_tables()` - 懒初始化三张新表：collections, collection_books, favorite_books
- `create_collection()` / `get_all_collections()` / `delete_collection()` / `rename_collection()`
- `add_book_to_collection()` / `remove_book_from_collection()` / `get_books_in_collection()`
- `get_collection_book_count()` / `is_book_in_collection()`
- `add_to_favorites()` / `remove_from_favorites()` / `get_favorite_books()` / `is_favorite()`
- `get_all_tags()` / `add_tag_to_book()` / `remove_tag_from_book()` / `get_book_tags()` ★新增

### src/bookhub/ui/pages/library_page.py (更新)
**更新**: 右键菜单改为调用 QuickAddDialog；新增封面编辑入口
- 移除旧的 Favorites 切换 / 旧 AddToCollectionDialog 入口
- 新增「添加到收藏」入口 → 写入 `favorite_books`（idempotent）
- 新增「添加标签 / 加入书单...」入口 → 打开 `QuickAddDialog`
- 新增「编辑封面...」入口 → `_edit_cover()`：文件选择 → WebP 转换 → `img_preview/` 落盘 → `file://` URL → DB 更新 → UI 刷新
- 新增 `_open_book_external()` / `_open_book_folder()` 实际执行打开文件/文件夹
- `_build_thumbnail_icon()` 同时支持 `file://` URL 和旧裸路径（向后兼容）


## 缩略图格式升级 - WebP + file:// URL (2026-04-14)

### 核心变更
- **格式**：缩略图从 PNG 升级为 WebP（quality=80），实测体积 18-35 KB/张（原 PNG 约 300-500 KB，节省约 90%）
- **存储解耦**：图片文件单独落盘于 `img_preview/`，DB `thumbnail_path` 字段存 `file://` URL，不嵌入 JSON
- **向后兼容**：`BookCardWidget._render_cover()` 同时识别 `file://` URL 和旧裸路径

### 变更文件
- `src/bookhub/library/metadata.py` - `_save_thumbnail_image()` 改为 WebP 输出 + 返回 `file://` URI
- `src/bookhub/library/thumbnail_tasks.py` - 输出扩展名改为 `.webp`；清理任务同时处理 `.png`/`.webp`
- `src/bookhub/ui/widgets/book_card.py` - `_render_cover()` 新增 `file://` URL 解析分支
- `to_be_tested_code/generate_test_thumbnails.py` ★新增 - 测试 PDF 批量生成脚本

### 测试结果（5个测试PDF）
| 文件 | 体积 |
|---|---|
| Morpho Clothing Folds and Creases | 21.2 KB |
| Morpho Hands and Feet | 18.7 KB |
| ROUGH ARCHIVE 2011-2014 | 27.5 KB |
| ROUGH ARCHIVE 2015-2018 | 34.4 KB |
| The Artists Guide to Drawing Animals | 28.3 KB |


## UI 网格一致性优化（2026-04-21）

### 核心变更
- 网格卡片标题统一为单行省略（像素级 elide），避免长标题撑高卡片导致排版不齐。
- 书籍元数据展示统一为 `author / publisher`，空值统一显示 `Unknown`，不再出现空白文本。
- 所有封面缩放由“铺满裁切”改为“完整显示优先（KeepAspectRatio）”，减少长宽比差异导致的封面截断。

### 影响文件
- `src/bookhub/ui/widgets/book_card.py`
  - 新增 `format_author_publisher_meta()`，供网格卡片和列表视图复用。
  - `BookCardWidget` 标题改为单行省略；元数据行改为 author/publisher 组合并支持 Unknown 占位。
  - `_render_cover()` 缩放策略改为 `KeepAspectRatio`。
- `src/bookhub/ui/pages/library_page.py`
  - 列表视图作者列复用 `format_author_publisher_meta()`，空值不再显示为空字符串。
  - 列表缩略图 icon 缩放改为 `KeepAspectRatio`。
- `src/bookhub/ui/pages/collections_page.py`
  - 书单封面与详情页书封缩放改为 `KeepAspectRatio`。
  - 详情卡标题由固定字符截断改为单行像素级省略。
- `src/bookhub/ui/pages/favorites_page.py`
  - 收藏页改为“单书卡片模式”（不再是书单/书单详情双层结构）。
  - 复用 `BookCardWidget` 展示卡片，并支持双击外部打开与右键移除收藏。


## 卡片外部打开交互增强（2026-04-22）

### 核心变更
- 网格卡片支持左键双击直接外部打开资源文件，沿用系统默认软件处理 PDF/EPUB。
- 列表视图右键“外部打开”由仅记录事件修复为真实执行外部打开。
- 外部打开链路增加路径存在性校验；失败时在鼠标附近显示圆角非模态轻提示。
- 网格封面占位区背景改为纯白、边框改为浅灰实线，与卡片色彩体系一致。
- Library 右键菜单去 emoji，并将新增/调整文案接入 i18n（`tr` + `zh-cn.json`）。

### 影响文件
- `src/bookhub/ui/widgets/book_card.py`
  - 新增 `open_requested` 信号与 `mouseDoubleClickEvent()`，将双击事件上抛给页面层。
- `src/bookhub/ui/pages/library_page.py`
  - 网格卡片接入双击打开回调。
  - 新增 `_open_path_external()` 统一外部打开逻辑（含校验、跨平台调用、事件记录）。
  - 新增 `_show_open_error_toast()` 实现鼠标锚点的圆角轻提示。
  - 修复列表右键“外部打开”逻辑，改为调用统一外部打开链路。
  - 右键菜单“添加标签 / 加入书单...”与“编辑封面...”改为 i18n 文案键。
- `src/bookhub/ui/resources/styles.py`
  - `#BookCover` 背景从灰底改为白底；边框从虚线改为浅灰实线。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 新增 `library.menu.quick_add`、`library.menu.edit_cover`、`library.toast.file_missing`、`library.toast.open_failed`。


## Favorites 语义修正（2026-04-22）

### 核心变更
- Favorites 页从“自定义书单页”调整为“单本书收藏页”，与侧栏语义保持一致。
- Library（网格/列表）右键菜单新增「添加到收藏」，直接写入 `favorite_books`。
- 页面切换时对支持 `refresh()` 的页面执行刷新，确保收藏变更可即时看到。

### 影响文件
- `src/bookhub/ui/pages/favorites_page.py`
  - 重构为单层收藏书籍网格页，支持双击外部打开与右键移除收藏。
- `src/bookhub/ui/pages/library_page.py`
  - 网格和列表右键菜单新增「添加到收藏」动作。
- `src/bookhub/ui/app_window.py`
  - `_show_page()` 增加页面级 `refresh()` 调度，`retranslate_ui()` 增加 Favorites 文案刷新。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 新增 `library.menu.add_to_favorites` 与 Favorites 页面相关文案键。


## Favorites 网格与排序修复（2026-04-22）

### 核心变更
- 修复 Favorites 网格在少量卡片场景下分散排列的问题，改为左上紧凑布局。
- 标题右侧新增“排序”下拉，支持按收藏添加时间正序/逆序切换。
- 排序偏好写入 `app_settings`（键：`favorites_sort_order`），重启后保持。

### 影响文件
- `src/bookhub/ui/pages/favorites_page.py`
  - 新增排序控件与排序状态管理（读取、切换、保存）。
  - 收藏数据读取改为按排序参数拉取。
  - 网格布局增加 `AlignLeft | AlignTop`，确保卡片紧凑排列。
- `src/bookhub/library/repository.py`
  - `get_favorite_books(order='desc')` 新增排序参数，按 `favorite_books.added_at` 返回。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 新增 `favorites.sort.label`、`favorites.sort.added_desc`、`favorites.sort.added_asc`。


## 卡片缩略图边缘与全局间隔统一（2026-04-22）

### 核心变更
- 移除 `BookCover` 缩略图区边框样式，消除卡片缩略图边缘黑线/深色描边视觉。
- 将卡片间隔参数统一到全局 `UI_LAYOUT.card_spacing`，Library、Collections、Favorites 统一消费。
- Settings 新增“卡片间距”选项，调整后即时生效，并持久化到 `app_settings.card_spacing`。
- AppWindow 的间隔更新逻辑改为“按页面能力分发”：
  - 当前支持 `apply_card_spacing()` 的页面立即重排；
  - 后续 Reading Now 开发只需实现同名方法即可自动接入。

### 影响文件
- `src/bookhub/ui/resources/styles.py`
  - `#BookCover` 边框改为 `none`。
- `src/bookhub/ui/resources/layout_config.py`
  - `UiLayoutConfig` 改为可变配置，新增 `normalize_card_spacing()` 与 `set_card_spacing()`。
- `src/bookhub/library/repository.py`
  - 新增 `get_card_spacing()` / `set_card_spacing()`，并在默认设置中加入 `card_spacing`。
- `src/bookhub/ui/pages/settings_page.py`
  - 新增卡片间距控件与信号 `card_spacing_changed`。
- `src/bookhub/ui/app_window.py`
  - 启动时加载间隔设置并应用；设置修改后分发到各页面重排。
- `src/bookhub/ui/pages/library_page.py`
  - 新增 `apply_card_spacing()`，网格使用动态间隔值。
- `src/bookhub/ui/pages/collections_page.py`
  - 主网格/详情网格统一使用动态间隔；新增 `apply_card_spacing()`。
- `src/bookhub/ui/pages/favorites_page.py`
  - 网格改为动态间隔，新增 `apply_card_spacing()`。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 新增 `settings.card_spacing`。


## 重名冲突提示交互改造（2026-04-23）

### 核心变更
- 扫描完成后的“重名冲突”反馈由阻塞式 `QMessageBox` 改为右下角非模态滑入提醒（Toast）。
- 提醒框自带秒级倒计时，倒计时结束后自动滑出窗口并关闭。
- 提醒文案保留冲突总数与示例文件名，避免长文本遮挡主流程。

### 影响文件
- `src/bookhub/ui/widgets/slide_toast.py` ★新增
  - 新增 `SlideToast` 组件，提供右下角定位、滑入/滑出动画、倒计时自动关闭能力。
- `src/bookhub/ui/app_window.py`
  - `_show_name_conflicts()` 改为调用 `SlideToast.show_toast()`，不再弹阻塞式告警框。
  - 新增 `resizeEvent()`，窗口尺寸变化时重定位右下角提醒。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 新增冲突提醒倒计时与示例文案键：`scan.conflict.toast_*`。


## Collections 详情网格与总书单卡片复用修复（2026-04-24）

### 核心变更
- 修复 Collections 详情页书籍网格与总书单（Library/Favorites）卡片样式不一致问题。
- `CollectionDetailPage` 不再维护独立 `DetailBookCard`，改为直接复用 `BookCardWidget`。
- 书单详情页新增“记录 -> ResourceItem”转换，统一字段来源与渲染路径。
- 保留“从书单移除”右键动作；双击卡片支持外部打开文件。

### 影响文件
- `src/bookhub/ui/pages/collections_page.py`
  - 移除手写详情卡片构造逻辑，统一为 `BookCardWidget`。
  - 新增 `_parse_tags()` 与 `_record_to_resource()`，对齐 Library/Favorites 的模型结构。
  - 新增 `_open_external()`，详情页行为与其他书籍卡片页一致。


## 顶部搜索浮层与搜索结果网格紧凑修复（2026-04-24）

### 核心变更
- 修复关键词搜索后少量结果网格横向拉散问题，统一为左上紧凑排列。
- 搜索建议下拉从 TopBar 内嵌布局改为 `Qt.Popup` 浮层，不再挤压下方书籍展示区。
- 浮层宽度采用整行宽度，定位到 TopBar 下边缘，并在窗口缩放/切页时重定位。

### 影响文件
- `src/bookhub/ui/pages/library_page.py`
  - 网格布局增加 `AlignLeft | AlignTop`。
  - 增加尾列 `setColumnStretch()` 吸收剩余空白，保证卡片紧凑罗列。
- `src/bookhub/ui/widgets/topbar.py`
  - 搜索建议容器改为 `Qt.Popup` 独立浮层。
  - 新增浮层定位与重定位方法，打开时按整行宽度计算几何。
- `src/bookhub/ui/app_window.py`
  - 在页面切换与窗口缩放时调用 TopBar 浮层重定位。


## 搜索首字符输入失焦修复（2026-04-24）

### 核心变更
- 修复搜索框输入首字符时因浮层打开抢焦点导致的失焦问题。
- 搜索浮层改为非激活工具窗（`Qt.Tool` + `WA_ShowWithoutActivating`），并将建议项设为不抢焦点。
- 每次展开建议浮层后将输入焦点归还给 `TopSearchInput`，保障连续输入。

### 影响文件
- `src/bookhub/ui/widgets/topbar.py`
  - 浮层窗口标志由 `Qt.Popup` 调整为 `Qt.Tool`。
  - 增加 `WA_ShowWithoutActivating` 与 `NoFocus` 配置。
  - `_open_dropdown()` 末尾显式执行 `search_input.setFocus(...)`。


## 搜索刷新链路解耦与层级稳定化（2026-04-24）

### 核心变更
- 将搜索输入链路拆分为“建议即时刷新”与“书单延迟提交刷新（150ms）”，避免每键同步重绘书单。
- 增加查询去重（`last_committed_query`），相同查询不重复触发页面渲染。
- 下拉建议列表新增差异判断，内容未变化时不重建项，减少闪烁。
- 书单渲染后统一执行一次 `singleShot(0)` 的下拉层级校正（`reposition + raise`），消除短暂层级颠倒。

### 影响文件
- `src/bookhub/ui/viewmodels/library_viewmodel.py`
  - 新增建议纯计算入口 `search_suggestions_for_query()`。
  - `set_query()` 仅更新过滤条件，不再耦合建议重建。
- `src/bookhub/ui/app_window.py`
  - 新增 150ms 搜索渲染节流定时器与 `_commit_search_query()`。
  - 输入阶段仅刷新建议；提交阶段才渲染当前 `Library/Missed` 页面。
  - 新增 `_stabilize_dropdown_layer()` 在重排后保持下拉置顶。
- `src/bookhub/ui/widgets/topbar.py`
  - `set_search_suggestions()` 增加列表差异判断。
  - 新增 `ensure_dropdown_on_top()` 供外部强制校正下拉层级。


## 搜索下拉常驻容器与单次更新优化（2026-04-24）

### 核心变更
- 修复搜索输入过程中下拉“像关闭再打开”的视觉闪动问题。
- 去除键程内重复重建：`_open_dropdown()` 仅负责显示/定位，不再执行内容渲染。
- 下拉内容改为行复用池（`_SuggestionRow`），更新时只改文本/绑定，超出行直接隐藏。
- 批量更新期间关闭重绘（`setUpdatesEnabled(False/True)`），减少中间帧抖动。

### 影响文件
- `src/bookhub/ui/widgets/topbar.py`
  - 新增 `_SuggestionRow` 复用行组件与 `_row_pool`。
  - 新增 `_ensure_row_capacity()`，按需扩容，不再全量销毁重建。
  - `set_search_suggestions()` 在建议未变化时仅做层级校正。
  - `_open_dropdown()` 改为只执行显示与焦点保持。


## Library 主区压缩 + 右侧常驻详情栏（2026-04-25）

### 核心变更
- Library 页面主内容从单栏改为 `QSplitter` 双栏：左侧为书籍展示区，右侧为常驻详情栏（可拖拽调宽）。
- 左侧侧边栏导航保持不变，仅压缩中间书籍展示区域以给右栏留出空间。
- 网格卡片新增 `cover_only` 模式：仅展示封面；元数据不再在网格卡片中显示。
- 网格展示区背景统一为浅灰；卡片底部条默认浅灰，选中态改为更深灰。
- 单击与双击采用 `500ms` 判定窗口：
  - 单击：延迟提交选中，更新右侧详情栏；
  - 双击：取消待提交单击，继续执行外部打开。
- 右侧详情栏常驻显示放大封面与元数据（标题、作者、出版社、状态、标签、文件路径）以及所属自定义书单列表。

### 影响文件
- `src/bookhub/ui/pages/library_page.py`
  - 新增 `BookDetailPanel` 常驻详情组件与 `QSplitter` 主布局。
  - 新增选中态管理、500ms 单/双击判定、grid/list 统一详情更新链路。
  - 网格改为 `BookCardWidget(..., cover_only=True)`，并维护卡片选中态同步。
- `src/bookhub/ui/widgets/book_card.py`
  - 新增 `clicked` 信号、`cover_only` 参数与 `set_selected()` 选中态 API。
  - 保留 `open_requested` 双击外部打开信号，保证原交互链路兼容。
- `src/bookhub/library/repository.py`
  - 新增 `get_collections_for_book(book_id)`，用于详情栏读取书籍所属自定义书单。
- `src/bookhub/ui/resources/styles.py`
  - 新增 Library 双栏布局、详情栏、cover-only 卡片与选中底部条样式。
- `src/bookhub/i18n/locales/zh-cn.json`
  - 新增详情栏空态与字段文案键。

### 细节修复（2026-04-25）
- 修复 Grid 在拖拽右侧详情栏宽度后“列数不及时更新导致右侧死空隙”的问题。
- Grid 纯封面卡片进一步精简：移除底部额外条层，仅保留背景层与封面。
- 右侧详情栏封面改为水平居中显示。

### 额外影响文件
- `src/bookhub/ui/pages/library_page.py`
  - 监听 `QSplitter.splitterMoved`，拖拽时即时重算列数并重排网格。
  - 详情封面挂载对齐从左对齐改为水平居中。
  - 移除网格末尾 `columnStretch` 填充策略，避免形成固定大块空白。
- `src/bookhub/ui/widgets/book_card.py`
  - `cover_only` 模式移除底部条控件，卡片仅包含封面区域。
- `src/bookhub/ui/resources/styles.py`
  - 删除 `BookCardFooter` 样式，`cover_only` 选中态改为卡片背景/边框反馈。
