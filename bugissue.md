# Bug / Issue 维护清单

更新时间：2026-07-31  
来源：只读代码审查（未改 `src/`；2026-07-31 复核当前代码并整合新发现，删除已完成 ISSUE-001/002/008，ISSUE-004/006/007 状态更新）

> 用途：给下一次维护 agent / 开发者一个可直接开工的待办列表。  
> 修复后请在本文件对应条目打勾，并在 `Agent-rule/logs/history/` 留档。

---

## 高优先级

### [x] BUG-1（安全）：CBZ 成员路径穿越（zip-slip，可任意写盘）

**位置**：`src/bookhub/library/formats/cbz.py` — `_safe_archive_member_path`（40-47 行）  
**现象**：Windows 上 `Path("/evil.jpg").is_absolute()` 返回 **False**（无盘符），parts 为 `('\\', 'evil.jpg')`，不含 `..`/空串，通过校验；随后 `cache_dir / member_path` 拼接结果逃逸缓存目录。  
**实测**：`cache / _safe_archive_member_path('/evil.jpg')` → `C:\evil.jpg`（驱动盘根目录）。  
**触发路径**：打开恶意 CBZ（`openResource` → `resolve_comic_open_path` → `prepare_cbz_for_external_viewer` → `_extract_cbz_members_to_cache`）→ **任意位置文件写入**。  
**修复方向**：拒绝含 `drive`/`root` 的成员（如 `member.startswith('/')` 或 `Path(member).drive` 非空），或在拼接后用 `resolve().relative_to(cache_dir)` 二次校验。

**状态（2026-07-31）**：已修 — `_safe_archive_member_path` 增加 `is_absolute() or drive or root` 前缀检查，拒绝 `/`、`\`、盘符前缀成员；新增直接单测与恶意 CBZ 端到端测试；全量回归 179 passed。

---

### [x] BUG-2（数据丢失）：删除根目录时 SQL LIKE 通配符误删兄弟目录

**位置**：`src/bookhub/library/repository.py` — `remove_root`（850/858/869）、`remove_comic_root`（910/917/927）、`remove_text_root`（969/977/988）  
**现象**：`root_prefix = normalized.rstrip("\\/") + os.sep + "%"`，`path LIKE ?` 未转义；Windows 目录名可合法包含 `%` / `_`（`%`/`_` 是 LIKE 通配符）。  
**实测**：移除根 `C:\books\100%_Special` 时，把兄弟目录 `C:\books\1000XSpecial` 下的书一并删除（本应只删 1 条，实际命中 2 条）。`normalize_path` 用 `resolve()` 返回反斜杠路径，与 `os.sep` 一致，真实可触发。  
**修复方向**：`LIKE ... ESCAPE '\'` 转义 `%`/`_`，或改用 `substr(path, 1, length(?)) = ?`（前缀比较，无通配符语义）。

**状态（2026-08-01）**：已修 — 三处 `path LIKE ?` 全部改为 `substr(path, 1, length(?)) = ?`（前缀精确比较，无通配符语义），`root_prefix` 不再追加 `%`；新增 3 个含 `%`/`_` 的 Library/Comic/Text 删除回归测试；旧 LIKE 命中 2 条、新 substr 只命中 1 条实测确认；全量回归 182 passed。

---

### [x] BUG-3（UI 残留）：搜索建议总是出现硬编码 "Bauhaus principles"

**位置**：`src/bookhub/ui/viewmodels/library_viewmodel.py`（77-86 行）`search_suggestions_for_query`  
**现象**：空查询也返回 `History / Bauhaus principles`，属遗留演示数据，会展示给所有用户。  
**修复方向**：删除该硬编码条目（或接入真实搜索历史）。

**状态（2026-08-01）**：已修 — `search_suggestions_for_query` 的 `suggestions` 初始化为空列表，删除硬编码 History/Bauhaus 条目；新增空查询回归测试；全量回归 183 passed。

---

## 中优先级

