# src 结构说明书（精简且完整）

更新时间：2026-07-18

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
│  ├─ test_scan_pdf_degrade.py
│  ├─ test_library_scan_incremental.py
│  ├─ test_scan_summary_fields.py
│  ├─ test_text_encoding.py
│  ├─ test_missed_cleanup.py
│  └─ test_text_scan_tags.py
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
   │  ├─ text_encoding.py
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
      ├─ web_window.py
      ├─ web_bridge.py
      ├─ web_scheme.py
      ├─ web/
      │  ├─ index.html
      │  ├─ css/
      │  │  └─ app.css
      │  └─ js/
      │     ├─ app.js
      │     ├─ text_rules.js
      │     └─ qwebchannel.js
      ├─ models/
      │  ├─ __init__.py
      │  └─ resource.py
      ├─ resources/
      │  ├─ __init__.py
      │  ├─ assets.py
      │  ├─ font_runtime.py
      │  ├─ layout_config.py
      │  └─ styles.py
      └─ viewmodels/
         ├─ __init__.py
         └─ library_viewmodel.py
```

## 3. 每个代码组件的用处介绍

### 3.1 入口与运行目录
- `src/main.py`：应用入口；在创建 `QApplication` 前设置 `AA_ShareOpenGLContexts` 并注册 `app://` 自定义 scheme，随后创建 Qt 应用并启动 WebEngine 主窗口 `WebAppWindow`（`--check-pymupdf` 自检分支保留）。
- `src/tests/test_rule_engine.py`：Text 规则引擎回归测试（步骤提取、行范围 warning、回退链、非法正则容错）。
- `src/tests/test_rule_preview.py`：Text 规则预览回归测试（自动样本、规则链回退、非法正则失败、空目录无样本）。
- `src/tests/test_text_rule_structure_parser.py`：Text 规则结构解析测试（嵌套括号、括号外分隔符、样本格式分组）。
- `src/tests/test_scan_pdf_degrade.py`：PDF 后端降级容错回归测试（PyMuPDF 不可用时的聚合 warning 与入库行为）。
- `src/tests/test_library_scan_incremental.py`：Library 增量扫描与 `hash_strategy` 分级指纹（未变跳过、touch 强制更新、缺缩略图重处理、COALESCE 保留指纹）。
- `src/tests/test_scan_summary_fields.py`：扫描摘要字段对齐回归（comic 计入新增、别名键、冲突 `incoming_path`）。
- `src/tests/test_text_encoding.py`：TXT 编码探测回归（GBK/GB18030、UTF-8 BOM、简/繁偏好、低置信双候选、规则预览 `detectedEncoding`）。
- `src/tests/test_missed_cleanup.py`：启动时清理遗留 `is_missing=1` 行；确认无 Missed 恢复 API。
- `src/tests/test_comic_preview_pipeline.py`：漫画快扫占位与后台并行补图回归测试（占位复制、压缩替换、原图删除、超大图降采样、排序顺序、GIF/BMP/TIFF 入库与 GIF 首帧封面）。
- `src/tests/test_cover_grid_settings.py`：封面选中边框归一化与 Repository 偏好持久化（含 Text 规则预览高度/窗口尺寸/预设）；已不再依赖旧 Widgets 页。
- `src/tests/test_web_bridge_smoke.py`：Web Bridge / scheme / Text Rules CRUD 冒烟。
- `src/sql/.gitkeep`：运行数据目录占位，实际运行时生成 `library.db`、`scan_report.json`。

### 3.2 bookhub 包根
- `src/bookhub/__init__.py`：包标记与顶层命名空间。

### 3.3 国际化组件（bookhub/i18n）
- `src/bookhub/i18n/__init__.py`：国际化导出入口。
- `src/bookhub/i18n/language.py`：语言切换、词典加载、回退策略。
- `src/bookhub/i18n/locales/zh-cn.json`：中文文案键值表；设置导航将路径与扫描合并命名，并提供 Fast 指纹漏检风险提示。

