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
