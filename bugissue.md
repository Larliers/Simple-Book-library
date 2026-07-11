# Bug / Issue 维护清单

更新时间：2026-06-23  
来源：只读代码审查（Karpathy Guidelines 风格，未改 `src/`）

> 用途：给下一次维护 agent / 开发者一个可直接开工的待办列表。  
> 修复后请在本文件对应条目打勾，并在 `Agent-rule/logs/history/` 留档。

---

## 高优先级

### [ ] ISSUE-001：SQLite 外键未启用，漫画收藏孤儿行

**位置**：`src/bookhub/library/repository.py`  
**现象**：
- 连接未执行 `PRAGMA foreign_keys = ON`
- `favorite_comics` 虽声明 `ON DELETE CASCADE`，实际不生效
- `remove_comic_root`、`delete_comics_by_ids` 只删 `comics`，不清理 `favorite_comics`

**影响**：漫画被扫描清理或移除根目录后，`favorite_comics` 残留孤儿行；UI 因 `INNER JOIN` 暂不可见，但 DB 膨胀、长期数据不一致。

**建议修复**：
1. 在 `_connection()` 上下文内连接后执行 `PRAGMA foreign_keys = ON`（及可选 `PRAGMA busy_timeout = ...`）
2. 或在删除 comic 时显式 `DELETE FROM favorite_comics WHERE comic_id IN (...)`
3. 一次性迁移脚本清理已有孤儿行

**验收**：
- 删除 comic 后 `favorite_comics` 无对应 `comic_id`
- 现有收藏列表行为不变

---

### [ ] ISSUE-002：书籍删除未清理收藏 / 书单关联

**位置**：`src/bookhub/library/repository.py`  
**涉及方法**：`delete_books_by_ids`、`remove_root`（及扫描侧 `_remove_missing_books_in_scope` 间接调用）

**现象**：
- 删 `books` 时不删 `favorite_books`、`collection_books`
- `collection_books` / `favorite_books` 无指向 `books` 的外键

**影响**：孤儿关联行累积；书单计数、收藏统计长期可能偏差（若未来查询方式变化会暴露）。

**建议修复**：
1. 删除 book 前/后清理 `favorite_books`、`collection_books` 中对应 `book_id`
2. 或补 FK + 启用 foreign_keys（与 ISSUE-001 一并做）
3. 迁移清理历史脏数据

**验收**：
- 删书 / 移除 Library 根 / 扫描缺失清理后，关联表无悬空 `book_id`

---

## 中优先级

### [ ] ISSUE-003：多线程并发写库缺 busy 超时 / WAL

**位置**：`src/bookhub/library/repository.py`；调用方 `worker.py`、`thumbnail_worker.py`、`app_window.py`

**现象**：主线程 UI 与 `ScanWorker`、`ThumbnailTaskWorker` 共用 `library.db`；漫画缩略图 `ThreadPoolExecutor` 并行渲染后串行写库，与 UI 交错。

**影响**：大批量扫描或缩略图重建时，偶发 `database is locked` 或 UI 短暂卡顿。

**建议修复**：
- `PRAGMA busy_timeout = 5000`（或可调）
- 评估 `PRAGMA journal_mode = WAL`（桌面单用户场景通常合适）
- 缩略图任务 DB 更新尽量批量或单连接串行

**验收**：压测扫描 + 缩略图 + 频繁刷新 Settings/列表，无 lock 弹窗

---

### [ ] ISSUE-004：Library 扫描进度条 total 统计偏大

**位置**：`src/bookhub/library/scanner.py` — `_count_library_scan_files` vs `scan_roots` 实际处理范围

**现象**：`total` 统计目录下**所有文件**，实际只入库 PDF/EPUB。

**影响**：进度条长期低于 100%，易误解为扫描卡住。

**建议修复**：`_count_library_scan_files` 仅统计 `SUPPORTED_EXTENSIONS` 内文件，或与 `scan_roots` 共用同一过滤逻辑。

**验收**：纯 PDF/EPUB 目录扫描时进度可达 100%

---

### [ ] ISSUE-005：超大漫画封面降采样失败仍复制原图

**位置**：`src/bookhub/library/scanner.py` — `_copy_or_downscale_comic_placeholder`

**现象**：`Image.open` 失败时 `except` 分支 `shutil.copy2` 原图到占位路径。

**影响**：超大图仍可能进入 Qt 解码路径，存在内存暴涨或解码失败风险（项目已有 256MB 限制相关 warning）。

**建议修复**：
- 失败时写固定小占位图或跳过占位、仅标记待后台缩略图
- 勿在失败分支无条件 copy 原图

**验收**：对已知超大封面样本，占位阶段不产生全尺寸原图 URI

---

## 低优先级 / 产品取舍

### [ ] ISSUE-006：重名冲突仅跳过，无合并或用户选择

**位置**：`src/bookhub/library/scanner.py` + `find_duplicate_name`

**说明**：同名同扩展名、不同路径 → 跳过并记 conflict 日志。属当前设计，但用户可能不知如何解决。

**可选**：Settings / 冲突日志增加「保留哪条路径」或「允许同名不同路径」策略。

---

### [ ] ISSUE-007：UI 层宽泛 `except Exception` 静默失败

**位置**：`comic_page.py`、`library_page.py`、`collections_page.py`、`book_card.py` 等

**说明**：如 `_open_external` 失败无 Toast，需查 Error logs 或自行猜。

**可选**：关键路径改用 `SlideToast` 或 `QMessageBox` 提示一次。

---

### [ ] ISSUE-008：开发环境 pytest 未入 requirements

**位置**：`requirements.txt`

**说明**：README 写 `pip install pytest` 单独装；CI/本地回归易遗漏。

**可选**：增加 `requirements-dev.txt` 或 `[dev]` 可选依赖。

---

## 已确认无问题 / 不必改

- PDF PyMuPDF 降级 + 聚合 warning（`scan_roots` + `_probe_pdf_backend`）
- 陈旧 duplicate 路径清理（`_cleanup_stale_duplicate_if_needed`）
- 漫画叶子目录识别，避免父子重复入库
- 扫描与缩略图任务互斥（`app_window._start_scan` / `_start_thumbnail_task`）— 有意设计
- Text 规则链回退与非法正则容错（`src/tests/` 有覆盖）

---

## 建议维护顺序

1. ISSUE-001 + ISSUE-002（数据一致性，改动集中 `repository.py`）
2. ISSUE-003（与 1 同文件，可一次 PR）
3. ISSUE-004、ISSUE-005（扫描体验与稳定性）
4. ISSUE-006～008 视产品需求

---

## 相关文档

- 功能说明：[`README.md`](README.md)
- 结构说明：[`src_construction.md`](src_construction.md)
- 开发留档：`Agent-rule/logs/history/`