### 3.4 书库后端组件（bookhub/library）
- `src/bookhub/library/__init__.py`：后端模块导出入口。
- `src/bookhub/library/repository.py`：SQLite 读写中心；设置、书籍、书单、收藏、标签操作；`hash_strategy` 新装与非法值回退均默认 `quick`；`map_library_books_for_scan` / `map_text_novels_for_scan` 提供 Library/Text 增量扫描用的 path→指纹索引；`upsert_book` 对空指纹列 COALESCE 保留旧值；漫画同名冲突查询与设置 `comic_title_conflict_policy`（默认 `skip_incoming`）；`get/set_text_encoding_preference`（`simplified|traditional|auto`，默认 `simplified`）；漫画排序与显示模式、Text 规则预览结果区高度、规则窗口尺寸、用户预设等 UI 偏好持久化。
- `src/bookhub/library/scanner.py`：目录扫描与文件过滤；构建入库候选（PDF/EPUB、Comic、Text Novel）；Library/Text 均按 Settings `hash_strategy` 比对已存指纹并计入 `skipped_unchanged_count`（Library 另要求缩略图仍在；Text 无 thumb 要求即跳过规则链）；漫画 upsert 前按 `comic_title_conflict_policy` 处理同 `comic_root` 同标题冲突；TXT/漫画旁注经 `text_encoding` 按 `encoding_preference` 探测后读入；扫描函数支持可选进度回调并输出当前路径与统计快照；Text 规则 author 入库前清理 Unknown/unkown 等占位作者，tag 结果按换行拆分为多标签；漫画目录快照判定、`folder_modified_at` 写入与超大封面降采样占位。
- `src/bookhub/library/text_encoding.py`：TXT 统一读入；`DecodeResult` / `detect_and_decode`；UTF-8 优先，64KB 样本经 charset-normalizer 按 `text_encoding_preference`（简/繁/自动）排名；简体永不选 Big5，繁体优先 Big5；低置信时 GB18030↔UTF-8 双候选回退。
- `src/bookhub/library/preview_paths.py`：预览图目录结构与路径构建服务（`resource_type + variant`）。
- `src/bookhub/library/metadata.py`：元数据提取与缩略图生成（WebP，`file://` 路径）；`compute_fingerprints` 按策略分级读盘（`size_mtime` 仅 stat、`quick` 前 4MB、`sha256` 整文件）。
- `src/bookhub/library/models.py`：扫描/任务的数据结构定义（含 `skipped_unchanged_count`；`TextScanRequest.hash_strategy` 默认 `quick`，并携带 `encoding_preference`；`ComicScanRequest.title_conflict_policy` / `encoding_preference`；`to_summary` 同时输出前端历史别名键）；`COMIC_IMAGE_EXTENSIONS` 含 jpg/png/webp/gif/bmp/tif/tiff。
- `src/bookhub/library/media_sanitizer.py`：封面图消毒；GIF/多帧图 `seek(0)` 后转 RGB PNG。
- `src/bookhub/library/text_rules/rule_models.py`：Text Novel 规则模型（`ImportRule`/`RuleStep`/`RuleContext`/`RuleResult`，含预览 warning 字段）。
- `src/bookhub/library/text_rules/rule_engine.py`：规则执行器与规则链回退（`apply_rule`、`apply_rule_chain`），透传步骤 warning。
- `src/bookhub/library/text_rules/source_resolver.py`：规则 source 解析（`filename`/`stem`/`txt_first_line`/`txt_head_text` 等）。
- `src/bookhub/library/text_rules/structure_parser.py`：Text 规则结构解析；支持嵌套括号块解析、括号范围过滤、括号外分隔符结构签名与多样本格式诊断分组。
- `src/bookhub/library/text_rules/step_handlers.py`：规则步骤处理（文本清洗、文本删除、split、多分隔符取段、分隔范围拼接、单行/范围行提取、删除前/后 N 行、分界线截取、按行循环提取、嵌套感知括号提取/删除、regex_extract 等）。
- `src/bookhub/library/text_rules/rule_preview.py`：Text 规则预览辅助；查找首个 TXT 样本、经 `text_encoding`（按偏好）读取首行/开头文本并复用规则链执行预览；样本载荷含 `detected_encoding` / `encoding_confidence`。
- `src/bookhub/library/text_rules/rule_examples.py`：默认规则链示例。
- `src/bookhub/library/text_rules/rule_catalog.py`：Text Rules Web 元数据目录（fields/sources/step 分类与参数表单、内置模板、常用正则、帮助章节）；`describe_step_catalog()` 供 Bridge 下发。
- `src/bookhub/library/worker.py`：扫描任务线程包装；透传 Library/Comic/Text 扫描进度信号；将 Settings `hash_strategy` 传入 Text/Library 请求（非法策略回退 `quick`）、将 `comic_title_conflict_policy` 与 `text_encoding_preference` 传入 Comic/Text 请求；汇总多 scope 统计与 warning。
- `src/bookhub/library/thumbnail_tasks.py`：缩略图清理与重建任务实现；漫画 `cover_fingerprint` 以 `manual:` 开头时跳过 regenerate，保留用户手选封面。
- `src/bookhub/library/thumbnail_worker.py`：缩略图任务线程包装。
- `src/bookhub/library/error_logs.py`：扫描/冲突日志读写；日志目录固定解析为项目根下 `src/Scan_error_logs`（避免相对路径导致 `src/src/Scan_error_logs`）。

