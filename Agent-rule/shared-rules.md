# Shared Rules

## 技术栈约束
- 默认离线运行，不依赖在线服务完成核心流程。
- 索引与元数据存储必须支持本地持久化与崩溃恢复。
- 核心模块必须通过稳定的 JSON 结构交互，不允许隐式字段。
- 新增运行时依赖前，必须先在 `registry/module-registry.md` 登记。

## 架构原则
- 分层职责：扫描/解析/缩略图/UI 分层独立。
- 合同优先：模块输入输出以 `contracts/` 为准。
- 单向数据流：上游产物进入下游，禁止 UI 反向驱动扫描逻辑。
- 可替换性：模块实现可替换，但合同字段名保持稳定。

## 模块规则
- 每个模块必须有唯一 `module_name` 与 `owner_agent`。
- 每个模块必须声明 `input`、`output`、`upstream`、`downstream`。
- 模块变更后必须同步更新 `registry/module-registry.md`。
- 跨模块交接必须使用 `handoff-spec.md` 定义的 Packet 与 Envelope。

## 性能要求
- 增量扫描优先于全量扫描。
- 大目录扫描必须可中断并可恢复。
- 缩略图生成采用延迟策略，避免阻塞首屏展示。
- UI 列表渲染必须支持分页或虚拟化，避免一次性加载全部资源。

## 禁止事项
- 禁止 UI 模块直接扫描文件系统。
- 禁止在未登记合同的情况下新增跨模块字段。
- 禁止在核心流程中引入强制网络调用。
- 禁止绕过日志系统提交重大结构变更。

## 规则变更的通用要求
- 任何规则变更必须同步更新：
  - `project-context.md`（如影响定位或范围）
  - `registry/module-registry.md`（如影响模块）
  - `logs/worklog.md`
  - `logs/decision-log.md`
- 版本变更遵循 `maintenance-agent.md` 的语义化版本规则。
- 变更说明必须包含影响范围、兼容性与回滚方案。
