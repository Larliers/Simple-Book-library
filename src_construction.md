# src 结构说明书（精简且完整）

更新时间：2026-06-12

## 1. 文档目标
- 保留字符串式文件路径结构。
- 给出每个代码组件（文件）的一句话用途。
- 作为 `src/` 结构与职责的当前事实文档。

## 2. 字符串式文件路径结构
```text
src/
├─ main.py
├─ tests/
│  ├─ test_comic_preview_pipeline.py
│  ├─ test_comic_page_cache.py
│  ├─ test_rule_engine.py
│  ├─ test_rule_preview.py
│  ├─ test_text_rule_structure_parser.py
│  ├─ test_text_rule_dialog.py
│  └─ test_scan_pdf_degrade.py
├─ sql/
│  └─ .gitkeep
├─ assets/
│  ├─ app_icon_bookcase.ico
│  ├─ app_icon_bookcase.svg
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
   │  ├─ preview_paths.py
   │  ├─ text_rules/
   │  │  ├─ __init__.py
   │  │  ├─ rule_engine.py
   │  │  ├─ rule_examples.py
   │  │  ├─ rule_models.py
   │  │  ├─ rule_preview.py
   │  │  ├─ source_resolver.py
   │  │  ├─ structure_parser.py
   │  │  └─ step_handlers.py
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
       │  ├─ quick_add_dialog.py
       │  ├─ text_rule_dialog.py
       │  ├─ text_rule_help_dialog.py
       │  └─ text_rule_regex_dialog.py
      ├─ models/
      │  ├─ __init__.py
      │  └─ resource.py
      ├─ pages/
      │  ├─ __init__.py
      │  ├─ comic_page.py
      │  ├─ collections_page.py
      │  ├─ favorites_page.py
      │  ├─ library_page.py
      │  ├─ settings_page.py
      │  └─ text_novel_page.py
      ├─ resources/
      │  ├─ __init__.py
      │  ├─ assets.py
      │  ├─ font_runtime.py
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
- `src/main.py`：应用入口；设置应用图标，创建 Qt 应用并启动主窗口。
- `src/tests/test_rule_engine.py`：Text 规则引擎回归测试（步骤提取、行范围 warning、回退链、非法正则容错）。
- `src/tests/test_rule_preview.py`：Text 规则预览回归测试（自动样本、规则链回退、非法正则失败、空目录无样本）。
- `src/tests/test_text_rule_dialog.py`：Text 规则弹窗 smoke 测试（旧 JSON 加载、字段切换、上下文参数、预览状态、格式诊断、帮助文档布局）。
- `src/tests/test_text_rule_structure_parser.py`：Text 规则结构解析测试（嵌套括号、括号外分隔符、样本格式分组）。
- `src/tests/test_scan_pdf_degrade.py`：PDF 后端降级容错回归测试（PyMuPDF 不可用时的聚合 warning 与入库行为）。
- `src/tests/test_comic_preview_pipeline.py`：漫画快扫占位与后台并行补图回归测试（占位复制、压缩替换、原图删除、超大图降采样、排序顺序）。
- `src/tests/test_comic_page_cache.py`：漫画页缓存回归测试（数据缓存命中、卡片复用与收藏联动失效）。
- `src/sql/.gitkeep`：运行数据目录占位，实际运行时生成 `library.db`、`scan_report.json`。

### 3.2 bookhub 包根
- `src/bookhub/__init__.py`：包标记与顶层命名空间。

### 3.3 国际化组件（bookhub/i18n）
- `src/bookhub/i18n/__init__.py`：国际化导出入口。
- `src/bookhub/i18n/language.py`：语言切换、词典加载、回退策略。
- `src/bookhub/i18n/locales/zh-cn.json`：中文文案键值表。

### 3.4 书库后端组件（bookhub/library）
- `src/bookhub/library/__init__.py`：后端模块导出入口。
- `src/bookhub/library/repository.py`：SQLite 读写中心；设置、书籍、书单、收藏、标签操作；漫画排序与显示模式、Text 规则预览结果区高度/用户预设等 UI 偏好持久化。
- `src/bookhub/library/scanner.py`：目录扫描与文件过滤；构建入库候选（PDF/EPUB、Comic、Text Novel）；Text 规则 author 入库前清理 Unknown/unkown 等占位作者，tag 结果按换行拆分为多标签；漫画目录快照判定、`folder_modified_at` 写入与超大封面降采样占位。
- `src/bookhub/library/preview_paths.py`：预览图目录结构与路径构建服务（`resource_type + variant`）。
- `src/bookhub/library/metadata.py`：元数据提取与缩略图生成（WebP，`file://` 路径）。
- `src/bookhub/library/models.py`：扫描/任务的数据结构定义。
- `src/bookhub/library/text_rules/rule_models.py`：Text Novel 规则模型（`ImportRule`/`RuleStep`/`RuleContext`/`RuleResult`，含预览 warning 字段）。
- `src/bookhub/library/text_rules/rule_engine.py`：规则执行器与规则链回退（`apply_rule`、`apply_rule_chain`），透传步骤 warning。
- `src/bookhub/library/text_rules/source_resolver.py`：规则 source 解析（`filename`/`stem`/`txt_first_line`/`txt_head_text` 等）。
- `src/bookhub/library/text_rules/structure_parser.py`：Text 规则结构解析；支持嵌套括号块解析、括号范围过滤、括号外分隔符结构签名与多样本格式诊断分组。
- `src/bookhub/library/text_rules/step_handlers.py`：规则步骤处理（文本清洗、文本删除、split、多分隔符取段、分隔范围拼接、单行/范围行提取、删除前/后 N 行、分界线截取、按行循环提取、嵌套感知括号提取/删除、regex_extract 等）。
- `src/bookhub/library/text_rules/rule_preview.py`：Text 规则预览辅助；查找首个 TXT 样本、读取首行/开头文本并复用规则链执行预览。
- `src/bookhub/library/text_rules/rule_examples.py`：默认规则链示例。
- `src/bookhub/library/worker.py`：扫描任务线程包装；汇总多 scope 统计与 warning。
- `src/bookhub/library/thumbnail_tasks.py`：缩略图清理与重建任务实现。
- `src/bookhub/library/thumbnail_worker.py`：缩略图任务线程包装。
- `src/bookhub/library/error_logs.py`：扫描/冲突日志读写；日志目录固定解析为项目根下 `src/Scan_error_logs`（避免相对路径导致 `src/src/Scan_error_logs`）。