### 3.5 UI 主组件（bookhub/ui）
- `src/bookhub/ui/__init__.py`：UI 包导出入口。
- `src/bookhub/ui/web_window.py`：当前主窗口 `WebAppWindow`；承载 `QWebEngineView` + `QWebChannel`，注册 `app://` scheme handler，装配 `UiBridge`；`page.setBackgroundColor` 与主题日/夜底色同步，减轻 Windows 焦点切回时 Chromium 清屏闪白；`web_zoom_factor` 启动 `setZoomFactor` 恢复并以轮询+debounce 写回 `app_settings`；负责后端编排——扫描/缩略图 worker、原生 `QFileDialog` 添加根目录与编辑封面（书籍+漫画；漫画写 `manual:` fingerprint 防自动缩略图覆盖）、`remove_from_library`（仅删库记录不删磁盘）、`open_text_rules` 转交 Bridge 打开 Web 面板（不再 `exec` 原生 `TextRuleDialog`）、字体与设置写库（含 `text_encoding_preference`）；扫描完成 Toast 计入 `comic_added_count`，冲突日志优先写 `incoming_path`（含漫画同名冲突）；忙时再点扫描/缩略图会 Toast，并通过 `scanState.kind` 推送忙碌态。
- `src/bookhub/ui/web/js/app.js`：单一 SPA 壳（侧栏/顶栏/详情常驻）；`#importBtn` → `addRoot("library")`；切页只重建 `#contentArea`；`scheduleRenderPage` + `renderGen` 可取消过期渲染；主内容区封面网格/合集/表格/漫画瀑布流与分页均走视口窗口化（`getBufferScreens`/`getGridColumns`/`measureCoverGridMetrics`/`visibleIndexRange` + `virt-spacer` + scroll/ResizeObserver rAF 合并）；可见 range 未变时跳过 DOM 重建，避免无效重建；`gridColumns` 限制每行封面数以放大单卡占屏、降低同屏解码量；`State.scrollPos` 切页恢复 scrollTop；收藏/漫画 `pageHeadTools` 排序控件；设置含 `viewportBufferScreens`（3–6）与 `gridColumns`（4–12）、`comic_title_conflict_policy` 下拉（都留/跳过新人/保留较新）、`textEncodingPreference` 下拉（简体优先/繁体优先/自动），并在 hash 字段内提示 Fast 漏检风险；路径与扫描任务合并到“路径与扫描”页，旧 `tasks` 状态自动归一到 `paths`；设置删路径确认模态；Settings 文本根「Rules」走 Web Text Rules 面板；Tasks 扫描摘要（字段兼容别名并计入漫画新增）；扫描/缩略图忙碌时禁用顶栏与 Settings 全部相关按钮；漫画性能三项开关；右键/详情支持漫画编辑封面与「从书库移除」；页面路由与网格/列表/漫画/合集渲染、详情栏、搜索建议、设置页、Quick Add/合集模态、日/夜主题引擎；全局拦截 Chromium 默认右键。
- `src/bookhub/ui/web/js/text_rules.js`：Text Rules 宽屏遮罩三栏编辑器（字段/规则链/步骤/预览）；防抖单样本预览、多样本预览、内置模板、用户预设、常用正则与帮助抽屉；经 Bridge 读写 `rules_json`。`renderTextRulesPanel()` 仅在 `openTextRulesPanel` 打开时构建一次性外壳（`.tr-overlay`/`.tr-host`/header/footer，带入场动画）；此后所有编辑（字段切换、规则/步骤增删移动、source/类别/类型 change、模板/预设）改调用 `renderTrBody()` 仅重建 `.tr-body` 三栏内容并保存/恢复各栏 `scrollTop`，不再重播入场动画；`installTrWheelGuard` 在 host 上拦截落在 `<select>` 的滚轮事件（Windows 悬停滚轮会静默改变原生 select 值并触发 change），`preventDefault` 后手动转发 `deltaY` 给 `.tr-col`/`.tr-drawer-body`，修复滚动时误触发全量重建导致的「白屏/像整页重载」；预览 diag 展示 `detectedEncoding` 与置信度。
- `src/bookhub/ui/web_bridge.py`：`UiBridge(QObject)` 前后端桥；内置英文回退含“Paths & Scan”与 Fast 指纹风险提示；`setPageSort`；`editCover` / `removeFromLibrary`；settings 含 `viewportBufferScreens` / `gridColumns` / `comicPlaceholderCopy` / `autoGenerateComicThumbs` / `comicThumbnailWorkers` / `comic_title_conflict_policy` / `textEncodingPreference` / `scanReport`；`@Slot` 暴露 `getBootstrap/search/getSuggestions/getDetail/openResource/toggleFavorite/openCollection/closeCollection/getTags/getCollections/addTag/removeTag/createCollection/setCollectionMembership/removeFromCollection/editCover/removeFromLibrary/openFolder/setSetting/setThemeSettings/addRoot/removeRoot/openTextRules/getTextRules/previewTextRule/previewTextRulesMulti/saveTextRules/getTextRulePresets/setTextRulePresets/startScan/startThumbnailTask/reloadFonts/getErrorLogs`；`Signal` 推送 `resourcesChanged/toast/scanProgress/scanState/settingsChanged/errorLogsChanged/languageChanged/textRulesOpen`；内部持有 `LibraryViewModel`（库/文本双上下文）并把书籍/文本/漫画/收藏/合集统一构造为前端资源载荷；封面路径写入 scheme 白名单集合；Text Rules 样本路径沙箱于对应 text root；预览载荷透传 `detectedEncoding` / `encodingConfidence`。
- `src/bookhub/library/repository.py`：`PRAGMA foreign_keys` + `busy_timeout`；删书/漫画与移根时清关联表；启动 orphan 清理；`hash_strategy` 缺省与非法值回退均为 `quick`；`comic_view_mode` 缺省为 `pagination`；`viewport_buffer_screens` 缺省 3（允许 3–6）；`grid_columns` 缺省 6（允许 4/5/6/7/8/10/12，限制每行封面数）；`comic_title_conflict_policy` 缺省 `skip_incoming`；`text_encoding_preference` 缺省 `simplified`。
- `src/bookhub/ui/web_scheme.py`：`app://` 自定义 URL scheme；`register_app_scheme()`（须在 QApplication 前调用）、`to_local_path()`（`file://`/裸路径归一化）、`AppSchemeHandler`（`app://app/*` 服务 `web/` 静态资源；`app://img/x?p=` 仅服务白名单封面图，越权拒绝）。
- `src/bookhub/ui/web/index.html`：玻璃拟态 UI 骨架（侧栏含 Import Books、顶栏/主区/详情栏/遮罩/toast/右键菜单挂载点），通过 `app://` 加载 css 与 js。
- `src/bookhub/ui/web/css/app.css`：玻璃拟态样式与动效；`.content-split` `user-select:none`（避免拖选干扰封面操作）；视口虚拟列表 `.virt-spacer-top/bottom`；`.content-split` / spacer / grid 设 `overflow-anchor: none`，禁用 Chromium 滚动锚定以防与 spacer 同步形成反馈环；Text Rules `.tr-overlay` / `.tr-host` 三栏宽屏面板与抽屉样式；`.tr-col` / `.tr-drawer-body` 设 `overflow-anchor: none`，对齐 `.content-split` 已验证约束，避免与 `renderTrBody()` 局部重建形成滚动锚定反馈；网格 `.book-card .cover` / `.mini-cover` 与详情 `.detail-cover-slot` 均 `object-fit: contain`（兼容非 2:3）；`.context-menu` 用 `width: max-content` 按文案收缩（避免子项 `width:100%` 相对视口撑满）；快添列表「添加/已添加」与 `.path-add-btn` 半透明 hover。
- `src/bookhub/ui/web/js/qwebchannel.js`：Qt 官方 `qwebchannel.js` 原样内置（从 Qt 资源导出）。
- `requirements-dev.txt`：开发/测试依赖（`pytest==8.3.5`）；运行依赖仍见根目录 `requirements.txt`。

