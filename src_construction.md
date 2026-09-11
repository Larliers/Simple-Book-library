# src 结构说明书（精简且完整）

更新时间：2026-09-11

## 1. 文档目标
- 保留字符串式文件路径结构。
- 给出每个代码组件（文件）的一句话用途。
- 作为 `src/` 结构与职责的当前事实文档。
- 仓库分支：`main` 为当前产品线（原 `2.0_glass_ui`，GitHub 默认）；`GUI` 为旧主干史料（原 `main`），不当开发基线。详见 `Agent-rule/project-context.md`。

## 2. 字符串式文件路径结构

### 2.1 UI 设计原型（Dev_Document，非运行时）
```text
Simple-Book-library-Dev_Document/UI/
├─ 新UI/
│  └─ glassmorphism-ui.html          # Glassmorphism 交互画板（单文件内联 CSS/JS）
├─ Changable_vaporwave_ui/           # 蒸汽波风格静态预览（与 glassmorphism DOM 对等、CSS 独立）
│  ├─ vaporwave-ui.html              # 入口页：全组件预览 + vw-scene 背景（大气渐变 + 扫描线）
│  ├─ fonts/                         # Sora/Space Mono woff2（本地，OFL）
│  ├─ css/
│  │  ├─ vaporwave-fonts.css         # @font-face 本地字体
│  │  ├─ vaporwave-tokens.css        # 色板/字体/阴影 CSS 变量（参考 karsyymiras.cc）
│  │  ├─ vaporwave-background.css   # 大气渐变 + CRT 扫描线（无太阳/透视网格）
│  │  ├─ vaporwave-layout.css       # app-shell 四列网格与响应式断点
│  │  └─ vaporwave-components.css    # 侧栏/顶栏/卡片/表格/弹窗/设置/Text Rules 等组件重皮肤
│  ├─ real-dom-preview.html          # 真实 DOM 镜像验证页：1:1 复刻运行时 index.html/app.js 结构并直连 src 生产 CSS，浏览器内验证皮肤排版（Library/Settings/Modal/Toast/TextRules + 皮肤/昼夜切换），不参与打包
│  └─ js/
│     └─ preview.js                 # 视图/Settings·Dialogs·States 面板切换与 Text Rules 假交互
├─ 旧UI-1.0/                         # 早期 PNG 截图
└─ 旧UI-2.0/                         # 旧版 HTML/PNG 史料
```