### 3.5 UI 主组件（bookhub/ui）
- `src/bookhub/ui/__init__.py`：UI 包导出入口。
- `src/bookhub/ui/app_window.py`：主窗口装配；连接 sidebar、topbar、pages 与后端任务；按当前页面将顶部搜索路由到 Library 或 Text Novel 资源集。

### 3.6 对话框组件（bookhub/ui/dialogs）
- `src/bookhub/ui/dialogs/__init__.py`：对话框包入口。
- `src/bookhub/ui/dialogs/import_dialog.py`：导入相关对话框逻辑。
- `src/bookhub/ui/dialogs/add_tag_dialog.py`：添加标签对话框。
- `src/bookhub/ui/dialogs/add_to_collection_dialog.py`：旧版加入书单对话框（兼容保留）。
- `src/bookhub/ui/dialogs/quick_add_dialog.py`：快速添加标签/加入书单弹窗。
- `src/bookhub/ui/dialogs/text_rule_dialog.py`：Text Novel 规则步骤编辑对话框；左侧字段 Tab/规则链，中列按类别筛选的卡片式步骤编辑（含嵌套括号与分隔处理步骤）与用户预设导入/保存，右侧常驻 TXT 样本预览和文件名格式诊断（项目样式滚动结果区，可拖拽并记忆高度）；右上角提供常用正则与使用文档入口。
- `src/bookhub/ui/dialogs/text_rule_help_dialog.py`：Text Rules 内置使用文档窗口；说明 source、步骤、分隔提取、嵌套括号、格式诊断和常见排错。
- `src/bookhub/ui/dialogs/text_rule_regex_dialog.py`：Text Rules 常用正则示范窗口；按用途、示例文本、正则、提取结果展示，覆盖日期、tag、分隔/混合分隔文件名、Pixiv id 等示例。