### 3.6 UI 数据模型（bookhub/ui/models）
- `src/bookhub/ui/models/__init__.py`：模型包入口。
- `src/bookhub/ui/models/resource.py`：UI 层 `ResourceItem` 资源模型。

### 3.7 UI 资源组件（bookhub/ui/resources）
- `src/bookhub/ui/resources/__init__.py`：资源包入口。
- `src/assets/app_icon_bookcase.svg`：书柜主题应用图标源文件。
- `src/assets/app_icon_bookcase.ico`：Nuitka/Windows exe 使用的应用图标。
- `src/bookhub/ui/resources/assets.py`：图标/资源加载，支持 icons 子目录与顶层资产图标。
- `src/bookhub/ui/resources/font_runtime.py`：运行时字体服务；扫描并注册 `src/fonts` 字体文件、解析有效字体与回退策略。
- `src/bookhub/ui/resources/layout_config.py`：布局尺寸与间距配置；包含 cover-only 选中边框宽度/颜色的归一化与运行时状态。
- `src/bookhub/ui/resources/styles.py`：仅保留 `DEFAULT_FONT_STACK`，供 `WebAppWindow` 字体回退；旧全局 QSS/`build_app_style` 已随 Widgets UI 清理移除。

### 3.8 视图模型组件（bookhub/ui/viewmodels）
- `src/bookhub/ui/viewmodels/__init__.py`：视图模型包入口。
- `src/bookhub/ui/viewmodels/library_viewmodel.py`：Library/Text 资源查询过滤、字段前缀搜索（`title:`/`author:`/`tag:`）、视图模式、搜索建议状态。

