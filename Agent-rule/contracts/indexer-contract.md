# Indexer Contract

## Purpose
- 规范**当前实现**的目录扫描、资源识别与索引更新行为。
- 实现入口：`ScanWorker` → `scanner.scan_roots` / `scan_comic_roots` / `scan_text_roots` → `LibraryRepository`。

## Current Architecture (fact)
```text
scan_roots / comic_roots / text_roots
        → ScanWorker (QThread)
            → scan_roots        # PDF/EPUB；hash_strategy 指纹跳过
            → scan_comic_roots  # 叶子图片文件夹；folder_size_mtime 快照跳过；同 comic_root 标题冲突按策略
            → scan_text_roots   # TXT + 规则链；同 hash_strategy 指纹跳过；text_encoding_preference 读入
        → SQLite upsert / 失踪则删除
        → scan_report.json + Scan_error_logs
```

## Scan Semantics
- **遍历模式**：每次扫描对配置根目录做**全量遍历**。
- **局部跳过（非 checkpoint API）**：
  - Library：按有效 `hash_strategy`（`size_mtime` / `quick` / `sha256`）比对已存指纹；未变且缩略图仍在则跳过元数据/封面。
  - Comic：默认按 Settings `comic_scan_strategy`=`snapshot` 用 `folder_size_mtime`（及封面指纹）判断文件夹是否未变；`full` 禁用 `folder_size_mtime` 短路并**重读旁注 TXT**；同一 `comic_root` 下同标题（叶子文件夹名）冲突按 `comic_title_conflict_policy` 处理；旁注 TXT 经 `text_encoding` 按偏好读入。
  - Text：按与 Library 相同的有效 `hash_strategy` 比对已存指纹；未变则跳过规则链与 upsert（无缩略图要求）；TXT 正文经 `text_encoding` 按偏好读入。
- **目录级策略覆盖**（Settings `per_root_scan_strategy_enabled`，默认关）：
  - **关**：Library/Text 统一用全局 `hash_strategy`；Comic 统一用全局 `comic_scan_strategy`；各根表 `scan_strategy` 列仍持久化覆盖值但不生效。
  - **开**：`library_roots` / `comic_roots` / `text_roots` 可空列 `scan_strategy`；`NULL` 或空串 = 继承对应全局策略。
  - Library/Text 覆盖值：`size_mtime` | `quick` | `sha256`（非法值回退全局）。
  - Comic 覆盖值：`snapshot` | `full`（非法值回退全局）。
  - 解析入口：`models.resolve_library_hash_strategy` / `models.resolve_comic_scan_strategy`；`scanner` 按根调用。
- **文本编码偏好**（Settings `text_encoding_preference`，默认 `simplified`）：
  - `simplified`：简体优先；normalizer 排名偏向 GB 族，**从不**选用 Big5 族。
  - `traditional`：繁体优先；Big5 族可胜出。
  - `auto`：不偏简繁，按 normalizer 置信/混乱度择优；低置信时 GB18030↔UTF-8 双候选回退。
  - 探测样本前 64KB；规则预览 diag 可带 `detectedEncoding` / `encodingConfidence`。
- **漫画同名冲突策略**（Settings `comic_title_conflict_policy`，默认 `skip_incoming`）：
  - `keep_both`：同标题不同路径都入库；仍记冲突日志/摘要。
  - `skip_incoming`：已存在同 `comic_root`+`title` → 跳过新人，记 `name_conflicts` + 错误日志。
  - `prefer_newer`：比较文件夹 mtime，保留较新者（可删旧 path 记录）。
- **非目标**：`last_checkpoint` / `next_checkpoint` 时间线检查点引擎；独立 `incremental_scan_engine` 模块（未实现，不作为交付承诺）。

## Logical Input (mapped to code)
```json
{
  "roots": [{"path": "string", "scan_strategy": "size_mtime|quick|sha256|null"}],
  "comic_roots": [{"path": "string", "scan_strategy": "snapshot|full|null"}],
  "text_roots": [{"path": "string", "rules_json": "string", "scan_strategy": "size_mtime|quick|sha256|null"}],
  "scan_depth": "1-3 for library",
  "comic_max_depth": "1-5 (worker currently fixed at 5)",
  "hash_strategy": "size_mtime|quick|sha256 (default: quick)",
  "comic_scan_strategy": "snapshot|full (default: snapshot)",
  "per_root_scan_strategy_enabled": "boolean (default: false)",
  "text_encoding_preference": "simplified|traditional|auto",
  "comic_title_conflict_policy": "keep_both|skip_incoming|prefer_newer",
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
- 漫画同 `comic_root` 同标题冲突按 `comic_title_conflict_policy` 分支，并写入 `name_conflicts` / 错误日志（跨根目录允许同名）。

## Error Shape (implementation)
```json
{
  "code": "string|null",
  "message": "string",
  "resource_path": "string|null"
}
```
（警告也可出现在 `ScanResult.warnings`，例如 PDF 后端不可用、漫画大图降采样。）