### 2.2 运行时源码（src）
```text
src/
├─ main.py
├─ tests/
│  ├─ js/
│  │  ├─ test_random_recommendations.js
│  │  └─ test_shortcuts.js
│  ├─ test_comic_preview_pipeline.py
│  ├─ test_comic_page_cache.py
│  ├─ test_rule_engine.py
│  ├─ test_rule_preview.py
│  ├─ test_text_rule_structure_parser.py
│  ├─ test_text_rule_dialog.py
│  ├─ test_scan_pdf_degrade.py
│  ├─ test_library_scan_incremental.py
│  ├─ test_text_scan_incremental.py
│  ├─ test_text_thumbnail_tasks.py
│  ├─ test_root_scan_strategy.py
│  ├─ test_scan_summary_fields.py
│  ├─ test_text_encoding.py
│  ├─ test_missed_cleanup.py
│  ├─ test_text_scan_tags.py
│  ├─ test_update_checker.py
│  ├─ test_app_paths.py
│  ├─ test_repository_orphan_cleanup.py
│  └─ test_collection_kinds.py
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
   ├─ app_paths.py
   ├─ version.py
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
   │  ├─ data_paths.py
   │  ├─ preview_cache_migrate.py
   │  ├─ preview_cache_worker.py
   │  ├─ update_checker.py
   │  ├─ update_check_worker.py
│  ├─ formats/
│  │  ├─ __init__.py
│  │  ├─ registry.py
│  │  ├─ common.py
   │  │  ├─ html_md.py
   │  │  ├─ fb2.py
   │  │  ├─ docx_fmt.py
   │  │  ├─ cbz.py
   │  │  └─ zip_safety.py
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
   │  ├─ text_cover.py
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
- `src/tests/test_scan_pdf_degrade.py`：PDF 后端降级容错回归测试（PyMuPDF 不可用时的聚合 warning 与入库行为）；Library 扫描进度 `total=0` busy 语义；comic/text 扫描断言真实 total。
- `src/tests/test_repository_orphan_cleanup.py`：根目录删除 LIKE 通配符误伤回归；整型设置非法值回退/越界 clamp（BUG-6）。
- `src/tests/test_library_scan_incremental.py`：Library 增量扫描与 `hash_strategy` 分级指纹（未变跳过、touch 强制更新、缺缩略图重处理、COALESCE 保留指纹）；`ScanRequest.roots` 使用 `LibraryScanRoot`。
- `src/tests/test_text_scan_incremental.py`：Text Novel 同名 sidecar 扫描回归；覆盖 webp/png/jpg/jpeg 优先级、非同名忽略、无封面/坏图 warning、自动封面增删改、TXT 未变时封面仍刷新，以及有效 manual 不被扫描覆盖。
- `src/tests/test_root_scan_strategy.py`：目录级扫描策略回归（旧库 `scan_strategy` 列迁移、Library/Text per-root 覆盖与全局回退、漫画 snapshot/full 旁注刷新、`set_root_scan_strategy` 合法性与 repository 默认值）。
- `src/tests/test_scan_summary_fields.py`：扫描摘要字段对齐回归（comic 计入新增、别名键、冲突 `incoming_path`）。
- `src/tests/test_text_encoding.py`：TXT 编码探测回归（GBK/GB18030、UTF-8 BOM、简/繁偏好、低置信双候选、规则预览 `detectedEncoding`）。
- `src/tests/test_missed_cleanup.py`：启动时清理遗留 `is_missing=1` 行；确认无 Missed 恢复 API。
- `src/tests/test_comic_preview_pipeline.py`：漫画快扫占位与后台并行补图回归测试（占位复制、压缩替换、原图删除、超大图降采样、排序顺序、GIF/BMP/TIFF 入库与 GIF 首帧封面）。
- `src/tests/test_cover_grid_settings.py`：封面选中边框归一化与 Repository 偏好持久化（含 Text Novel Grid/List、Text 规则预览高度/窗口尺寸/预设、随机推荐密度，以及八项快捷键的默认空绑定、合法值、非法/保留键拒绝、冲突、清除和重启持久化）；已不再依赖旧 Widgets 页。
- `src/tests/test_web_bridge_smoke.py`：Web Bridge / scheme / Text Rules CRUD 冒烟；`NAV_ITEMS` 含图书馆/书籍合集/文本小说/小说合集/漫画/漫画合集/随机推荐；验证 `getRandomRecommendations()` 三类来源隔离与密度行为，并调用 Node 脚本验证推荐及快捷键前端行为；覆盖 `shortcutBindings` payload、`setShortcutBinding` 返回/冲突、`nativeShortcutInput` 信号、Windows `XBUTTON`/`APPCOMMAND` 映射、`ShortcutWebView` 对自身及会吞掉事件的子控件上 Back/Forward 按下拦截；`openResource` 在可打开目标存在时发出 `open_external` `interactionEvent`，资源或文件缺失不发；其余覆盖目录策略、更新、资源格式、合集与漫画打开路径。
- `src/tests/test_text_thumbnail_tasks.py`：Text Novel 设置页缩略图任务回归；覆盖清空受控 sidecar 缓存、清除封面状态、从当前同名图重建，以及有效 manual 封面不被重建覆盖。
- `src/tests/js/test_random_recommendations.js`：以 Node 内置 `vm` 和最小 DOM 假件真实执行生产 `app.js`；覆盖图书/小说/漫画推荐交互、缓存与响应式密度，并覆盖 Text Novel Grid 标题、独立视图偏好及 Text/List 与 Library/List 的封面列差异。
- `src/tests/js/test_shortcuts.js`：以 Node 内置 `vm` 执行生产 `app.js`；覆盖按键规范化/保留键、`BrowserBack`/`keyCode` 166/167/`button`/`which`/`buttons` 侧键录入、`auxclick` 去重、统一动作路由、Library/合集详情/随机推荐来源、无选择和不可用提示、输入/模态/长按屏蔽、冲突保持录入、Escape 取消、原生侧键分发，以及退出/进入最近系列分动作和三类合集独立记忆。
- `src/tests/test_comic_search.py`：漫画顶栏搜索回归（ViewModel title/path/info_text 过滤；UiBridge comic 与 comic_collections 总览 context 路由，PySide6 可用时跑 Bridge 集成）。
- `src/tests/test_collection_kinds.py`：合集 kind 隔离（book/text_novel/comic 互不混装）、跨类加入拒绝、小说成员从书籍合集剥离、收藏星标迁入默认「收藏」合集、删漫画清 `collection_comics`。
- `src/tests/test_library_viewmodel_search.py`：Library/Text 搜索与字段前缀建议回归。
- `src/tests/test_update_checker.py`：GitHub 更新检查回归（版本 normalize/compare、mock API 成功/404/有更新/已最新/网络错误）。
- `src/tests/test_app_paths.py`：运行时路径回归（dev 态 repo 根路径 vs Nuitka frozen 态 exe 同级 `img_preview`/`sql`/`Scan_error_logs`）。
- `src/tests/test_preview_cache_dir.py`：缩略图缓存目录解析、设置覆盖、migrate/rewire/switch、URI 改写边界与 cleanup 路径守卫。
- `src/tests/test_new_formats_import.py`：Library HTML/MD/FB2/DOCX 元数据与缩略图、zip 安全上限、CBZ 漫画扫描与失踪清理。
- `src/sql/.gitkeep`：运行数据目录占位，实际运行时生成 `library.db`、`scan_report.json`。

### 3.2 bookhub 包根
- `src/bookhub/__init__.py`：包标记与顶层命名空间；导出 `__version__`。
- `src/bookhub/app_paths.py`：运行时根目录与默认数据路径（`is_frozen`/`app_root`）；开发态 `{repo}/img_preview`、`src/sql`、`src/Scan_error_logs`；打包态 exe 同级 `img_preview/`、`sql/`、`Scan_error_logs/`。
- `src/bookhub/version.py`：应用 semver（`APP_VERSION`）与 GitHub Releases/API 常量（`Larliers/Simple-Book-library`）。

### 3.3 国际化组件（bookhub/i18n）
- `src/bookhub/i18n/__init__.py`：国际化导出入口。
- `src/bookhub/i18n/language.py`：语言切换、词典加载、回退策略。
- `src/bookhub/i18n/locales/zh-cn.json`：中文文案键值表；含随机推荐、推荐密度，以及快捷键设置导航、动作分组、录入/清除、鼠标侧键、冲突/无选择/不可用、退出与进入最近系列及合集页提示；设置导航将路径与扫描合并命名。

### 3.4 书库后端组件（bookhub/library）
- `src/bookhub/library/__init__.py`：后端模块导出入口。
- `src/bookhub/library/repository.py`：SQLite 读写中心；设置、书籍、书单、收藏、标签操作；Text Novel 记录含 `cover_source`/`cover_fingerprint`，旧非空小说封面迁移为 manual，`text_novel_view_mode` 默认 Grid 并持久化，并为缩略图维护任务按 roots 枚举活动小说；其余包含随机推荐密度、快捷键、目录策略、扫描指纹、漫画策略、文本编码、预览缓存及 UI 偏好。
- `src/bookhub/library/scanner.py`：目录扫描与文件过滤；Library 入库 PDF/EPUB/HTML/MD/FB2/DOCX，Comic 入库叶子图片文件夹与 CBZ；Text 为 TXT 并复用 `text_cover.py` 完成同名 sidecar 选择、指纹和缓存，有效 manual 优先、损坏图 warning 降级；其余包含目录策略、漫画快照/full、同名冲突、失踪清理、文本编码和进度语义。
- `src/bookhub/library/text_cover.py`：Text Novel 同名封面的共享服务；按 `.webp/.png/.jpg/.jpeg` 选择同 stem 图片，计算路径+size+mtime_ns 指纹，并生成 360×540 以内 WebP 缓存，供扫描与设置页重建任务复用。
- `src/bookhub/library/text_encoding.py`：TXT 统一读入；`DecodeResult` / `detect_and_decode`；UTF-8 优先，64KB 样本经 charset-normalizer 按 `text_encoding_preference`（简/繁/自动）排名；简体永不选 Big5，繁体优先 Big5；低置信时 GB18030↔UTF-8 双候选回退。
- `src/bookhub/library/data_paths.py`：缩略图缓存目录解析；默认经 `app_paths.default_preview_dir()`（dev：`img_preview/`，打包：exe 同级）；空/相对/不可写路径回退默认；`preview_cache` 模式枚举。
- `src/bookhub/library/formats/`：新格式解析与封面提取；`registry.py` 是 Library 格式支持、元数据提取与缩略图生成的单一注册入口（延迟导入）；其余 `html_md`/`fb2`/`docx_fmt`/`cbz`/`zip_safety`/`common` 提供具体实现。Library 用内嵌图或标题占位卡；Comic CBZ 取包内首图，`prepare_cbz_for_external_viewer` 将全部页解压到 `preview/comic/read/` 供外部看图；docx/fb2.zip/cbz 经成员数与未压缩体积上限防 zip bomb。
- `src/bookhub/library/preview_paths.py`：预览图目录结构与路径构建服务（`resource_type + variant`）。
- `src/bookhub/library/preview_cache_migrate.py`：缓存目录 migrate（先 staging 复制、碰撞校验、再 URI 改写）/ rewire_only / switch_only；拒绝迁移到旧缓存的子目录；`safe_unlink_under_preview` 供所有 cleanup 守卫。
- `src/bookhub/library/preview_cache_worker.py`：后台线程执行缓存目录变更，避免大目录复制卡 UI。
- `src/bookhub/library/update_checker.py`：GitHub `/releases/latest` 请求（stdlib urllib）、semver 归一化/比较、`check_for_update()` 返回 `update_available|up_to_date|error` JSON 形字段。
- `src/bookhub/library/update_check_worker.py`：`UpdateCheckWorker(QThread)` 后台执行更新检查并通过 `finished` 信号回传 JSON，避免阻塞 WebEngine UI 线程。
- `src/bookhub/library/metadata.py`：元数据提取与缩略图生成（WebP，`file://` 路径）；`extract_metadata_by_extension` / `build_thumbnail_by_extension` 显式分派 PDF/EPUB/HTML/MD/FB2/DOCX；`extension_lower` 识别 `.fb2.zip`；`compute_fingerprints` 按策略分级读盘（`size_mtime` 仅 stat、`quick` 前 4MB、`sha256` 整文件）。
- `src/bookhub/library/models.py`：扫描/任务的数据结构定义（含 `LibraryScanRoot`/`ComicScanRoot`/`TextScanRoot` 可空 `scan_strategy`；`resolve_library_hash_strategy` / `resolve_comic_scan_strategy`——总开关关时忽略根覆盖、开时 NULL 继承全局）；`ComicScanRequest.scan_strategy` 全局默认 `snapshot`；`skipped_unchanged_count`；`TextScanRequest.hash_strategy` 默认 `quick` 并携带 `encoding_preference`；`ComicScanRequest.title_conflict_policy` / `encoding_preference`；`to_summary` 同时输出前端历史别名键；`COMIC_IMAGE_EXTENSIONS` 含 jpg/png/webp/gif/bmp/tif/tiff。
- `src/bookhub/library/media_sanitizer.py`：封面图消毒；GIF/多帧图 `seek(0)` 后转 RGB PNG。
- `src/bookhub/library/text_rules/rule_models.py`：Text Novel 规则模型（`ImportRule`/`RuleStep`/`RuleContext`/`RuleResult`，含预览 warning 字段）。
- `src/bookhub/library/text_rules/rule_engine.py`：规则执行器与规则链回退（`apply_rule`、`apply_rule_chain`），透传步骤 warning。
- `src/bookhub/library/text_rules/source_resolver.py`：规则 source 解析（`filename`/`stem`/`txt_first_line`/`txt_head_text` 等）。
- `src/bookhub/library/text_rules/structure_parser.py`：Text 规则结构解析；支持嵌套括号块解析、括号范围过滤、括号外分隔符结构签名与多样本格式诊断分组。
- `src/bookhub/library/text_rules/step_handlers.py`：规则步骤处理（文本清洗、文本删除、split、多分隔符取段、分隔范围拼接、单行/范围行提取、删除前/后 N 行、分界线截取、按行循环提取、嵌套感知括号提取/删除、regex_extract 等）。
- `src/bookhub/library/text_rules/rule_preview.py`：Text 规则预览辅助；查找首个 TXT 样本、经 `text_encoding`（按偏好）读取首行/开头文本并复用规则链执行预览；样本载荷含 `detected_encoding` / `encoding_confidence`。
- `src/bookhub/library/text_rules/rule_examples.py`：默认规则链示例。
- `src/bookhub/library/text_rules/rule_catalog.py`：Text Rules Web 元数据目录（fields/sources/step 分类与参数表单、内置模板、常用正则、帮助章节）；`describe_step_catalog()` 供 Bridge 下发。
- `src/bookhub/library/worker.py`：扫描任务线程包装；从 `list_roots_with_strategy` / `list_comic_roots_with_strategy` / `list_text_roots_with_rules` 把各根 `scan_strategy` 注入 `LibraryScanRoot`/`ComicScanRoot`/`TextScanRoot`；漫画请求携带 `get_comic_scan_strategy()` 全局默认；透传 Library/Comic/Text 扫描进度信号；将 Settings `hash_strategy` 传入 Text/Library 请求（非法策略回退 `quick`）、将 `comic_title_conflict_policy` 与 `text_encoding_preference` 传入 Comic/Text 请求；汇总多 scope 统计与 warning。
- `src/bookhub/library/thumbnail_tasks.py`：Library/Comic/Text Novel 缩略图清理与重建任务实现；cleanup 仅 `unlink` `preview_dir` 内路径；Text Novel 清空时清除封面来源/指纹，重建时保留有效 manual 并从当前 sidecar 恢复；漫画 `cover_fingerprint` 以 `manual:` 开头时跳过 regenerate；`resolve_comic_open_path()` 解析漫画外部打开路径。
- `src/bookhub/library/thumbnail_worker.py`：缩略图任务线程包装；构造时可注入 `preview_dir`，按 `library|comic|text_novel` scope 分派 cleanup/regenerate。
- `src/bookhub/library/error_logs.py`：扫描/冲突日志读写；目录经 `app_paths.default_log_dir()`（dev：`src/Scan_error_logs/`，打包：exe 同级）。

