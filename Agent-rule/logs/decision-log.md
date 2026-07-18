# Decision Log

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