### 3.7 UI 数据模型（bookhub/ui/models）
- `src/bookhub/ui/models/__init__.py`：模型包入口。
- `src/bookhub/ui/models/resource.py`：UI 层 `ResourceItem` 资源模型。

### 3.8 页面组件（bookhub/ui/pages）
- `src/bookhub/ui/pages/__init__.py`：页面包入口。
- `src/bookhub/ui/pages/comic_page.py`：Comic/Comic Fav 页面；支持文件夹日期/名称排序与显示模式二选一（瀑布流/分页）；封面双击外部打开；右键添加/移除收藏；网格封面采用无壳层 cover-only 卡片并共享全局选中边框设置。
- `src/bookhub/ui/pages/library_page.py`：Library 页面；grid/list；右侧详情栏；单/双击交互；网格区域移除 `+ ADD NEW BOOK` 末尾方块入口，仅保留封面直陈列。
- `src/bookhub/ui/pages/collections_page.py`：书单页与书单详情页；详情支持 grid/list 视图与侧键返回上一级。
- `src/bookhub/ui/pages/favorites_page.py`：收藏页；支持 grid/list 视图与排序持久化；封面网格与 Library/Comic 共享无壳层 cover-only 卡片表现。
- `src/bookhub/ui/pages/settings_page.py`：设置页（扫描、匹配策略、卡片间距、封面选中边框粗细/颜色、缩略图任务、错误日志、Text Novel）；导航仅保留 General 与 Error logs；Text Novel 路径行支持“Delete + Rules + Path”布局；支持 Text 预览长度与漫画显示模式（瀑布流/分页）及分页容量配置；扫描/缩略图任务按 Library/Comic/Text 分类型入口。
- `src/bookhub/ui/pages/text_novel_page.py`：Text Novel 页面；固定列表视图；接收 AppWindow 按文本小说标题/作者/tag/路径过滤后的资源；右侧详情栏展示 TXT 预览文本；双击外部打开。

### 3.9 UI 资源组件（bookhub/ui/resources）
- `src/bookhub/ui/resources/__init__.py`：资源包入口。
- `src/assets/app_icon_bookcase.svg`：书柜主题应用图标源文件。
- `src/assets/app_icon_bookcase.ico`：Nuitka/Windows exe 使用的应用图标。
- `src/bookhub/ui/resources/assets.py`：图标/资源加载，支持 icons 子目录与顶层资产图标。
- `src/bookhub/ui/resources/font_runtime.py`：运行时字体服务；扫描并注册 `src/fonts` 字体文件、解析有效字体与回退策略。
- `src/bookhub/ui/resources/layout_config.py`：布局尺寸与间距配置；包含 cover-only 选中边框宽度/颜色的归一化与运行时状态。
- `src/bookhub/ui/resources/styles.py`：全局 QSS 样式；支持基于选中字体动态构建 `font-family` 栈，并支持注入 cover-only 选中边框动态样式参数。

### 3.10 视图模型组件（bookhub/ui/viewmodels）
- `src/bookhub/ui/viewmodels/__init__.py`：视图模型包入口。
- `src/bookhub/ui/viewmodels/library_viewmodel.py`：Library/Text 资源查询过滤、字段前缀搜索（`title:`/`author:`/`tag:`）、视图模式、搜索建议状态。

