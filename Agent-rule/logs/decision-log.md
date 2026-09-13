# Decision Log

## 最新决策
```json
{"decision_id":"decision-20260913-001","timestamp":"2026-09-13T13:30:05+08:00","owner":"ui-agent","title":"Text Novel 表头与下拉复用后端排序 seam","context":"List 四列需要资源管理器式点击排序，同时保持 Grid、主页与合集的现有持久化语义","options":["仅前端临时排序","为表头新增独立状态","扩展现有 setPageSort 与排序枚举"],"decision":"扩展现有 setPageSort 为十档；表头和下拉共享 payload sort，主页与合集继续分键持久化","rationale":["避免前后端顺序漂移","Grid/List 切换继续复用同一排序","不增加 Bridge 方法或数据库迁移"],"impact":["Text Novel 主页与合集 List 支持四列表头升降序","Library 与漫画行为不变","兼容性：旧四档设置继续有效，非法值仍回退 file_mtime_desc；无数据库或资源 payload 迁移","回滚方案：回退本功能提交即可；旧版本读到新增枚举时会回退 file_mtime_desc，无需数据库回滚"],"followups":[]}
```

## 决策记录规则
- 每个关键架构决策必须在日志文件中突出注释，该记录存放到logs文件夹下的history文件夹中，文件名以年-月-日进行命名，若有同名文件，直接追加进去，**保存为md文档**，本文件下方的内容仅为模板和实际参考
- 决策记录必须包含原因、备选方案与影响评估。
- 决策一经生效，相关规则文件必须同步更新。

## 决策模板
```json
{
  "decision_id": "decision-YYYYMMDD-XXX",
  "timestamp": "ISO-8601",
  "owner": "master-agent|maintenance-agent",
  "title": "string",
  "context": "string",
  "options": ["string"],
  "decision": "string",
  "rationale": ["string"],
  "impact": ["string"],
  "followups": ["string"]
}
```

## 2026-09-13 - Text Novel 表头与下拉共享排序 seam

完整决策记录见 `logs/history/2026-09-13.md`。

```json
{"decision_id":"decision-20260913-001","timestamp":"2026-09-13T13:30:05+08:00","owner":"ui-agent","title":"Text Novel 表头与下拉复用后端排序 seam","context":"List 四列需要资源管理器式点击排序，同时保持 Grid、主页与合集的现有持久化语义","options":["仅前端临时排序","为表头新增独立状态","扩展现有 setPageSort 与排序枚举"],"decision":"扩展现有 setPageSort 为十档；表头和下拉共享 payload sort，主页与合集继续分键持久化","rationale":["避免前后端顺序漂移","Grid/List 切换继续复用同一排序","不增加 Bridge 方法或数据库迁移"],"impact":["Text Novel 主页与合集 List 支持四列表头升降序","Library 与漫画行为不变","兼容性：旧四档设置继续有效，非法值仍回退 file_mtime_desc；无数据库或资源 payload 迁移","回滚方案：回退本功能提交即可；旧版本读到新增枚举时会回退 file_mtime_desc，无需数据库回滚"],"followups":[]}
```

## 2026-09-12 - 字段标签截断与标签前进后退

完整决策记录见 `logs/history/2026-09-12.md`。

```json
{"decision_id":"decision-20260912-003","timestamp":"2026-09-12T10:45:00+08:00","owner":"ui-agent","title":"字段标签从目录截掉并复用合集前进后退","context":"早期扫描把 author/language 写入 tags_json；标签详情没有前进后退快捷识别","options":["只改 CSS 省略号","目录过滤并停写","复用合集动作","新增标签专用动作"],"decision":"目录和快捷添加截掉字段前缀；扫描不再写入；exit_collection/reopen_recent_collection 在标签页同样生效","rationale":["这些不是用户标签","已有后退/前进绑定无需重绑"],"impact":["存量字段标签立刻从目录消失","书本详情仍可能显示旧值直到重扫"],"followups":["不批量改写库内 tags_json"]}
```

## 2026-09-12 - open_tag 只从目录点击发出

完整决策记录见 `logs/history/2026-09-12.md`。

