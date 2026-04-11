# Decision Log

## 决策记录规则
- 每个关键架构决策必须单独记录。
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
