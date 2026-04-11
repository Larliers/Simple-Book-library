# Worklog

## 记录规则
- 每次任务执行后必须追加一条记录,该记录存放到logs文件夹下的history文件夹中，文件名以年-月-日进行命名，保存为md文档，本文件下方的内容仅为模板和实际参考
- 记录必须包含任务来源、影响范围、产出与风险。
- 字段名保持稳定，便于后续自动检索。

## 每次工作记录模板
```json
{
  "log_id": "worklog-YYYYMMDD-XXX",
  "timestamp": "ISO-8601",
  "actor": "master-agent|maintenance-agent|indexer-agent|parser-agent|thumbnail-agent|ui-agent",
  "task": "string",
  "changes": ["string"],
  "affected_files": ["string"],
  "outputs": ["string"],
  "risks": ["string"],
  "next_actions": ["string"]
}
```

## 初始启动记录
```json
{
  "log_id": "worklog-20260411-001",
  "timestamp": "2026-04-11T13:00:00Z",
  "actor": "maintenance-agent",
  "task": "初始化 Agent-rule 规则系统",
  "changes": [
    "创建标准目录结构",
    "初始化核心规则文件",
    "建立 agents/contracts/registry/logs 基线"
  ],
  "affected_files": [
    "Agent-rule/project-context.md",
    "Agent-rule/shared-rules.md",
    "Agent-rule/master-agent.md",
    "Agent-rule/maintenance-agent.md",
    "Agent-rule/handoff-spec.md"
  ],
  "outputs": ["v0.1.0 基线规则可用"],
  "risks": ["后续模块扩展需严格遵守字段稳定性"],
  "next_actions": ["执行首轮模块任务拆分并登记 registry"]
}
```