```json
{"decision_id":"decision-20260912-002","timestamp":"2026-09-12T10:30:00+08:00","owner":"ui-agent","title":"open_tag 只从目录点击经 Bridge 发出","context":"合同已登记 open_tag 但无发出点；getTagResources 同时服务刷新","options":["getTagResources 一律发","前端自记事件","Bridge.openTag 仅用户点目录时发"],"decision":"新增 openTag Slot，形状对齐 open_external；resource_id 为精确标签名；空标签不发，空详情仍发；刷新/改范围/改排序/失效重载不发","rationale":["与 09-11 open_external 同一可追踪入口","避免刷新误记为打开"],"impact":["interactionEvent 增加 open_tag","目录 click 先 openTag 再 loadTagResources"],"followups":["loading 硬锁与改范围双请求本轮不修"]}
```

## 2026-09-12 - 标签身份、分组与失效边界

完整决策记录见 `logs/history/2026-09-12.md`。

```json
{"decision_id":"decision-20260912-001","timestamp":"2026-09-12T10:08:29+08:00","owner":"ui-agent","title":"标签保持精确身份并通过统一来源 seam 聚合","context":"标签目录需要同时覆盖图书、文本小说和漫画，又不能破坏既有资源动作语义","options":["独立标签索引表","Repository 统一汇总现有 tags_json","前端直接拼接三类 payload"],"decision":"Repository 统一聚合，详情携带真实 sourcePage，并用独立失效信号和 request id 防旧响应","rationale":["避免第二份索引漂移","兼容既有标签身份和资源动作"],"impact":["comics 增加 tags_json","新增 tagManagerScopes 与标签 Bridge 接口","锁定 pypinyin==0.55.0"],"followups":[]}
```

## 2026-09-11 - 扫描字段刷新与 loop_inline

```json
{
  "decision_id": "decision-20260911-009",
  "timestamp": "2026-09-11T19:20:00+08:00",
  "owner": "parser-agent",
  "title": "文本扫描每次重抽规则字段，指纹只省封面",
  "context": "改规则后重扫作者不更新；Title: 被默认 take_after_text(T) 吃成 itle:；loop_lines 一行只能 search 一次",
  "options": [
    "指纹未变整本跳过",
    "指纹未变仍跑规则并窄更新元数据",
    "每次整本 upsert"
  ],
  "decision": "每次扫描都用当前 rules 重抽；文件+封面未变只写 title/author/tags/info_text；新增 loop_inline；默认标题链剥 Title:/标题：",
  "rationale": [
    "用户明确要求每次扫文本都必须按当前规则写回",
    "upsert_book UPDATE 会把 status 打成 UNREAD 并改封面列",
    "#tag1#tag2 需要 finditer 而不是改 split_tags"
  ],
  "impact": [
    "无自定义 title 时标题改为首行",
    "规则结果覆盖库内同名字段",
    "阅读状态在文件未变时保留"
  ],
  "followups": [
    "不改漫画合集排序",
    "不按 # 拆标签"
  ]
}
```

## 2026-09-11 - 本批功能走 minor 发布为 v2.4.0

```json
{
  "decision_id": "decision-20260911-010",
  "timestamp": "2026-09-11T19:15:00+08:00",
  "owner": "maintenance-agent",
  "title": "本批功能走 minor 发布为 v2.4.0",
  "context": "用户要求 commit、push 并远程打包发布；latest tag 为 v2.3.0",
  "options": ["patch", "minor", "major"],
  "decision": "workflow_dispatch bump=minor，预期 v2.4.0",
  "rationale": [
    "含小说排序、loop_inline、扫描每次重抽规则等用户可见能力",
    "与 v2.2.0/v2.3.0 功能批次同级"
  ],
  "impact": [
    "工作流会再提交 chore: release 并打 tag",
    "Nuitka 远程构建可能超过一小时"
  ],
  "followups": ["发布完成后核对 zip 与 Release 页"]
}
```

## 初始决策
```json
{
  "decision_id": "decision-20260411-001",
  "timestamp": "2026-04-11T13:05:00Z",
  "owner": "master-agent",
  "title": "项目定位为资源管理器而非阅读器",
  "context": "项目聚焦本地资源治理，需要优先保障扫描、索引、解析与展示链路",
  "options": [
    "A: 内置阅读器 + 管理能力",
    "B: 仅资源管理，阅读交给第三方软件"
  ],
  "decision": "选择 B",
  "rationale": [
    "降低系统复杂度",
    "将性能预算集中在扫描与展示",
    "减少阅读引擎兼容性维护成本"
  ],
  "impact": [
    "UI 需提供稳定的外部打开交互",
    "核心模块不引入阅读渲染依赖"
  ],
  "followups": [
    "在 UI 合同中固化 external_open_action",
    "在 shared-rules 中声明非目标边界"
  ]
}
```