### [x] BUG-4（原 ISSUE-005）：超大漫画封面降采样失败仍复制原图

**位置**：`src/bookhub/library/scanner.py` — `_copy_or_downscale_comic_placeholder`（439-452 行）  
**现象**：`Image.open` 解码失败进入 `except` 分支时，`shutil.copy2` 直接复制原图到占位路径。  
**影响**：超大图仍可能进入 Qt 解码路径（项目已有 256MB 解码限制 warning）。  
**修复方向**：失败时写固定小占位图或仅标记待后台缩略图，勿在失败分支无条件 copy 原图。

**状态（2026-08-01）**：已修 — except 分支改为用 `Image.new` 生成 96x144 灰色固定占位 PNG（不依赖解码外部文件，损坏/超大源也能成功）；返回 `.png` 仍是 `variant=original`，快扫占位 + 后台补全架构不变；后台 regenerate 失败时 fallback 保留占位 URI。新增损坏封面占位安全 + regenerate fallback 两个测试；全量回归 185 passed。

---

### [ ] BUG-5（原 ISSUE-004 演进）：Library 扫描进度恒 100%

**位置**：`src/bookhub/library/scanner.py` — `scan_roots`（`total_files = 0`）+ `_emit_scan_progress`（`max(current, total)`）  
**现状**：旧 ISSUE-004 的 `_count_library_scan_files` 预扫描已移除（避免大目录预遍历），但 `total` 恒为 0，`max(current, 0)` 使进度从一开始就满格。  
**影响**：用户无法感知扫描进度，易误以为卡住/无反馈。  
**修复方向**：改为不定进度（busy 态）或按根/按目录实时累计并设上限，或前端进度条改为「处理中」动画。

---

### [ ] BUG-6：`apply_setting` 对整型设置直接 `int(value)` 无容错

**位置**：`src/bookhub/ui/web_window.py` — `apply_setting`（177/200/205/208/210 行：`scanDepth`/`textPreviewChars`/`comicPageSize`/`viewportBufferScreens`/`gridColumns`）  
**现象**：直接 `int(value)`，同文件其他设置均用 normalize 容错；前端传入异常值会抛 `ValueError`，中断整个 Qt slot 设置批次。  
**修复方向**：与 `searchFontSize`/`cardSpacing` 一致，改用 normalize 函数或 try/except 回退默认值。

---

### [ ] BUG-7（原 ISSUE-003）：多线程并发写库无 WAL

**位置**：`src/bookhub/library/repository.py` — `_connection`（194-203 行）  
**现状**：已有 `PRAGMA foreign_keys = ON` + `busy_timeout = 5000`，但未开 WAL；`ScanWorker`/`ThumbnailTaskWorker` 各自新建 Repository（含 DDL），与主线程 UI 并发写同一 `library.db`。  
**影响**：大批量扫描/缩略图重建时仍可能偶发 `database is locked`。  
**修复方向**：评估 `PRAGMA journal_mode = WAL`（桌面单用户通常合适），缩略图任务 DB 更新尽量批量或单连接串行。

---

### [ ] BUG-8：CBZ 读取缓存目录永不清理（磁盘泄漏）

**位置**：`src/bookhub/library/formats/cbz.py` — `_cbz_read_cache_dir`（49-55 行）  
**现象**：token 含 `st_mtime_ns`，CBZ 每改动一次生成新的 `preview/comic/read/<token>` 目录，旧目录只在本 token 重提取时清理，历史 token 目录**永不清理**。  
**影响**：经常更新的 CBZ 会在 `img_preview/comic/read/` 累积大量解压副本，磁盘膨胀。  
**修复方向**：清理 `read/` 下非当前 token 的过期目录（如保留最近 N 个 / 按 mtime 清理）。

---

## 低优先级 / 产品取舍

### [ ] 低-1：`web_bridge._comic_page_payload` 死代码

