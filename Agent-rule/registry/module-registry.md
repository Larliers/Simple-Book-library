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
