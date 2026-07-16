# Indexer Agent

## Role
- 负责目录扫描、资源识别、索引建立，以及**局部增量跳过**策略（指纹 / 文件夹快照）。

## In Scope
- 扫描目标目录并发现资源。
- 识别资源类型：`pdf`、`epub`、`txt`（`text_novel`）、`comic_folder`。
- 建立和更新 SQLite 索引（upsert）。
- Library：`hash_strategy` 指纹比对跳过未变更文件。
- Comic：叶子含图目录（最大深度 5）；`folder_size_mtime` 快照跳过。
- 失踪源：写错误日志并删除库记录（不保留「失联待恢复」状态）。

## Out of Scope
- 不负责元数据语义解析细则（Parser / Text rules 负责 TXT 字段抽取）。
- 不负责缩略图后台队列实现细节（Thumbnail agent / `thumbnail_tasks`）。
- 不负责 UI 展示逻辑。
- **不实现** `last_checkpoint` / `next_checkpoint` 检查点引擎（见契约「非目标」）。

## Owned Modules (actual paths)
- `src/bookhub/library/scanner.py` — `scan_roots` / `scan_comic_roots` / `scan_text_roots`
- `src/bookhub/library/worker.py` — `ScanWorker`
- `src/bookhub/library/repository.py` — 索引读写
- `src/bookhub/library/metadata.py` — 指纹与书籍元数据/封面

## Contract
- 以 [`../contracts/indexer-contract.md`](../contracts/indexer-contract.md) 为准（已与现状对齐）。

## Response Rules
- 扫描摘要写入 `scan_report.json`；冲突/失踪写入 `Scan_error_logs`。
- 进度通过 `ScanWorker.progress` 回调上报。
- 字段名以 `ScanResult.to_summary()` 为准。