## 2026-09-11 - 小说排序合集详情真正生效

```json
{
  "decision_id": "decision-20260911-008",
  "timestamp": "2026-09-11T18:40:00+08:00",
  "owner": "ui-agent",
  "title": "小说排序镜像漫画四档且合集详情真正生效",
  "context": "用户要求文本小说区域增加排序，细则参考漫画；漫画合集下拉目前只记设置不改成员顺序",
  "options": [
    "仅主页",
    "主页+合集下拉但合集仍按加入时间",
    "主页+合集详情都真正按所选排序"
  ],
  "decision": "主页与小说合集详情都真正排序；默认 file_mtime_desc；图书馆不动",
  "rationale": [
    "用户明确要合集详情真正生效",
    "日期字段用 INTEGER file_mtime 对齐漫画 folder_mtime，不在 SQL 里拆指纹字符串"
  ],
  "impact": [
    "现有小说库默认顺序变为文件日期新到旧",
    "新增 text_novel_sort_order_main/fav"
  ],
  "followups": [
    "不修漫画合集排序缺口"
  ]
}
```

## 2026-09-11 - 文本小说能力按 minor 发版

```json
{
  "decision_id": "decision-20260911-007",
  "timestamp": "2026-09-11T17:45:00+08:00",
  "owner": "master-agent",
  "title": "文本小说 Grid/封面/缩略图维护按 minor 发版",
  "context": "GitHub 已发布 v2.2.0（快捷键）；Codex 会话后半段的 Grid、同名封面与缩略图维护尚未进入 Release",
  "options": [
    "patch → v2.2.1",
    "minor → v2.3.0",
    "不对 Codex 提交 push 就对 origin/main 再 bump"
  ],
  "decision": "先 rebase/push Codex 两个提交，再 workflow_dispatch bump=minor，预期 v2.3.0",
  "rationale": [
    "Grid 与同名封面是用户可见新能力，口径与当天快捷键 minor 一致",
    "不先 push 会发不含功能的空 bump"
  ],
  "impact": [
    "下一正式版为 v2.3.0",
    "不手改 APP_VERSION，由 Release workflow 从 latest GitHub Release 递增"
  ],
  "followups": [
    "Actions 成功后确认 tag、zip 与检查更新对齐"
  ]
}
```

## 2026-09-11 - 文本小说缩略图维护语义

```json
{
  "decision_id": "decision-20260911-006",
  "timestamp": "2026-09-11T17:29:42+08:00",
  "owner": "thumbnail-agent",
  "title": "文本小说缩略图维护区分清空与重建语义",
  "context": "Text Novel 同时存在 manual 与 sidecar 封面，设置任务必须避免误删外部文件或覆盖用户选择",
  "options": [
    "直接复用 Library 仅清 thumbnail_path 的语义",
    "清空后立即自动重建",
    "按封面来源分别定义 cleanup 与 regenerate"
  ],
  "decision": "cleanup 只删除 preview_root 内缓存并清除封面状态；regenerate 保留有效 manual，否则按当前同名 sidecar 恢复",
  "rationale": [
    "缓存任务不能删除 preview_root 外文件",
    "手动封面优先必须覆盖独立重建路径",
    "无 sidecar 时明确回退标题占位"
  ],
  "impact": [
    "ThumbnailTaskWorker 新增 text_novel scope",
    "Settings 新增两个 Text Novel 维护按钮",
    "扫描与重建共享同一套 sidecar 选择和压缩规则"
  ],
  "followups": []
}
```

## 2026-09-11 - 文本同名封面来源与指纹

```json
{
  "decision_id": "decision-20260911-005",
  "timestamp": "2026-09-11T16:55:06+08:00",
  "owner": "ui-agent",
  "title": "文本同名封面采用来源优先与独立指纹",
  "context": "TXT 内容未变时，同名封面仍可能新增、修改或删除；用户手动封面不能被扫描覆盖",
  "options": [
    "封面仅随 TXT 指纹变化刷新",
    "每次扫描无条件重建封面",
    "记录 cover_source 与 cover_fingerprint，封面独立参与增量判断"
  ],
  "decision": "选择独立来源与指纹；manual 优先，sidecar 按 webp、png、jpg、jpeg 匹配",
  "rationale": [
    "封面与 TXT 内容的生命周期独立",
    "独立指纹避免未变封面反复解码",
    "旧 Text Novel 非空封面迁移 manual 可避免覆盖既有用户选择"
  ],
  "impact": [
    "books 增加两个可空字段且无需新表",
    "自动封面删除后清理缓存并回退标题占位",
    "损坏封面不阻断小说入库，只记录警告"
  ],
  "followups": []
}
```