### 3.5 UI 主组件（bookhub/ui）
- `src/bookhub/ui/__init__.py`：UI 包导出入口。
- `src/bookhub/ui/web_window.py`：当前主窗口 `WebAppWindow`；负责 WebEngine、主题底色/缩放、扫描/缩略图/缓存迁移/更新、原生目录与封面选择、资源删除及设置写库；手动编辑书籍/小说封面时标记 `cover_source=manual`；`ShortcutWebView` 统一转发鼠标 Back/Forward 并阻止网页历史导航。
- `src/bookhub/ui/web/js/app.js`：单一 SPA 壳；Text Novel 使用独立持久化 Grid/List，Grid 显示封面+标题并复用虚拟化，List 删除封面列而 Library 保留；Settings 为 Library/Comic/Text Novel 分别提供清空和重建缩略图按钮；当前页面写入 `body[data-page]`，用于将 390px 单列外壳限定在 Text Novel；其余含统一快捷键/右键动作、随机推荐响应式三列、主内容视图、详情、合集、搜索、主题和任务交互。
- `src/bookhub/ui/web/js/text_rules.js`：Text Rules 宽屏遮罩三栏编辑器（字段/规则链/步骤/预览）；防抖单样本预览、多样本预览、内置模板、用户预设、常用正则与帮助抽屉；经 Bridge 读写 `rules_json`。`renderTextRulesPanel()` 仅在 `openTextRulesPanel` 打开时构建一次性外壳（`.tr-overlay`/`.tr-host`/header/footer，带入场动画）；此后所有编辑（字段切换、规则/步骤增删移动、source/类别/类型 change、模板/预设）改调用 `renderTrBody()` 仅重建 `.tr-body` 三栏内容并保存/恢复各栏 `scrollTop`，不再重播入场动画；`installTrWheelGuard` 在 host 上拦截落在 `<select>` 的滚轮事件（Windows 悬停滚轮会静默改变原生 select 值并触发 change），`preventDefault` 后手动转发 `deltaY` 给 `.tr-col`/`.tr-drawer-body`，修复滚动时误触发全量重建导致的「白屏/像整页重载」；预览 diag 展示 `detectedEncoding` 与置信度。
- `src/bookhub/ui/web_bridge.py`：`UiBridge(QObject)` 前后端桥；Text Novel 页面声明 `grid_or_list`，settings payload 暴露 `textNovelViewMode`、推荐密度与完整快捷键绑定；其余包括随机推荐、资源变化、主题/设置/扫描/更新、资源与合集 CRUD、搜索、详情与 Text Rules。
- `src/bookhub/library/repository.py`：`PRAGMA foreign_keys` + `busy_timeout`；删书/漫画与移根时清关联表（含 `collection_comics`）；启动 orphan 清理；`collections.kind`（book/text_novel/comic）+ `collection_comics`；跨类加入拒绝；既有合集默认 book 并剥离小说成员；`favorite_*` 一次性迁入名为「收藏」的对应 kind 合集（表保留不 DROP）；`hash_strategy` 缺省与非法值回退均为 `quick`；`comic_view_mode` 缺省为 `pagination`；`viewport_buffer_screens` 缺省 3（允许 3–6）；`grid_columns` 缺省 6（允许 4/5/6/7/8/10/12，限制每行封面数）；随机推荐每类数量缺省 6（允许 3/6/9/12），内部最大列数缺省 2（允许 1/2/3）；`comic_title_conflict_policy` 缺省 `skip_incoming`；`text_encoding_preference` 缺省 `simplified`。
- `src/bookhub/ui/web_scheme.py`：`app://` 自定义 URL scheme；`register_app_scheme()`（须在 QApplication 前调用）、`to_local_path()`（`file://`/裸路径归一化）、`AppSchemeHandler`（`app://app/*` 服务 `web/` 静态资源含 woff2 字体；`app://img/x?p=` 仅服务白名单封面图，越权拒绝）。
- `src/bookhub/ui/web/index.html`：玻璃拟态 UI 骨架（侧栏含 Import Books、顶栏/主区/详情栏/遮罩/toast/右键菜单挂载点）；`data-ui-skin` + `data-theme` 双轴；`data-skin-link` 样式链由 `app.js` 按皮肤动态注入；`#vwSceneMount` 供蒸汽波 vw-scene 背景层。
- `src/bookhub/ui/web/fonts/`：蒸汽波 Web 字体（Sora/Space Mono woff2 + OFL.txt）；经 `app://app/fonts/*` 与 `skins/vaporwave/fonts.css` @font-face 加载，不依赖 CDN。
- `src/bookhub/ui/web/css/base.css`：布局/结构/动画（无 skin 色板）；Glass 与 Vaporwave 共用；1120px 断点确保响应式详情栏落位，600px 下 Text Novel 与 Settings 改为单列外壳，设置任务按钮允许换行且无横向溢出，并提供统一键盘焦点描边。
- `src/bookhub/ui/web/css/app.css`：legacy 入口，`@import` glass bundle（兼容旧引用）。
- `src/bookhub/ui/web/css/skins/glass/tokens.css`：玻璃拟态 day/night CSS 变量。
- `src/bookhub/ui/web/css/skins/glass/components.css`：玻璃拟态组件样式；随机推荐响应式网格；快捷键列表含录入描边、键帽、禁用清除按钮与窄屏无溢出重排。
- `src/bookhub/ui/web/css/skins/vaporwave/fonts.css`：蒸汽波 @font-face，引用 `web/fonts/` 本地 woff2。
- `src/bookhub/ui/web/css/skins/vaporwave/tokens.css`：蒸汽波 day/night token（Sora/Space Mono 语义变量）。
- `src/bookhub/ui/web/css/skins/vaporwave/background.css`：vw-scene 大气渐变 + CRT 扫描线（已移除太阳/动态透视网格）；night 子选择器微调。
- `src/bookhub/ui/web/css/skins/vaporwave/layout.css`：蒸汽波 z-index 层叠（不改生产 grid）。
- `src/bookhub/ui/web/css/skins/vaporwave/components.css`：蒸汽波组件重皮肤；与 Glass 保持随机推荐及快捷键列表结构一致，快捷键录入态使用霓虹描边、键帽与 Space Mono，窄屏不横向溢出。
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
- `src/bookhub/ui/viewmodels/library_viewmodel.py`：Library/Text/Comic 资源查询过滤、字段前缀搜索（`title:`/`author:`/`tag:`）、普通 query 匹配 title/author/tags/path/info_text、视图模式、搜索建议状态。

