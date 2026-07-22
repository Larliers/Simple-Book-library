# Module Registry

## 模块登记规范
- 每个模块必须登记且字段完整。
- 字段名固定，不允许自定义同义字段。
- 变更模块状态时必须同步记录到 `logs/worklog.md` 与 `logs/decision-log.md`。

## 字段模板
```json
{
  "module_name": "string",
  "owner_agent": "string",
  "status": "planned|active|deprecated",
  "purpose": "string",
  "input": ["string"],
  "output": ["string"],
  "upstream": ["string"],
  "downstream": ["string"],
  "notes": "string"
}
```

## 格式模块（2026-07-18）

### library_format_extractors
```json
{
  "module_name": "library_format_extractors",
  "owner_agent": "indexer-agent",
  "status": "active",
  "purpose": "Library 新格式元数据与封面提取（html/md/fb2/docx）",
  "input": ["file_path", "extension"],
  "output": ["ParsedMetadata", "thumbnail_file_uri"],
  "upstream": ["scanner.scan_roots"],
  "downstream": ["LibraryRepository.upsert_book", "thumbnail_tasks"],
  "notes": "formats/registry.py 为后缀、元数据提取与缩略图生成的唯一注册入口（延迟导入）；HTML 不做浏览器整页渲染；依赖 python-docx==1.1.2 / lxml==6.1.1"
}
```

### comic_cbz_scanner
```json
{
  "module_name": "comic_cbz_scanner",
  "owner_agent": "indexer-agent",
  "status": "active",
  "purpose": "在 comic root 内识别 CBZ 归档为一本漫画并生成封面占位",
  "input": ["comic_roots", "comic_scan_strategy", "title_conflict_policy"],
  "output": ["comic upsert payload", "scan_metrics"],
  "upstream": ["ScanWorker"],
  "downstream": ["LibraryRepository.upsert_comic", "thumbnail_generator"],
  "notes": "path 为 CBZ 文件；cover_image_path 形如 path::member；CBR 非目标"
}
```

## 初始模块示例

### comic_folder_scanner
```json
{
  "module_name": "comic_folder_scanner",
  "owner_agent": "indexer-agent",
  "status": "active",
  "purpose": "扫描漫画目录并识别目录型资源单元",
  "input": ["scan_roots", "scan_mode", "last_checkpoint"],
  "output": ["resource_index_delta", "scan_metrics"],
  "upstream": ["master-agent"],
  "downstream": ["filename_parser", "thumbnail_generator", "resource_list_view"],
  "notes": "优先增量扫描，避免全量重复遍历"
}
```

### filename_parser
```json
{
  "module_name": "filename_parser",
  "owner_agent": "parser-agent",
  "status": "active",
  "purpose": "解析文件名与目录名并提取结构化元数据",
  "input": ["records", "ruleset"],
  "output": ["parsed_records", "unresolved_records", "ruleset_version"],
  "upstream": ["comic_folder_scanner"],
  "downstream": ["resource_list_view"],
  "notes": "规则配置化，支持不同命名风格"
}
```

### thumbnail_generator
```json
{
  "module_name": "thumbnail_generator",
  "owner_agent": "thumbnail-agent",
  "status": "active",
  "purpose": "生成并缓存资源缩略图",
  "input": ["resources", "thumbnail_profile", "generation_mode"],
  "output": ["thumbnails", "deferred_queue", "metrics"],
  "upstream": ["comic_folder_scanner"],
  "downstream": ["resource_list_view", "resource_waterfall_view"],
  "notes": "采用延迟生成策略保障首屏响应"
}
```

### resource_list_view
```json
{
  "module_name": "resource_list_view",
  "owner_agent": "ui-agent",
  "status": "active",
  "purpose": "渲染资源列表并提供筛选排序交互",
  "input": ["resources", "ui_state", "view_mode"],
  "output": ["render_plan", "interaction_events"],
  "upstream": ["filename_parser", "thumbnail_generator"],
  "downstream": ["external_open_action"],
  "notes": "UI 仅消费数据，不执行扫描"
}
```

### comic_cover_selector
```json
{
  "module_name": "comic_cover_selector",
  "owner_agent": "thumbnail-agent",
  "status": "active",
  "purpose": "按自然序选择漫画目录首图并生成缩略图缓存",
  "input": ["comic_folder_path", "image_extensions", "thumbnail_profile"],
  "output": ["cover_image_path", "thumbnail_path", "cache_key"],
  "upstream": ["comic_folder_scanner"],
  "downstream": ["comic_sidebar_binding"],
  "notes": "支持 jpg/png/webp/jpeg；双击打开封面图依赖 cover_image_path"
}
```

### comic_sidebar_binding
```json
{
  "module_name": "comic_sidebar_binding",
  "owner_agent": "ui-agent",
  "status": "active",
  "purpose": "在 Comic/Comic Fav 页面渲染 grid，并把同级 txt 文本绑定到右侧详情栏",
  "input": ["comic_resources", "selected_resource", "view_mode=comic_grid"],
  "output": ["render_plan", "interaction_events", "detail_sidebar_text"],
  "upstream": ["comic_folder_scanner", "comic_cover_selector"],
  "downstream": ["external_open_action"],
  "notes": "页面仅 grid，无 list；文本区位于详情缩略图下方"
}
```