## 2026-09-11 - 侧键录入三条通道

```json
{
  "decision_id": "decision-20260911-004",
  "timestamp": "2026-09-11T13:10:00+08:00",
  "owner": "ui-agent",
  "title": "侧键走页面、Qt 子控件与 Windows 原生三条通道",
  "context": "设置页绑定框无法识别鼠标侧键",
  "options": [
    "只拦 ShortcutWebView.mousePressEvent",
    "只听 JS button 3/4",
    "页面事件 + 子控件过滤 + Windows XBUTTON/APPCOMMAND"
  ],
  "decision": "选择第三条；token 统一为 MouseBack/MouseForward，并去重",
  "rationale": [
    "Chromium 子控件会吃掉父级 mousePressEvent",
    "系统常把侧键变成 BrowserBack 或 WM_APPCOMMAND",
    "auxclick 单独出现时也必须能录入"
  ],
  "impact": [
    "应用聚焦时侧键被吞，未绑定也不走网页历史",
    "窗口失焦时不拦截原生消息"
  ],
  "followups": ["真机仍失败再加低级鼠标钩子"]
}
```

## 2026-09-11 - 合集前进/后退分键

```json
{
  "decision_id": "decision-20260911-003",
  "timestamp": "2026-09-11T12:55:00+08:00",
  "owner": "ui-agent",
  "title": "合集导航改为前进/后退两个动作且按页记忆",
  "context": "用户要求退出与进入拆成两个快捷键，并在书籍合集中独立于其他合集页记忆",
  "options": ["保持全局 toggle", "两个动作共用全局最近项", "两个动作且三类合集页独立记忆"],
  "decision": "选择按页独立记忆；退出仅在详情生效，进入仅在对应合集列表生效",
  "rationale": ["浏览器前进/后退不会跨站点串历史", "页面返回按钮不应兼做重入"],
  "impact": ["绑定表增加 exit_collection 与 reopen_recent_collection", "忽略遗留 toggle_recent_collection"],
  "followups": []
}
```

## 2026-09-11 - 快捷键动作注册表与打开事件收口

```json
{
  "decision_id": "decision-20260911-001",
  "timestamp": "2026-09-11T11:04:30+08:00",
  "owner": "ui-agent",
  "title": "快捷键采用统一动作注册表与应用内输入通道",
  "context": "按钮、右键菜单和合集导航原先各自直调函数，无法安全复用动作，也没有退出后可重新进入的会话目标",
  "options": ["为每个组件单独增加 keydown", "注册系统级全局热键", "应用内动作注册表 + KeyboardEvent.code + 原生鼠标侧键信号"],
  "decision": "选择应用内统一动作注册表；绑定持久化，最近系列仅会话保存",
  "rationale": ["同一可用性判断和危险确认可供右键与快捷键共用", "KeyboardEvent.code 不受键盘布局字符变化影响", "原生视图可阻止 Chromium 把侧键当历史导航", "不引入系统级权限和依赖"],
  "impact": ["新增 shortcut_bindings 设置和七个固定动作", "Bridge 增加 setShortcutBinding 与 nativeShortcutInput", "设置页增加快捷键导航和录入/清除界面", "合集详情可一键退出并重入最近系列"],
  "followups": ["已关闭：openResource 发出 open_external interactionEvent，见 decision-20260911-002"]
}
```

```json
{
  "decision_id": "decision-20260911-002",
  "timestamp": "2026-09-11T12:45:00+08:00",
  "owner": "ui-agent",
  "title": "外部打开事件在 Bridge.openResource 源头发出",
  "context": "标准审查指出 open_resource 经 executeAction 进入 _open_external 后没有可追踪事件",
  "options": ["只给快捷键记事件", "在 openResource 源头发 interactionEvent", "落盘日志或新表"],
  "decision": "目标文件存在时发出合同形状的 open_external 信号；资源或文件缺失不发；不扩展 open_folder 事件名",
  "rationale": ["覆盖右键、双击和快捷键同一打开入口", "桌面端无需新消费者，测试连接信号即可断言", "避免把历史 telemetry 做成独立子系统"],
  "impact": ["interactionEvent 信号", "Shortcut 合同与模块输出补 interaction_events"],
  "followups": []
}
```

## 2026-09-09 - 随机推荐采用列级来源与显式缓存失效

