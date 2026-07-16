# Indexer Contract

## Purpose
- 规范**当前实现**的目录扫描、资源识别与索引更新行为。
- 实现入口：`ScanWorker` → `scanner.scan_roots` / `scan_comic_roots` / `scan_text_roots` → `LibraryRepository`。

## Current Architecture (fact)
```text
scan_roots / comic_roots / text_roots
        → ScanWorker (QThread)
            → scan_roots        # PDF/EPUB；hash_strategy 指纹跳过
            → scan_comic_roots  # 叶子图片文件夹；folder_size_mtime 快照跳过
            → scan_text_roots   # TXT + 规则链
        → SQLite upsert / 失踪则删除
        → scan_report.json + Scan_error_logs
```

## Scan Semantics
- **遍历模式**：每次扫描对配置根目录做**全量遍历**。
- **局部跳过（非 checkpoint API）**：
  - Library：按 Settings `hash_strategy`（`size_mtime` / `quick` / `sha256`）比对已存指纹；未变且缩略图仍在则跳过元数据/封面。
  - Comic：按 `folder_size_mtime`（及封面指纹）判断文件夹是否未变。
  - Text：当前无等价指纹跳过（仍全量处理 TXT）。
- **非目标**：`last_checkpoint` / `next_checkpoint` 时间线检查点引擎；独立 `incremental_scan_engine` 模块（未实现，不作为交付承诺）。

## Logical Input (mapped to code)
```json
{
  "roots": ["library root paths"],
  "comic_roots": ["comic root paths"],
  "text_roots": [{"path": "string", "rules_json": "string"}],
  "scan_depth": "1-3 for library",
  "comic_max_depth": "1-5 (worker currently fixed at 5)",
  "hash_strategy": "size_mtime|quick|sha256",
  "scope": "all|library|comic|text",
  "trigger": "string"
}
```

## Logical Output (mapped to code)
- 持久化：`books` / `comics` 表 upsert；失踪源文件/文件夹 → 删除记录 + `append_scan_log`。
- 摘要：`ScanResult.to_summary()` → `scan_report.json` / `scan_events`。
- 「变更集」语义由 upsert（added/updated）与失踪删除体现，**不**单独输出 `resource_index_delta` JSON 数组。
- 指标字段示例：`scanned_files`、`comic_detected_folders`、`skipped_unchanged_count`、`removed_missing_*`。

## Guarantees
- 扫描错误进入 `ScanResult.errors` / `comic_errors` / `text_errors` 或错误日志，不静默吞掉关键失败。
- `comic_folder` 单元可追踪 `path`、`comic_root`、`cover_image_path`、`image_count`、`info_text`。
- 同名同扩展冲突（书籍/TXT）写入 `name_conflicts` 与错误日志。

## Error Shape (implementation)
```json
{
  "code": "string|null",
  "message": "string",
  "resource_path": "string|null"
}
```
（警告也可出现在 `ScanResult.warnings`，例如 PDF 后端不可用、漫画大图降采样。）
