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
**用途**: 自定义书单（自定义书单）页面 —— 重构自原 Favorites 收藏夹
- `_load_thumbnail()` / `_fallback_cover()` - 缩略图辅助函数（真实封面 + 首字母兜底）；`_load_thumbnail()` 同时支持 `file://` URL（2026-04-14 新格式）和旧裸路径（向后兼容）
- `ReadingListCard` - 自定义书单卡片，封面优先展示书单内第一本书的真实缩略图
- `ReadingListDetailPage` - 书单详情页，书籍卡片显示真实缩略图，支持移除
- `FavoritesPage` - "自定义书单"主页面，与 Collections 并列，功能完全一致

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
- 新增「🏷️ 添加标签 / 加入书单…」入口 → 打开 `QuickAddDialog`
- 新增「🖼️ 编辑封面…」入口 → `_edit_cover()`：文件选择 → WebP 转换 → `img_preview/` 落盘 → `file://` URL → DB 更新 → UI 刷新
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