## 4. 当前关键实现（简要）
- 2026-09-11 远程 minor Release：Codex 文本小说 Grid/同名封面与缩略图维护已发布为 `v2.3.0`（Actions `Release` bump=minor，产物 `Simple-Book-library-v2.3.0-win64.zip`），叠在当天 `v2.2.0` 快捷键之上。
- 2026-09-11 Text Novel 缩略图维护：Settings 补齐清空/重建两个入口，经既有 `runThumbnailTask` 通道使用 `scope=text_novel`；清空只删除受控缓存并清除封面状态，重建保留有效 manual，否则按当前同名 sidecar 恢复，缺失时维持标题占位。
- 2026-09-11 Text Novel Grid 与同名封面：首次默认 Grid，并通过 `textNovelViewMode` 独立持久化；Grid 展示封面+标题，Text List 移除封面列。TXT 扫描按 WebP/PNG/JPG/JPEG 优先级匹配同目录同 stem 图片，缓存 360×540 内 WebP；路径+size+mtime_ns 封面指纹独立检测增删改，有效 manual 封面优先，坏图 warning 降级。
- 2026-09-11 可自定义快捷键：八个固定动作通过 `executeAction` 统一右键菜单与快捷键路径；绑定默认空并持久化，支持稳定键盘组合及鼠标 Back/Forward，拒绝冲突和保留键；输入/模态/Text Rules 屏蔽；合集导航拆成退出当前系列与进入最近系列，三类合集页各自只记本页最近一次成功打开项；Glass/Vaporwave 设置页同步。`openResource` 成功解析到可打开目标后发出 `open_external` 交互事件，关闭审查遗留的可追踪缺口。
- 2026-09-10 随机推荐响应式密度：每类推荐数量 3/6/9/12（默认 6）和内部最大列数 1/2/3（默认 2）持久化到 `app_settings`；三类外层列不变，内部按行优先并以单个 `ResizeObserver` 在 120–260px 目标卡宽内自动降列；数量变化重抽、列数变化仅重排，Glass/Vaporwave 同步。
- 2026-09-09 随机推荐页：侧栏在漫画合集后新增 `random_recommendations`；Bridge 的 `getRandomRecommendations()` 从未缺失且不受搜索条件影响的图书/文本小说/漫画三类来源各自无重复抽取，抽样上限现由 2026-09-10 的每类数量设置驱动；前端会话缓存推荐结果，外层固定三类列、内部使用响应式网格，支持整组重新推荐，并通过列级 `sourcePage` 复用正确的详情、双击打开、右键与 Quick Add 交互；仅扫描/资源增删显式使缓存失效，request id 阻止旧响应写回；Glass/Vaporwave 双皮肤同步。
- 2026-09-09 分支更名：默认产品线 `2.0_glass_ui` → `main`；旧主干 `main` → `GUI`（史料，不当开发基线）。
- 2026-09-09 发布线收敛：工作分支改动并入当时的 `2.0_glass_ui`（现已更名为 `main`）；删除本地 `cursor/fix-bugs-1-4` 与 `20260410`；经 Actions `Release` workflow patch bump 打包 win64 zip。BUG-5：Library 扫描 `total=0` 走 busy 条纹进度；BUG-6：整型设置 repository 层容错。
- 2026-08-18 三类合集互相独立：侧栏为图书馆 / 书籍合集 / 文本小说 / 小说合集 / 漫画 / 漫画合集；`collections.kind` 隔离成员；漫画合集为可新建命名列表（详情走 comic_grid）；独立「收藏」「漫画收藏」页退出侧栏，既有星标迁入默认「收藏」合集；见 `decision-20260818-001`。
- 2026-07-28 发布自动化与便携路径：`app_paths.py` 统一 dev/打包态数据目录；`scripts/pack_release.ps1` 将 `main.dist` 改名为 `Simple-Book-library-v{APP_VERSION}`、预建空 `img_preview`/`sql`/`Scan_error_logs` 并打 win64 zip；`.github/workflows/release.yml` 支持 workflow_dispatch 一键 bump（patch/minor/major）→ commit/tag → Nuitka build → pack → GitHub Release；用户数据不进入 zip。
- 2026-07-28 漫画顶栏搜索对接：`comics.title` 扫描入库已有，补齐前后端搜索链路；Bridge `_library_vm`/`_text_vm`/`_comic_vm`/`_comic_collection_vm` + `_search_vm_for_context`，`search`/`getSuggestions` 支持 comic 与漫画合集详情；前端 `searchContext`/`State.searchQueries` 按页独立 query 与 placeholder；匹配 title/path/info_text；合集总览仍无搜索。
- 2026-07-25 书籍格式角标：图书馆/书籍与小说合集详情封面网格左上角显示格式 pill（PDF/EPUB/FB2 等）；Bridge `_record_to_item`/`_item_payload`/`_book_payload` 下发 `extension`；`app.js` 白名单启用 `buildCoverSlot`+`formatBadgeLabel`；漫画页不显示；Glass/Vaporwave 双皮肤 `.cover-wrap`/`.format-badge`。
- 2026-07-24 蒸汽波排版崩坏修复（P0）：`skins/vaporwave/components.css` 由原型逐字节复制版（1090 行，选择器对不上真实 DOM，四大面板丢失 grid 落位导致主区被挤进 320px 窄列）重写为与 glass 逐选择器对齐的 613 行版本；布局声明照抄 glass、视觉层保留蒸汽波语言；新增 `Changable_vaporwave_ui/real-dom-preview.html` 真实 DOM 镜像验证页，浏览器截图验收 Library/Settings/Modal/Toast/TextRules 与 day/night 全部正常。
- 2026-07-24 蒸汽波背景精简：移除 vw-sun 条纹太阳与 vw-grid 动态透视网格，保留 atmosphere 渐变 + scanlines，减轻主内容区视觉干扰。
- 2026-07-24 UI 皮肤切换按钮反馈：`setUiSkin` 持久化后同步 `State.uiSkin` 并重绘 Settings 分段控件 active 态（仅视觉选中，仍不热重载 CSS）；`settingsChanged` 同步 `uiSkin` 字段。
- 2026-07-24 UI 皮肤切换（重启生效）：Settings Appearance Glass/Vaporwave 切换后 `setUiSkin` 持久化并 Toast 提示重启软件（不再 WebView 热重载）；蒸汽波字体内嵌于 `web/fonts/` + `skins/vaporwave/fonts.css`，离线可用。
- 2026-07-24 UI 皮肤切换：Settings Appearance 增加 Glass/Vaporwave 分段切换；`ui_skin` 持久化至 `app_settings`；CSS 拆为 `base.css` + `skins/glass/*` + `skins/vaporwave/*` 独立 bundle；`data-ui-skin` 与 `data-theme` 正交；蒸汽波含 day/night token 与 vw-scene 背景层。
- 2026-07-24 蒸汽波 UI 静态预览：新增 `Simple-Book-library-Dev_Document/UI/Changable_vaporwave_ui/`，DOM 结构与 `glassmorphism-ui.html` 对等，样式完全独立（Sora + Space Mono、霓虹硬阴影、透视网格背景）；含 Settings/Dialogs/Component States 底部预览区与 Text Rules 假交互；Night mode 控件仅静态展示；本次不涉及 `src/` 运行时皮肤切换。
- 2026-07-18 目录级扫描策略：`per_root_scan_strategy_enabled`（默认关）；三表可空 `scan_strategy`；开时 Library/Text 覆盖 `hash_strategy`、Comic 覆盖 `snapshot|full`；关时全局 `hash_strategy` / `comic_scan_strategy`（默认 snapshot）生效且保留 DB 覆盖值；`full` 禁用漫画 `folder_size_mtime` 短路并重读旁注；UI 路径页开关 + 各根策略弹窗 + General 漫画全局下拉；见 `decision-20260718-002`。
- 2026-07-18 Quick 默认与设置合并：新装/`hash_strategy` 非法回退改为 `quick`；Settings 指纹字段增加 Fast 漏检提示；「路径」与「扫描与任务」合并为「路径与扫描」（保留 `paths` ID，旧 `tasks` 归一）；旧用户已持久化 Fast 不强制迁移；见 `decision-20260718-001`。
- 2026-07-17 TXT 编码偏好：`text_encoding_preference`（simplified|traditional|auto，默认简体）；64KB 探测 + 简/繁排名 + 双候选回退；规则预览 diag 显示 `detectedEncoding`/置信度；见 `decision-20260717-002`。
- 2026-07-17 Text 指纹跳过 / 漫画同名策略：`scan_text_roots` 与 Library 共用 Settings `hash_strategy` 跳过未变更 TXT（无 thumb 要求）；同 `comic_root` 同标题按 `comic_title_conflict_policy`（默认 `skip_incoming`）分支；Settings 下拉可配。
- 2026-07-16 漫画格式 / Missed 清理 / indexer 契约靠拢：COMIC 扩展 gif/bmp/tiff（GIF 首帧封面）；删除 Missed 恢复 API 与文案，启动 purge `is_missing=1`；indexer-contract/agent 改为描述全量遍历+局部跳过。
- 2026-07-16 TXT 编码 / 忙时 Scan / README 漫画边界：`text_encoding` 统一探测；忙碌态禁用全部 Scan/缩略图按钮并 Toast；README 标明文件夹漫画预期、不支持 CBZ/CBR。
- 2026-07-16 扫描反馈对齐：Toast/摘要计入 `comic_added_count`；`to_summary` 输出历史别名键；冲突日志优先 `incoming_path`；Settings 展示 skipped / comic added。
- 2026-07-16 Library 增量扫描：`compute_fingerprints` 按 `hash_strategy` 分级读盘；`scan_roots` 对指纹未变且缩略图仍在的书跳过元数据/封面；`map_library_books_for_scan` + upsert 指纹 COALESCE；摘要字段 `skipped_unchanged_count`。
- 2026-07-14 旧 Widgets UI 清理：删除已无运行时入口的 `app_window.py`、`pages/`、`widgets/`、`dialogs/`；删除仅测旧 UI 的 `test_text_rule_dialog.py`/`test_comic_page_cache.py`；`test_cover_grid_settings.py` 仅保留 Repository/`layout_config` 断言；`styles.py` 瘦身为 `DEFAULT_FONT_STACK`。设计史料仍在 `Dev_Document/UI/旧UI-*`，与源码清理解耦。
- 2026-07-11 UI 重写（WebEngine 玻璃拟态）：UI 层从纯 QSS 迁移为 `QWebEngineView` 加载 `src/bookhub/ui/web/` 前端，`QWebChannel` 经 `UiBridge` 与后端双向通信；`app://` 自定义 scheme 服务前端资源并以白名单方式代理封面图；内建完整日/夜主题引擎与 Web 化设置页。`main.py` 入口为 `WebAppWindow`；Text Rules 走 Web 三栏面板。`library/` 后端与数据结构未改动；`build_nuitka.ps1` 携带 `web/` 与 QtWebEngine；`src/tests/test_web_bridge_smoke.py` 覆盖桥接与 scheme。- 运行依赖：`requirements.txt` 采用固定版本策略；在 Python 3.10.6 环境锁定 `PySide6==6.6.1` 以规避 `libshiboken/signature` 初始化崩溃。
- 打包准备：新增书柜主题应用图标，`scripts/build_nuitka.ps1` 使用 `Nuitka==4.1.2` 构建 exe，从 `version.py` 读取 `APP_VERSION` 写入 `--product-version`/`--file-version`，并显式打包 `src/assets`、i18n locales、`fitz` 与 `pymupdf` 原始包目录；PyMuPDF 采用预编译 `.pyd/.dll` 随包携带并关闭 Nuitka excluded-module 运行时阻断；`scripts/pack_release.ps1` 负责发行目录改名与 zip；`scripts/`、`src/tests/`、运行数据库、扫描日志、缩略图缓存不进入发行包。
- 2026-05-29 外部工具链注释：本次仅完成 Hue 离线落地与本地 MCP 集成（`F:\Coding_Dev\UI\hue*`、全局 `mcp.json`），`src/` 代码与目录结构未发生变更。
- 2026-05-30 外部工具链注释：Hue MCP 相关目录已统一迁移到 `F:\MCP\hue-mcp-server` 与 `F:\MCP\hue`；本次仍不涉及 `src/` 代码变更。
- 2026-06-11 UI 范本注释：新增 `Simple-Book-library-Dev_Document\UI\新UI\glassmorphism-ui.html` 作为 Glassmorphism 交互画板；设置、弹窗、组件状态已拆到底部独立预览区，便于后续拖拽/缩放窗口设计；页面内新增中文/英文 i18n 浮动预览按钮，且注释标明不进入后续正式开发；左侧侧栏删除“导入书籍”入口；Library 总页面主区采用 cover-only 封面网格，标题/作者/tag 等信息交由右侧详情栏承载；范本新增日间/夜间主题变量、按本地时间 `22:00-07:00` 自动切换的夜间模式设置区、检查频率与自动过渡时长预览控件；手动 Day/Night/Auto 预览使用快速切换，避免分钟级过渡造成白天样式灰化残留；本次不涉及 `src/` 代码与目录结构变更。
- 缩略图：WebP 落盘，DB 保存 `file://` URL。
- 数据能力：三类独立命名合集（书籍/小说/漫画）已接入；Tags 仍走书籍；独立 Favorites 页已退出侧栏。
- Library 展示：主区双栏，右侧详情栏常驻且可拖拽宽度。
- 合集详情展示：书籍/小说合集详情支持与 Library 一致的 grid/list 切换并接入右侧详情栏；漫画合集详情仅 comic_grid。
- 封面网格视觉：Library、Comic、三类合集详情统一使用“背景 + 封面直陈列”无壳层样式；仅在选中时显示可配置边框（全局设置）。
- Settings 导航：常规、外观与主题、快捷键、路径与扫描、错误日志；路径与任务已合并，快捷键页为八项固定动作提供录入/清除，不恢复旧占位管理页。
- Text Novel：新增独立侧栏入口与独立列表页；TXT 不进入 Library 主列表；右侧详情栏可展示 `info_text` 预览。
- 详情面板语义统一：`info_text` 仅作为“文本预览”渲染一次；「所属合集」按资源 kind 显示（图书/小说 `bookCollections`，漫画 `comicCollections`）。
- Text 规则：规则弹窗新增“使用文档”入口、三步引导区、一键模板（标题/作者/兜底）与当前字段规则链预览；source 与 step type 显示文案与内部 code 分离（`userData` 持久化 code），在不改 JSON 协议前提下增强可读性。
- Text 规则 i18n：补齐规则弹窗内参数字段名、source/step 文案、规则/步骤列表格式与帮助文档文案键，减少硬编码英文暴露。
- i18n 治理基线：新增 `scripts/i18n_hardcoded_scan.py`，用于扫描 UI 常见硬编码文案候选并输出清单（仅报告，不阻断）。
- 扫描容错：当 PyMuPDF（`fitz`）不可用时，PDF 扫描自动降级为“仅入库+标题兜底”，跳过元数据/缩略图并输出单条聚合 warning，避免错误风暴弹窗。
- 缺失记录治理：扫描按 scope 检查已入库源路径；缺失项写入 `src/Scan_error_logs` 后硬删除；无 Missed 指纹恢复；启动时 purge 遗留 `is_missing=1` 行；重名冲突遇到陈旧路径会先清理再导入。
- 任务触发：启动扫描支持配置开关（默认关闭）；路径变更自动扫描支持独立开关（默认开启）。
- 缩略图任务：Library、Comic 与 Text Novel 分 scope 清理/重建；结果摘要包含 `scope + task_kind + total/succeeded/skipped/failed`。
- Reading Now 与 Tools 占位页已下线：主窗口不再注册对应页面，侧栏仅保留可用功能入口；底层 `status` 字段与数据结构保持不变。
- TopBar：移除右侧 IMPORT/NEW LIST/刷新/菜单占位区，搜索栏填充顶部可用宽度。
- TopBar：搜索框支持最小高度与字号放大；搜索输入与建议下拉字号可在 Settings 调节并持久化（默认 15px）。
- 本地启动：根目录可放置被 `.gitignore` 忽略的 `启动 简易图书馆.lnk`，双击后通过 `.venv\Scripts\pythonw.exe` 启动 `src\main.py`。
- 网格布局：Library/Favorites/CollectionDetail 的书籍网格统一左内边距 12px，避免左侧贴边溢出观感。
- 交互规则：单击看详情（无门控延迟）、双击外部打开。
- 字体重载：`Reload Fonts` 现在执行完整链路（重扫 `src/fonts` -> 注册字体 -> 解析回退 -> `QApplication.setFont` + 动态 QSS 立即生效 -> 持久化设置）；目录不存在时自动创建并通过右下角 Toast 提示。
- 漫画性能：扫描阶段改为“快扫入库+可选首图占位复制”，压缩缩略图改为后台并行补全；预览图目录升级为 `img_preview/<resource_type>/<original|compressed>`。
- 漫画性能（本轮）：Comic/漫画合集详情页显示模式改为 Settings 全局二选一（瀑布流/分页），分页容量可配（24/48/72/96）；扫描侧排序字段改为 `folder_modified_at`（目录 mtime）并保留 `folder_size_mtime` 仅作增量判定；超大封面占位自动降采样以规避 Qt 256MB 解码限制。
- 页面渲染性能（本轮）：Comic/漫画合集详情增加“事件驱动失效 + 双层缓存（数据索引缓存 + 卡片复用缓存）”；Library/三类合集网格改为“布局重排优先复用卡片、按需重建单卡”，减少切页和重排时的全量 widget 销毁与封面重复解码。

## 5. 边界与约束
- 当前导入粒度：目录导入（不支持单文件导入）。
- 当前支持格式：Library 支持 PDF/EPUB/HTML/Markdown/FB2/DOCX，Comic 支持目录封面提取与 CBZ，Text Novel 支持 TXT（含预览、规则导入、同名 sidecar 封面）。
- 外部打开：依赖系统默认关联程序。

## 6. 维护要求
- 每次 `src/` 结构变化后，必须更新本文件。
- 每次开发后，必须在 `Agent-rule/logs/history/YYYY-MM-DD.md` 追加留档。
- 文档保持“当前事实”，历史细节放 `logs/history`，不在本文件堆叠。