```json
{
  "decision_id": "decision-20260909-001",
  "timestamp": "2026-09-09T13:10:10+08:00",
  "owner": "ui-agent",
  "title": "随机推荐采用列级 sourcePage、会话缓存和显式数据源失效标记",
  "context": "推荐页混合 Library、Text Novel、Comic 三种资源；通用 resourcesChanged 同时承载收藏、标签、合集和真实数据源变化，不能一律重抽",
  "options": [
    "A: 每次进入页面都重新抽取",
    "B: 所有 resourcesChanged 都立即清空并重抽",
    "C: 会话缓存；仅扫描、资源根增删和资源删除显式标记失效"
  ],
  "decision": "选择 C；sourcePage 放在固定推荐列上，列内卡片继承",
  "rationale": [
    "切页返回保持结果符合会话稳定性要求",
    "标签、收藏和合集变更不改变候选集合，不应让推荐跳变",
    "列级来源避免九个条目重复字段，同时保证所有动作路由一致",
    "request id 使数据源变化时的旧异步响应自动失效"
  ],
  "impact": [
    "resourcesChanged 增加 recommendationsInvalidated 布尔字段",
    "扫描完成、资源根增删、资源删除发送 true；其他 UI 数据刷新保持 false",
    "前端行为测试覆盖缓存、防重复、旧回调淘汰、搜索恢复和三类来源动作"
  ],
  "followups": []
}
```

## 追加决策
```json
{
  "decision_id": "decision-20260411-002",
  "timestamp": "2026-04-11T15:09:00Z",
  "owner": "master-agent",
  "title": "网格密度参数前置到 Library 页实时调节",
  "context": "用户需要在主界面直接观察和微调不同分辨率下的卡片密度，而非仅通过代码文件调整",
  "options": [
    "A: 仅保留 layout_config.py 手动改值",
    "B: 在 Library 页加入实时控制条并绑定配置"
  ],
  "decision": "选择 B",
  "rationale": [
    "降低调参与验证成本",
    "支持快速观察列数、卡片宽度与间距联动效果",
    "保持配置中心化，避免页面硬编码分叉"
  ],
  "impact": [
    "UI 层新增运行期参数调整入口",
    "GridDensityConfig 需支持可变更新并触发重排"
  ],
  "followups": [
    "补充配置持久化策略",
    "增加一键恢复默认值能力"
  ]
}
```

```json
{
  "decision_id": "decision-20260717-001",
  "timestamp": "2026-07-17T10:05:00+08:00",
  "owner": "indexer-agent",
  "title": "漫画同名默认 skip_incoming；Text 指纹跳过对齐 Library",
  "context": "Text 重扫仍全量跑规则链成本高；同一 comic_root 下同名叶子夹易重复入库，需可配置策略且默认保守",
  "options": [
    "A: 漫画冲突 keep_both（维持现状）为默认",
    "B: 漫画冲突 skip_incoming 为默认，另提供 keep_both / prefer_newer",
    "C: Text 继续全量 sha256 / 不跳过",
    "D: Text 使用与 Library 相同的 Settings hash_strategy 跳过（无 thumb 要求）"
  ],
  "decision": "漫画选 B；Text 选 D",
  "rationale": [
    "默认跳过新人避免同 root 重复占库，仍可用 keep_both 保留旧行为",
    "Text 与 Library 共用指纹策略，设置心智一致；Text 无封面故跳过条件不含 thumb",
    "跨 comic_root 允许同名，避免不同系列「第01卷」被全局误杀"
  ],
  "impact": [
    "Settings 新增 comic_title_conflict_policy；indexer-contract / README 需同步",
    "Text 二次扫描可计入 skipped_unchanged_count；用户改过的 title/tags 在指纹未变时得以保留",
    "Fast 指纹优化仅建议留档；TXT 编码优化后由 decision-20260717-002 落地"
  ],
  "followups": [
    "可选：落地 Fast 指纹优化建议（见 history/2026-07-17.md）；TXT 编码见 decision-20260717-002"
  ]
}
```

