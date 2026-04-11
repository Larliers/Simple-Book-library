# Agent-rule 开发维护说明

本文件用于快速说明 `Agent-rule` 目录中每个 Markdown 文件的职责，便于开发和维护时定位规则来源。

## 根目录文件

### `project-context.md`
- 定义项目定位、管理对象、核心流程、非目标、优先级和规则版本。
- 作用：统一团队对项目边界和目标的认知。

### `shared-rules.md`
- 定义全局约束：技术栈、架构原则、模块规则、性能要求、禁止事项、规则变更要求。
- 作用：所有 Agent 和模块实现的共同基线。

### `master-agent.md`
- 定义总控 Agent 的角色、职责、路由准则和固定输出结构。
- 作用：用于任务拆分、调度和交接草稿生成。

### `maintenance-agent.md`
- 定义规则系统维护职责、变更类型、版本规则和维护输出结构。
- 作用：保障规则演进时的结构一致性与可追溯性。

### `handoff-spec.md`
- 定义跨 Agent 交接格式（Handoff Packet）和回包格式（Output Envelope）。
- 作用：保证 Agent 间输入输出字段稳定一致。

## agents 目录

### `agents/indexer-agent.md`
- 扫描目录、识别资源、建立索引、执行增量扫描策略。

### `agents/parser-agent.md`
- 解析文件名/目录名并提取结构化元数据，支持规则配置化。

### `agents/thumbnail-agent.md`
- 选择封面候选、生成缩略图并管理缓存与延迟生成。

### `agents/ui-agent.md`
- 负责展示层与交互层，包括列表/瀑布流展示、数据绑定、外部打开动作。

## contracts 目录

### `contracts/indexer-contract.md`
- 约束索引模块的输入、输出、保证项与错误结构。

### `contracts/parser-contract.md`
- 约束解析模块的输入、输出、保证项与错误结构。

### `contracts/thumbnail-contract.md`
- 约束缩略图模块的输入、输出、保证项与错误结构。

### `contracts/ui-contract.md`
- 约束 UI 模块的数据输入、渲染输出与错误结构。

## registry 目录

### `registry/module-registry.md`
- 记录模块登记规范和模块清单（owner、状态、上下游、输入输出等）。
- 作用：作为模块责任边界和依赖关系的登记中心。

## logs 目录

### `logs/worklog.md`
- 记录每次任务执行内容、影响范围、产出、风险和后续动作。

### `logs/decision-log.md`
- 记录关键架构与规则决策，包括背景、备选方案、结论与影响。

## 使用建议
- 新增或调整规则时，优先同步更新 `shared-rules.md`、相关 `contracts`、`module-registry.md` 与 `logs`。
- 跨 Agent 协作时，先检查 `handoff-spec.md`，再发起任务交接。
