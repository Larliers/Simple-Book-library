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

### text_novel_sidecar_cover
```json
{
  "module_name": "text_novel_sidecar_cover",
  "owner_agent": "thumbnail-agent",
  "status": "active",
  "purpose": "为 Text Novel 选择同 stem 图片、生成 WebP 缓存、独立跟踪封面变化，并支持设置页清空或重建",
  "input": ["txt_path", "existing_cover_source", "existing_cover_fingerprint", "preview_root", "thumbnail_task_kind"],
  "output": ["thumbnail_path", "cover_source", "cover_fingerprint", "scan_warning", "thumbnail_task_result"],
  "upstream": ["scanner.scan_text_roots", "ThumbnailTaskWorker"],
  "downstream": ["LibraryRepository.upsert_book", "resource_list_view", "settings_thumbnail_tasks"],
  "notes": "ScanWorker 后台执行；webp/png/jpg/jpeg 优先；manual 且文件有效时优先；sidecar 缓存不超过 360x540；cleanup 只删受控缓存并清状态，regenerate 保留有效 manual"
}
```

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
  "notes": "Library/Comic 采用延迟生成策略保障首屏响应；Text Novel 同名封面由 ScanWorker 后台扫描阶段生成"
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
  "notes": "UI 仅消费数据，不执行扫描；Text Novel 独立持久化 Grid/List，Grid 虚拟化且显示封面与标题，List 不显示封面列"
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

### random_recommendations_view
```json
{
  "module_name": "random_recommendations_view",
  "owner_agent": "ui-agent",
  "status": "active",
  "purpose": "按图书、文本小说、漫画三个来源随机展示封面推荐，并复用来源对应的详情交互",
  "input": ["library_resources", "text_novel_resources", "comic_resources", "recommendation_density_settings"],
  "output": ["recommendation_columns_with_source_page", "responsive_inner_grid", "resources_changed_payload", "render_plan", "interaction_events"],
  "upstream": ["filename_parser", "thumbnail_generator", "comic_cover_selector"],
  "downstream": ["resource_detail_binding", "external_open_action"],
  "notes": "三类固定顺序；每类数量 3/6/9/12（默认 6），内部最大列数 1/2/3（默认 2）并随容器宽度降级；结果不重复，UI 仅缓存会话结果"
}
```

### tag_management_view
```json
{
  "module_name": "tag_management_view",
  "owner_agent": "ui-agent",
  "status": "active",
  "purpose": "按中文拼音与英文字母分组展示标签目录，并在标签详情中以统一网格展示三类关联资源",
  "input": ["library_tags", "text_novel_tags", "comic_tags", "tag_manager_scopes", "tag_order", "tag_request_id"],
  "output": ["tag_index", "tag_detail", "mixed_resources_with_source_page", "interaction_events"],
  "upstream": ["LibraryRepository", "UiBridge", "filename_parser", "comic_folder_scanner"],
  "downstream": ["resource_detail_binding", "external_open_action", "shortcut_action_dispatcher"],
  "notes": "侧边栏位于随机推荐之后；A→Z/Z→A 仅会话保存，# 始终置尾；只统计所选范围内未缺失资源；请求以 request id 丢弃旧响应；Glass/Vaporwave 共用结构并支持键盘与窄屏"
}
```

### comic_sidebar_binding
```json
{
  "module_name": "comic_sidebar_binding",
  "owner_agent": "ui-agent",
  "status": "active",
  "purpose": "在 Comic 与漫画合集详情页面渲染 grid，并把同级 txt 文本绑定到右侧详情栏",
  "input": ["comic_resources", "selected_resource", "view_mode=comic_grid"],
  "output": ["render_plan", "interaction_events", "detail_sidebar_text"],
  "upstream": ["comic_folder_scanner", "comic_cover_selector"],
  "downstream": ["external_open_action"],
  "notes": "页面仅 grid，无 list；文本区位于详情缩略图下方"
}
```

### shortcut_action_dispatcher
```json
{
  "module_name": "shortcut_action_dispatcher",
  "owner_agent": "ui-agent",
  "status": "active",
  "purpose": "把右键菜单、键盘快捷键、页面侧键与原生/Windows 侧键消息统一路由到带真实资源上下文的动作入口",
  "input": ["shortcut_bindings", "keyboard_event_code", "page_mouse_side_input", "native_mouse_side_input", "win_xbutton_appcommand", "selected_resource_context", "recent_collections_by_page"],
  "output": ["action_execution", "binding_result", "shortcut_notice", "collection_navigation", "interaction_events"],
  "upstream": ["resource_list_view", "random_recommendations_view", "UiBridge", "ShortcutWebView"],
  "downstream": ["resource_detail_binding", "external_open_action", "collection_membership", "library_removal"],
  "notes": "八个固定动作；绑定经 app_settings 持久化且默认留空；退出/进入最近系列分属两个动作，三类合集页会话内独立记忆；侧键经 JS/Qt 子控件/Windows XButton 与 APPCOMMAND 归一为 MouseBack/MouseForward；系统保留键、编辑控件、模态框与 Text Rules 受保护"
}
```
