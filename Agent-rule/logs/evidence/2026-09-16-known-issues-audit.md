# 2026-09-16 本地遗留 Issue 全量核验证据

## 边界

- 基线：`main` / `b17a34b8a5e0d6ad0a2ac0480636af36c69d25af`，包含审计开始前的未提交改动。
- 只诊断与整理；不修复运行时代码、不改 schema/Bridge API/测试、不提交、不 push。
- 所有动态复现使用临时数据库、缓存和虚构资源；没有读取或写入真实书库。
- 本文不记录真实书库绝对路径、私人书名或用户数据。

## 候选来源

- 根目录 `bugissue.md` 的所有既有编号，包括已勾选项。
- `Agent-rule/logs/` 的 `risks`、`followups`、`next_actions` 和 Text Rules 白屏交接。
- Settings 旧规格、开发总览、`pytest_out*.txt`、`nuitka-crash-report.xml`。
- `src/` 的 TODO/FIXME 与未使用函数/宽泛刷新路径。
- 旧运行日志仅用于提出候选，不作为缺陷结论。

## 自动测试

### 审计前基线

```text
python -m pytest -q
270 passed, 43 subtests passed

node src/tests/js/quick_add.behavior.test.js src/bookhub/ui/web/js/app.js
QUICK_ADD_BEHAVIOR_OK

node src/tests/js/random_recommendations.behavior.test.js src/bookhub/ui/web/js/app.js
RANDOM_RECOMMENDATIONS_BEHAVIOR_OK

node src/tests/js/shortcuts.behavior.test.js src/bookhub/ui/web/js/app.js
SHORTCUTS_BEHAVIOR_OK

node src/tests/js/tag_management.behavior.test.js src/bookhub/ui/web/js/app.js
TAG_MANAGEMENT_BEHAVIOR_OK
```

### 安全、扫描和 Bridge 定向回归

```text
python -m pytest -q \
  src/tests/test_new_formats_import.py \
  src/tests/test_repository_orphan_cleanup.py \
  src/tests/test_library_viewmodel_search.py \
  src/tests/test_comic_preview_pipeline.py \
  src/tests/test_scan_pdf_degrade.py \
  src/tests/test_web_bridge_smoke.py

95 passed, 6 subtests passed in 16.31s
```

## 最小运行时复现

审计期临时 fixture 在完成后删除；以下步骤均可用同等临时对象复现。

| 项目 | 输入/负载 | 结果 |
|---|---|---|
| BUG-1 | `/evil.jpg`、`\\evil.jpg`、`C:\\evil.jpg`、`../evil.jpg`、安全成员 | 四个危险成员均拒绝，安全成员接受；当前不存在。 |
| BUG-4 | 无法解码的封面字节 | 生成 PNG 96×144 占位图；当前不存在。 |
| BUG-5 | Library 扫描进度事件 | `total=0` 原样传递，前端可进入 busy；当前不存在。 |
| BUG-6 | 真实 `WebAppWindow.apply_setting` 路径，值为 `abc` | `scanDepth`、`textPreviewChars` 接受；`comicPageSize`、`viewportBufferScreens`、`gridColumns` 抛 `ValueError`。 |
| BUG-7 | SQLite 8 线程 × 40 独立写入 | `journal_mode=delete`；320 次写入、0 错误、约 1.7 秒。只证明 WAL 缺失，不证明当前负载必然锁库。 |
| BUG-8 | 同一路径 CBZ 两次改写并读取 | 产生 2 个 token 目录，旧目录仍存在。 |
| 低-3 | 自动扫描开启 + BusyHost 拒绝任务 | 返回 `{ok:true, scanned:true}`，与实际未启动不符。 |
| 低-5 | 20,000 行、查尾部资源 100 次 | 约 0.115 秒，稳定执行全量物化和线性扫描。 |
| OPT-1 | 标签添加、合集创建/重命名/删除 | 四项各发出 1 次完整 `resourcesChanged`。 |

## GUI 隔离核验

启动方式：mock 注入临时 Repository，离屏加载当前 WebEngine 源码；资源为 140 条虚构 Text Novel、45 条虚构 Text Rules。记录 `renderGen`、`scrollTop`、容器尺寸、DOM 数量与字体状态。