## 4. 当前关键实现（简要）
- 2026-07-18 Quick 默认与设置合并：新装/`hash_strategy` 非法回退改为 `quick`；Settings 指纹字段增加 Fast 漏检提示；「路径」与「扫描与任务」合并为「路径与扫描」（保留 `paths` ID，旧 `tasks` 归一）；旧用户已持久化 Fast 不强制迁移；见 `decision-20260718-001`。
- 2026-07-17 TXT 编码偏好：`text_encoding_preference`（simplified|traditional|auto，默认简体）；64KB 探测 + 简/繁排名 + 双候选回退；规则预览 diag 显示 `detectedEncoding`/置信度；见 `decision-20260717-002`。
- 2026-07-17 Text 指纹跳过 / 漫画同名策略：`scan_text_roots` 与 Library 共用 Settings `hash_strategy` 跳过未变更 TXT（无 thumb 要求）；同 `comic_root` 同标题按 `comic_title_conflict_policy`（默认 `skip_incoming`）分支；Settings 下拉可配。
- 2026-07-16 漫画格式 / Missed 清理 / indexer 契约靠拢：COMIC 扩展 gif/bmp/tiff（GIF 首帧封面）；删除 Missed 恢复 API 与文案，启动 purge `is_missing=1`；indexer-contract/agent 改为描述全量遍历+局部跳过。
- 2026-07-16 TXT 编码 / 忙时 Scan / README 漫画边界：`text_encoding` 统一探测；忙碌态禁用全部 Scan/缩略图按钮并 Toast；README 标明文件夹漫画预期、不支持 CBZ/CBR。
- 2026-07-16 扫描反馈对齐：Toast/摘要计入 `comic_added_count`；`to_summary` 输出历史别名键；冲突日志优先 `incoming_path`；Settings 展示 skipped / comic added。
- 2026-07-16 Library 增量扫描：`compute_fingerprints` 按 `hash_strategy` 分级读盘；`scan_roots` 对指纹未变且缩略图仍在的书跳过元数据/封面；`map_library_books_for_scan` + upsert 指纹 COALESCE；摘要字段 `skipped_unchanged_count`。
- 2026-07-14 旧 Widgets UI 清理：删除已无运行时入口的 `app_window.py`、`pages/`、`widgets/`、`dialogs/`；删除仅测旧 UI 的 `test_text_rule_dialog.py`/`test_comic_page_cache.py`；`test_cover_grid_settings.py` 仅保留 Repository/`layout_config` 断言；`styles.py` 瘦身为 `DEFAULT_FONT_STACK`。设计史料仍在 `Dev_Document/UI/旧UI-*`，与源码清理解耦。
- 2026-07-11 UI 重写（WebEngine 玻璃拟态）：UI 层从纯 QSS 迁移为 `QWebEngineView` 加载 `src/bookhub/ui/web/` 前端，`QWebChannel` 经 `UiBridge` 与后端双向通信；`app://` 自定义 scheme 服务前端资源并以白名单方式代理封面图；内建完整日/夜主题引擎与 Web 化设置页。`main.py` 入口为 `WebAppWindow`；Text Rules 走 Web 三栏面板。`library/` 后端与数据结构未改动；`build_nuitka.ps1` 携带 `web/` 与 QtWebEngine；`src/tests/test_web_bridge_smoke.py` 覆盖桥接与 scheme。- 运行依赖：`requirements.txt` 采用固定版本策略；在 Python 3.10.6 环境锁定 `PySide6==6.6.1` 以规避 `libshiboken/signature` 初始化崩溃。
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
- 缺失记录治理：扫描按 scope 检查已入库源路径；缺失项写入 `src/Scan_error_logs` 后硬删除；无 Missed 指纹恢复；启动时 purge 遗留 `is_missing=1` 行；重名冲突遇到陈旧路径会先清理再导入。
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