```json
{
  "decision_id": "decision-20260717-002",
  "timestamp": "2026-07-17T10:50:00+08:00",
  "owner": "indexer-agent",
  "title": "TXT 编码偏好 simplified|traditional|auto（默认简体）",
  "context": "纯 Big5→GB18030 强制改写会伤台繁库；需可配简/繁偏好，并降低低置信误判",
  "options": [
    "A: 维持强制 Big5→GB18030（仅面向简体）",
    "B: Settings text_encoding_preference + 64KB 样本 + normalizer 排名 + 双候选回退",
    "C: 无开关全量 GBK / errors=ignore"
  ],
  "decision": "选择 B；默认 simplified",
  "rationale": [
    "简体默认不选 Big5，避免大陆库乱码；繁体优先允许 Big5",
    "低置信双候选（GB18030↔UTF-8）比盲信 normalizer 更稳",
    "规则预览暴露 detectedEncoding/confidence，便于排查乱码"
  ],
  "impact": [
    "Worker 将偏好传入 Text/Comic 扫描；repository 持久化默认值",
    "indexer-contract / README / src_construction 需同步；design-advice-20260717-txt-encoding 标为已实现"
  ],
  "followups": [
    "Fast 指纹优化见 decision-20260718-001（文案 + 新装默认 Quick；算法本身未改）"
  ]
}
```

```json
{
  "decision_id": "decision-20260718-001",
  "timestamp": "2026-07-18T10:30:00+08:00",
  "owner": "indexer-agent + ui-agent",
  "title": "新装默认 Quick，路径与扫描任务共用设置入口",
  "context": "Fast 的 size+mtime 比对可能漏检内容变化；路径配置与扫描动作属于同一工作流，宜合并以便后续按文件夹定制扫描策略",
  "options": [
    "A: 继续默认 Fast 并仅增加风险提示",
    "B: 默认 Quick，保留 Fast 与 Strict 可选；旧用户已持久化值不强制迁移",
    "C: 默认 Strict",
    "D: 路径与任务继续分为两个导航页",
    "E: 路径与任务合并到一个导航页"
  ],
  "decision": "选择 B 与 E",
  "rationale": [
    "Quick 读盘成本远低于 Strict，假阴性远低于 Fast",
    "保留 Fast 给追求最低 I/O 的用户，并用 Settings 文案标明风险",
    "无法可靠区分旧默认与用户主动选 Fast，故不做强制迁移",
    "路径与扫描合并减少导航层级，并为「指定文件夹策略」预留同页布局"
  ],
  "impact": [
    "新库 / 非法值回退为 quick；已有合法 size_mtime 保持",
    "Settings 导航「路径与扫描」同时渲染路径卡与任务卡；旧 tasks 状态归一到 paths",
    "切换到 Quick 后旧记录首次补算 fingerprint_quick，第二次可 skip"
  ],
  "followups": [
    "观察大型书库使用 Quick 时的扫描耗时",
    "下一轮：支持指定文件夹使用特定扫描策略"
  ]
}
```

```json
{
  "decision_id": "decision-20260718-002",
  "timestamp": "2026-07-18T12:00:00+08:00",
  "owner": "indexer-agent + ui-agent",
  "title": "目录级扫描策略：总开关 + 全局/覆盖继承；漫画 snapshot/full",
  "context": "用户希望不同根目录使用不同指纹或漫画重扫强度；需与全局 Settings 共存且关闭开关时不丢已配覆盖值",
  "options": [
    "A: 仅全局 hash_strategy，无 per-root",
    "B: 每根强制独立策略，无全局回退",
    "C: 总开关 per_root_scan_strategy_enabled；开时根 scan_strategy 覆盖全局，关时统一全局但保留 DB 覆盖值",
    "D: 漫画仅 snapshot，不提供 full"
  ],
  "decision": "选择 C；漫画全局与 per-root 均为 snapshot|full，默认 snapshot",
  "rationale": [
    "总开关降低默认复杂度，关闭时行为与旧版一致",
    "保留覆盖值避免用户反复配置；开开关即可恢复",
    "Library/Text 复用 hash_strategy 三档；Comic 用 folder_size_mtime 快照 vs full 重扫旁注",
    "resolve_* 集中解析，scanner/worker 不重复分支"
  ],
  "impact": [
    "三表 library_roots/comic_roots/text_roots 新增可空 scan_strategy；settings 新增 per_root_scan_strategy_enabled、comic_scan_strategy",
    "UI 路径页开关 + 各根策略按钮/弹窗；General 页漫画全局策略下拉",
    "comic full 禁用 folder_size_mtime 短路并重读 info_text 旁注",
    "indexer-contract / README / src_construction / test_root_scan_strategy 需同步"
  ],
  "followups": [
    "大型多根书库下对比 per-root Quick vs Strict 耗时",
    "可选：UI 自动化覆盖 setRootScanStrategy 端到端"
  ]
}
```