| 皮肤/视口 | Text Novel | Text Rules | 字体 |
|---|---|---|---|
| Glass 1440×860 | 内部滚动成立；`scrollTop=500`；`renderGen=2`；50 个可见卡片 | 第一栏 260 → 260，连续 20 次 `renderTrBody()` 后未丢失；overlay 存在 | 不作为 Glass 判定 |
| Glass 749×860 | 内部滚动成立 | 260 → 260；无白屏 | 不作为 Glass 判定 |
| Vaporwave 600×749 | 高 186、`scrollHeight=70520`、500 可达；宽 316=`scrollWidth`；body 600=`bodyScrollWidth` | 第一栏 260 → 260；高 535；overlay 存在 | Sora=false，Space Mono=false |
| Vaporwave 390×844 | 高 236、`scrollHeight=26351`、500 可达；宽 106=`scrollWidth`；body 390=`bodyScrollWidth` | 第一栏 260 → 260；高 582；overlay 存在 | Sora=false，Space Mono=false |

结论：Text Rules 快速滚动白屏和 Vaporwave 600px 无内部滚动在当前源码均未复现；横向溢出也未出现。字体失败稳定复现，且与 `fonts.css` 相对路径计算一致。

截图：

- `C:\Users\83023\.codex\visualizations\2026\09\15\01a0a500-9fd0-7f70-af5e-e0d509bb66d9\audit-glass-1440.png`
- `C:\Users\83023\.codex\visualizations\2026\09\15\01a0a500-9fd0-7f70-af5e-e0d509bb66d9\audit-glass-749.png`
- `C:\Users\83023\.codex\visualizations\2026\09\15\01a0a500-9fd0-7f70-af5e-e0d509bb66d9\audit-vaporwave-600.png`
- `C:\Users\83023\.codex\visualizations\2026\09\15\01a0a500-9fd0-7f70-af5e-e0d509bb66d9\audit-vaporwave-390.png`

## 静态因果证据

- BUG-6：`web_window.py` 三处残留 `int(value)`，Repository 的容错尚未执行。
- BUG-8：缓存 token 含 `st_mtime_ns`，无按源或全局的旧 token 清理。
- BUG-9：`css/skins/vaporwave/fonts.css` 的 `../../fonts/` 解析到 `css/fonts/`，实际字体在 `web/fonts/`。
- 低-1：`_comic_page_payload` 只有定义，入站调用为 0。
- 低-3：`start_scan()` 返回 `None`，Bridge 调用后无条件 `scanned=True`。
- 低-4：虚拟网格 `lastKey` 只含几何范围，不含条目身份或数据版本。
- 低-5：`_find_book_row` 每次调用 `list_books()` 并 Python 线性遍历。
- OPT-1：标签/合集 CRUD 调用 `push_resources()`，payload 含完整 pages。
- OPT-2：范围切换 callback 与 `settingsChanged` 都负责失效和加载；`tagLoading` 是共享布尔锁。
- OPT-3：添加根目录路径固定发送 `tag_catalog_invalidated=True`，与是否扫描出资源无关。

## 历史产物结论

- `pytest_out.txt` 的依赖缺失被后续输出和当前 270 项测试覆盖，归档为历史过时。
- `nuitka-crash-report.xml` 属旧打包内存失败；本轮不执行高成本打包，状态为无法验证。
- 旧开发总览的“尚未实现”与当前源码/测试明显冲突，归档为历史过时。
- Settings 中“启动最小化”是产品候选；“统一管理复制”与当前原路径扫描架构不是同一小功能。

## 最终门禁

- `python -m pytest -q`：`270 passed, 43 subtests passed in 36.13s`。
- `node src/tests/js/test_quick_add.js .../app.js`：`QUICK_ADD_BEHAVIOR_OK`。
- `node src/tests/js/test_random_recommendations.js .../app.js`：`RANDOM_RECOMMENDATIONS_BEHAVIOR_OK`。
- `node src/tests/js/test_shortcuts.js .../app.js`：`SHORTCUTS_BEHAVIOR_OK`。
- `node src/tests/js/test_tag_management.js .../app.js`：`TAG_MANAGEMENT_BEHAVIOR_OK`。
- `node --check`：`app.js`、`text_rules.js` 均通过。
- `git diff --check`：通过（仅有 Git 的 CRLF 转换提示，无 whitespace error）。
- 审计临时 Python fixture 已删除；工作树相较审计前只新增/修改本轮授权的清单、证据、history、worklog 和结构说明，未新增运行时代码或测试改动。