### 3.11 小部件组件（bookhub/ui/widgets）
- `src/bookhub/ui/widgets/__init__.py`：小部件包入口。
- `src/bookhub/ui/widgets/sidebar.py`：左侧导航栏组件。
- `src/bookhub/ui/widgets/topbar.py`：顶部搜索栏与建议浮层；支持按页面切换搜索占位文案。
- `src/bookhub/ui/widgets/book_card.py`：书籍卡片组件（常规卡片、cover-only 卡片）；统一格式化作者/出版社元信息并隐藏缺失出版社的 Unknown 占位；cover-only 分支使用零内边距封面直陈列（无常驻外壳）。
- `src/bookhub/ui/widgets/slide_toast.py`：右下角滑入提示组件。

## 4. 当前关键实现（简要）
- 运行依赖：`requirements.txt` 采用固定版本策略；在 Python 3.10.6 环境锁定 `PySide6==6.6.1` 以规避 `libshiboken/signature` 初始化崩溃。
- 打包准备：新增书柜主题应用图标，`scripts/build_nuitka.ps1` 使用 `Nuitka==4.1.2` 构建 exe，并显式打包 `src/assets`、i18n locales、`fitz` 与 `pymupdf` 原始包目录；PyMuPDF 采用预编译 `.pyd/.dll` 随包携带并关闭 Nuitka excluded-module 运行时阻断；`scripts/`、`src/tests/`、运行数据库、扫描日志、缩略图缓存不进入发行包。
- 2026-05-29 外部工具链注释：本次仅完成 Hue 离线落地与本地 MCP 集成（`F:\Coding_Dev\UI\hue*`、全局 `mcp.json`），`src/` 代码与目录结构未发生变更。
- 2026-05-30 外部工具链注释：Hue MCP 相关目录已统一迁移到 `F:\MCP\hue-mcp-server` 与 `F:\MCP\hue`；本次仍不涉及 `src/` 代码变更。
- 2026-06-11 UI 范本注释：新增 `Simple-Book-library-Dev_Document\UI\新UI\glassmorphism-ui.html` 作为 Glassmorphism 交互画板；设置、弹窗、组件状态已拆到底部独立预览区，便于后续拖拽/缩放窗口设计；页面内新增中文/英文 i18n 浮动预览按钮，且注释标明不进入后续正式开发；左侧侧栏删除“导入书籍”入口；Library 总页面主区采用 cover-only 封面网格，标题/作者/tag 等信息交由右侧详情栏承载；范本新增日间/夜间主题变量、按本地时间 `22:00-07:00` 自动切换的夜间模式设置区、检查频率与自动过渡时长预览控件；手动 Day/Night/Auto 预览使用快速切换，避免分钟级过渡造成白天样式灰化残留；本次不涉及 `src/` 代码与目录结构变更。
- 缩略图：WebP 落盘，DB 保存 `file://` URL。
- 数据能力：Collections、Favorites、Tags 已接入。
- Library 展示：主区双栏，右侧详情栏常驻且可拖拽宽度。
- Favorites/CollectionDetail 展示：支持与 Library 一致的 grid/list 切换；主区接入右侧详情栏；详情页主区布局采用与 Library 相同的伸展策略，避免分栏贴底；grid 卡片采用 cover-only 样式并支持选中态；模式持久化到 `app_settings`。
- 封面网格视觉：Library、Comic、Comic Fav、Favorites、CollectionDetail 统一使用“背景 + 封面直陈列”无壳层样式；仅在选中时显示可配置边框（全局设置）。
- Settings 导航：仅保留 General 与 Error logs 两项；移除顶部搜索框、Shortcuts、Manage Metadata 占位区域。
- Text Novel：新增独立侧栏入口与独立列表页；TXT 不进入 Library 主列表；右侧详情栏可展示 `info_text` 预览。
- 详情面板语义统一：`info_text` 仅作为“文本预览”渲染一次；“所属书单”仅在 `book` 资源类型显示，Comic/Text Novel 不再复用该字段。
- Text 规则：规则弹窗新增“使用文档”入口、三步引导区、一键模板（标题/作者/兜底）与当前字段规则链预览；source 与 step type 显示文案与内部 code 分离（`userData` 持久化 code），在不改 JSON 协议前提下增强可读性。
- Text 规则 i18n：补齐规则弹窗内参数字段名、source/step 文案、规则/步骤列表格式与帮助文档文案键，减少硬编码英文暴露。
- i18n 治理基线：新增 `scripts/i18n_hardcoded_scan.py`，用于扫描 UI 常见硬编码文案候选并输出清单（仅报告，不阻断）。
- 扫描容错：当 PyMuPDF（`fitz`）不可用时，PDF 扫描自动降级为“仅入库+标题兜底”，跳过元数据/缩略图并输出单条聚合 warning，避免错误风暴弹窗。
- 缺失记录治理：扫描按 scope 检查已入库源路径；缺失项写入 `src/Scan_error_logs` 后硬删除，不再进入 Missed 体系；重名冲突遇到陈旧路径会先清理再导入。
- 任务触发：启动扫描支持配置开关（默认关闭）；路径变更自动扫描支持独立开关（默认开启）。
- 缩略图任务：Library 与 Comic 分 scope 清理/重建；结果摘要包含 `scope + task_kind + total/succeeded/skipped/failed`。
- Reading Now 与 Tools 占位页已下线：主窗口不再注册对应页面，侧栏仅保留可用功能入口；底层 `status` 字段与数据结构保持不变。
- TopBar：移除右侧 IMPORT/NEW LIST/刷新/菜单占位区，搜索栏填充顶部可用宽度。
- TopBar：搜索框支持最小高度与字号放大；搜索输入与建议下拉字号可在 Settings 调节并持久化（默认 15px）。
- 本地启动：根目录可放置被 `.gitignore` 忽略的 `启动 简易图书馆.lnk`，双击后通过 `.venv\Scripts\pythonw.exe` 启动 `src\main.py`。
- 网格布局：Library/Favorites/CollectionDetail 的书籍网格统一左内边距 12px，避免左侧贴边溢出观感。
- 交互规则：单击看详情（无门控延迟）、双击外部打开。
- 字体重载：`Reload Fonts` 现在执行完整链路（重扫 `src/fonts` -> 注册字体 -> 解析回退 -> `QApplication.setFont` + 动态 QSS 立即生效 -> 持久化设置）；目录不存在时自动创建并通过右下角 Toast 提示。
- 漫画性能：扫描阶段改为“快扫入库+可选首图占位复制”，压缩缩略图改为后台并行补全；预览图目录升级为 `img_preview/<resource_type>/<original|compressed>`。
- 漫画性能（本轮）：Comic/Comic Fav 页显示模式改为 Settings 全局二选一（瀑布流/分页），分页容量可配（24/48/72/96）；扫描侧排序字段改为 `folder_modified_at`（目录 mtime）并保留 `folder_size_mtime` 仅作增量判定；超大封面占位自动降采样以规避 Qt 256MB 解码限制。
- 页面渲染性能（本轮）：Comic/Comic Fav 增加“事件驱动失效 + 双层缓存（数据索引缓存 + 卡片复用缓存）”；Library/Favorites/Collections 网格改为“布局重排优先复用卡片、按需重建单卡”，减少切页和重排时的全量 widget 销毁与封面重复解码。

## 5. 边界与约束
- 当前导入粒度：目录导入（不支持单文件导入）。
- 当前支持格式：Library 支持 PDF/EPUB，Comic 支持目录封面提取，Text Novel 支持 TXT（含预览与规则导入）。
- 外部打开：依赖系统默认关联程序。

## 6. 维护要求
- 每次 `src/` 结构变化后，必须更新本文件。
- 每次开发后，必须在 `Agent-rule/logs/history/YYYY-MM-DD.md` 追加留档。
- 文档保持“当前事实”，历史细节放 `logs/history`，不在本文件堆叠。