**位置**：`src/bookhub/ui/web_bridge.py`（517 行）  
**说明**：`_comic_page_payload`（rows 版本）定义后从未被调用，实际使用 `_comic_page_payload_from_items`。删除即可。

---

### [ ] 低-2：漫画右键菜单切换收藏后详情面板不刷新

**位置**：`src/bookhub/ui/web/js/app.js`（788/802 行）  
**说明**：右键菜单 `toggleFavorite(page, item.id, () => {})` 空回调；顶部收藏按钮（717 行）有 `refreshDetailIfSelected()`，右键路径缺失。收藏态在详情面板可能不同步。

---

### [ ] 低-3：`saveTextRules` 扫描被拒时 `scanned` 仍返回 True

**位置**：`src/bookhub/ui/web_bridge.py`（1117-1120 行）  
**说明**：`start_scan("text")` 触发后无条件 `scanned = True`，即使宿主因忙碌拒绝扫描（UI 已禁用按钮）也置真，前端 Toast 文案可能误导。

---

### [ ] 低-4：`mountVirtualCoverGrid` 的 `lastKey` 缓存可能显示过期卡片

**位置**：`src/bookhub/ui/web/js/app.js`（454/465、571/580 行附近）  
**说明**：条目数变化但可视行几何不变时，`lastKey` 相同会跳过 DOM 重建，短期内可能显示过期条目。属极小概率视觉残留。

---

### [ ] 低-5：`_find_book_row` 对全部 books 做 Python 全表扫描

**位置**：`src/bookhub/ui/web_bridge.py`（743-747 行）  
**说明**：`getDetail`/`openFolder` 每次遍历 `list_books` 全量匹配 `resource_id`；书库量级大时变慢。可改为 SQL 按 `resource_id` 直查。

---

### [ ] ISSUE-006（部分解决）：Library/Text 重名冲突仍无策略

**说明**：Comic 已支持 `comic_title_conflict_policy`（skip_incoming / keep_both / prefer_newer，Settings 下拉）；Library/Text 仍为「同名同扩展名跳过 + 冲突日志」。如需为 Library/Text 也提供策略，参考 Comic 实现。

---

### [~] ISSUE-007（已过时）：旧 Widgets UI 静默失败已随清理消失

**说明**：2026-07-14 清理旧 Widgets UI 后，原 `comic_page.py`/`library_page.py` 等已不存在；新 UI `web_bridge._open_external`（782-783 行）失败时已有 Toast 提示。无需再处理。

---

## 已确认无问题 / 不必改

- PDF PyMuPDF 降级 + 聚合 warning（`scan_roots` + `_probe_pdf_backend`）
- 陈旧 duplicate 路径清理（`_cleanup_stale_duplicate_if_needed`）
- 漫画叶子目录识别，避免父子重复入库
- 扫描与缩略图任务互斥（`web_window` 忙时禁用相关按钮 + Toast）— 有意设计
- Text 规则链回退与非法正则容错（`src/tests/` 有覆盖）
- `PRAGMA foreign_keys = ON` + `busy_timeout = 5000`（2026-07-11 已加）
- 外部打开失败有 Toast（对应旧 ISSUE-007，已随新 UI 解决）

---

## 建议维护顺序

1. BUG-1（安全 zip-slip，CBZ 恶意写入）→ 已修（2026-07-31）
2. BUG-2（数据丢失，LIKE 通配符误删兄弟目录）→ 已修（2026-08-01）
3. BUG-3（UI 残留硬编码建议）→ 已修（2026-08-01）
4. BUG-6、BUG-7（健壮性，repository/web_window 同文件可一起）
5. BUG-8、BUG-5（磁盘泄漏 / 扫描进度体验）
6. BUG-4（超大封面降采样容错）→ 已修（2026-08-01）
7. 低-1～低-5 与 ISSUE-006 视产品需求

---

## 相关文档

- 功能说明：[`README.md`](README.md)
- 结构说明：[`src_construction.md`](src_construction.md)
- 开发留档：`Agent-rule/logs/history/`
