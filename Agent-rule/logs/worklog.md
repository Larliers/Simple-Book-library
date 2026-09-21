# Worklog

## 最新记录
```json
{"log_id":"worklog-20260920-003","timestamp":"2026-09-20T16:05:00+08:00","actor":"maintenance-agent","task":"补充 README 的 TXT Rules 目标用户说明及英文翻译","changes":["中文 README 说明 Rules 面向使用自动化下载程序、浏览器插件或油猴脚本收集 TXT 图书后进行分类的用户","英文 README 增加对应的 download automation、browser extensions 和 Tampermonkey/Greasemonkey userscripts 说明","明确 Rules 只负责本地文件识别与分类，不负责下载内容","src_construction 更新公开文档资产说明"],"affected_files":["README.md","README.en.md","src_construction.md","Agent-rule/logs/worklog.md","Agent-rule/logs/history/2026-09-20.md"],"outputs":["中英文新增说明均位于 TXT Rules 小节","英文新增段落保持单段不超过 240 字符","git diff --check 通过"],"risks":["Rules 的实际能力仍限于导入后的本地文件识别与分类，不应被描述为下载器"],"next_actions":[]}
```

## 2026-09-20 - 三类资源多选与原子批量 Quick Add

```json
{
  "log_id": "worklog-20260920-001",
  "timestamp": "2026-09-20T09:30:00+08:00",
  "actor": "library-agent + ui-agent",
  "task": "为图书、文本小说和漫画增加跨视图多选及多合集、多 Tag 批量添加",
  "changes": [
    "Repository 新增混合资源单事务 apply_batch_quick_add，先全量校验再创建合集、写成员和 Tag",
    "Bridge 新增严格 applyBatchQuickAdd JSON interface，返回定向来源页/合集页缓存和 Tag 失效标记",
    "Web UI 新增完整有序数据多选状态机、键盘/右键/ARIA 交互、批量详情面板与分 kind 弹窗",
    "Glass/Vaporwave 补齐选中标记、批量分组和窄窗口样式",
    "同步中英文文案、UI agent/contract、结构说明、行为测试和 GUI 证据"
  ],
  "affected_files": [
    "src/bookhub/library/repository.py",
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web/css/skins/glass/components.css",
    "src/bookhub/ui/web/css/skins/vaporwave/components.css",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/test_collection_kinds.py",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/js/test_quick_add.js",
    "src/tests/js/test_multi_select.js",
    "Agent-rule/agents/ui-agent.md",
    "Agent-rule/contracts/ui-contract.md",
    "src_construction.md"
  ],
  "outputs": [
    "Python 全量 292 passed, 70 subtests passed",
    "五组 Node 行为测试和两组 JS 语法检查通过",
    "Glass/Vaporwave 在 1400、1120、520px 的 Qt WebEngine 验收通过",
    "Agent-rule/logs/evidence/2026-09-20-batch-quick-add-gui.md"
  ],
  "risks": [
    "本次只增加批量添加；批量移除、删除、打开和封面编辑仍保持单项语义",
    "窄窗口批量弹窗依赖内部纵向滚动查看全部分组和提交按钮"
  ],
  "next_actions": []
}
```

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

## 2026-09-19 - 发布总书库排序到 origin

完整记录见 `logs/history/2026-09-19.md`。今日 Codex 会话「为总书库增加排列功能」已由 Codex 提交 `dde2105`，本轮只做发布与留档。

```json
{"log_id":"worklog-20260919-003","timestamp":"2026-09-19T16:20:00+08:00","actor":"maintenance-agent","task":"根据今日 Codex 对话将总书库排序功能推送到 origin/main","changes":["确认工作树干净且 feat 已由 Codex 提交为 dde2105","补齐发布留档并将本地领先提交推送到 origin/main"],"affected_files":["Agent-rule/logs/history/2026-09-19.md","Agent-rule/logs/worklog.md","src_construction.md"],"outputs":["origin/main 包含 dde2105 feat: add persistent library sorting","顺带发布当日 P1：c060b72 / 2193f1d / 78e7885 / 31395c5"],"risks":["未触发 Release，安装包仍停在 v2.4.0","不能单独推送 feat 而不带上其之前的 4 个 P1 提交"],"next_actions":["等待用户确认是否 workflow_dispatch 打新 Release"]}
```

## 2026-09-19 - P1 三项缺陷修复

完整记录见 `logs/history/2026-09-19.md`，GUI 与红绿灯证据见 `logs/evidence/2026-09-19-p1-bug-fixes.md`。

```json
{"log_id":"worklog-20260919-001","timestamp":"2026-09-19T18:30:00+08:00","actor":"maintenance-agent","task":"修复并归档 BUG-6、BUG-8、BUG-9","changes":["Qt slot 整型设置统一交给 Repository normalizer","修复 Vaporwave 五个字体资源路径","CBZ v2 匿名 marker 与同源即时/30 天 TTL 两层淘汰","同步主清单、结构说明和日志"],"affected_files":["src/bookhub/ui/web_window.py","src/bookhub/ui/web/css/skins/vaporwave/fonts.css","src/bookhub/library/formats/cbz.py","src/tests/test_repository_orphan_cleanup.py","src/tests/test_web_bridge_smoke.py","src/tests/test_new_formats_import.py","bugissue.md","src_construction.md","Agent-rule/logs/history/2026-09-19.md","Agent-rule/logs/evidence/2026-09-19-p1-bug-fixes.md","Agent-rule/logs/decision-log.md","Agent-rule/logs/worklog.md"],"outputs":["BUG-6/8/9 已归档，主待办剩 8 项","全量 279 passed, 54 subtests passed","四组 Node 与 JS 语法检查通过","双皮肤三视口 GUI 通过"],"risks":["390px Library 保持既有固定双栏压缩布局","BUG-7 未改，仍需真实负载基准"],"next_actions":["按 bugissue.md 处理低-3 与失效范围优化"]}
```

## 2026-09-18 - 启动 Cursor My Machines worker

完整记录见 `logs/history/2026-09-18.md`。

```json
{"log_id":"worklog-20260918-001","timestamp":"2026-09-18T16:35:00+08:00","actor":"master-agent","task":"为本仓库启动 Cursor Agent CLI 的 My Machines worker（agent worker start）","changes":["安装 Cursor Agent CLI 2026.09.15-d2fe57e 并写入用户 PATH","agent login 登录 dr.kenliers@gmail.com","补齐 better-sqlite3 ABI 137 后启动常驻 worker simple-book-library"],"affected_files":["Agent-rule/logs/history/2026-09-18.md","Agent-rule/logs/worklog.md"],"outputs":["worker 已连接，Cursor 可见 1 台机器","workerId=924c5fb2-14f4-47a0-939a-396249fca493","repo=Larliers/Simple-Book-library","入口 https://cursor.com/agents#workerId=924c5fb2-14f4-47a0-939a-396249fca493"],"risks":["关闭 worker 终端即断开","agent update 可能覆盖 ABI 修复","脏工作区与领先 origin 的 4 个提交会被 Cloud Agent 看到","Windows 无 computer use"],"next_actions":["在 cursor.com/agents 选择 simple-book-library 后下发任务","保持 worker 进程不退出"]}
```

## 2026-09-16 - 本地遗留 Issue 全量核验

完整记录见 `logs/history/2026-09-16.md`，动态与 GUI 证据见 `logs/evidence/2026-09-16-known-issues-audit.md`，唯一主清单见仓库根目录 `bugissue.md`。

```json
{"log_id":"worklog-20260916-001","timestamp":"2026-09-16T10:15:00+08:00","actor":"maintenance-agent","task":"全量核验本地遗留 Issue，并整合为唯一主清单","changes":["复核 bugissue、Agent 日志、Text Rules 交接、旧规格、测试输出和崩溃报告","完成临时运行时与双皮肤 GUI 复现","重构 bugissue.md 并新增审计证据和结构说明定位"],"affected_files":["bugissue.md","Agent-rule/logs/evidence/2026-09-16-known-issues-audit.md","Agent-rule/logs/history/2026-09-16.md","Agent-rule/logs/worklog.md","src_construction.md"],"outputs":["主待办 11 项：7 项确认存在、4 项部分存在","全量 270 passed, 43 subtests passed","四组 Node 行为测试和 JS 语法检查通过","git diff --check 通过，临时审计 fixture 已删除"],"risks":["本轮未修复主待办","高 DPI 与 Nuitka 打包保持无法验证","BUG-7 尚需真实重负载基准"],"next_actions":["按 bugissue.md 建议顺序实施","等待用户确认提交和 push 边界"]}
```

## 2026-09-15 - Quick Add 收尾

完整记录见 `logs/history/2026-09-15.md`，GUI 证据见 `logs/evidence/2026-09-15-quick-add-gui.md`。

```json
{"log_id":"worklog-20260915-002","timestamp":"2026-09-15T11:58:00+08:00","actor":"ui-agent","task":"接力 Quick Add 收尾：复核审查项、修 settings 非法字符串、补三类 GUI 与日志","changes":["set_scan_depth 与 set_text_preview_chars 与 getter 共用容错归一化","apply_setting 不再对这两项预先 int()","真实 WebEngine 补齐图书/小说/漫画创建与加入已有合集验收"],"affected_files":["src/bookhub/library/repository.py","src/bookhub/ui/web_window.py","src_construction.md","Agent-rule/logs/worklog.md","Agent-rule/logs/decision-log.md","Agent-rule/logs/history/2026-09-15.md","Agent-rule/logs/evidence/2026-09-15-quick-add-gui.md"],"outputs":["全量 270 passed, 43 subtests passed","双皮肤三类资源 GUI 证据"],"risks":["Vaporwave 600 Text Novel 的 contentArea 未形成内部滚动，scrollTop 保持 0 但写入仍不重绘","Quick Add 改标签仍可能整页重绘","本地 main 领先 origin 4 个提交，未 push"],"next_actions":["等待确认是否提交收尾改动","等待确认是否 push 以及是否包含 09-12/09-13 提交"]}
```

```json
{"log_id":"worklog-20260915-001","timestamp":"2026-09-15T11:17:18+08:00","actor":"ui-agent","task":"Quick Add 合集无刷新与快捷创建","changes":["Repository 新增 apply_collection_membership_changes 单事务校验 kind/ID、同名复用、创建与增删","Bridge 新增 applyCollectionQuickAdd，成功不广播 resourcesChanged","搜索无 Unicode casefold 同名时显示创建并添加；提交期锁定关闭/遮罩/标签/合集","SQLite 异常转为 storage_error；失败留窗，成功只回写合集页缓存与当前详情"],"affected_files":["src/bookhub/library/repository.py","src/bookhub/ui/web_bridge.py","src/bookhub/ui/web/js/app.js","src/bookhub/ui/web/css/base.css","src/bookhub/i18n/locales/zh-cn.json","src/tests/js/test_quick_add.js","src/tests/test_collection_kinds.py","src/tests/test_web_bridge_smoke.py","Agent-rule/contracts/ui-contract.md","Agent-rule/agents/ui-agent.md","src_construction.md"],"outputs":["三类资源 Quick Add 合集无整页重绘","快捷创建与批量确认","提交锁与 storage_error 回归"],"risks":["Quick Add 改标签仍走 addResourceTag 并可能整页重绘","createCollection/renameCollection/deleteCollection 仍全量广播","兼容性：无数据库迁移；旧 setCollectionMembership 改走同一事务且不再广播","回滚方案：回退 3ef3ee1 与 b17a34b"],"next_actions":[]}
```

## 2026-09-13 - 文本小说列表表头排序

完整记录见 `logs/history/2026-09-13.md`，GUI 证据见 `logs/evidence/2026-09-13-text-novel-column-sort-gui.md`。

```json
{"log_id":"worklog-20260913-001","timestamp":"2026-09-13T13:30:05+08:00","actor":"ui-agent","task":"文本小说主页与小说合集 List 表头排序","changes":["Repository 扩展为文件日期及四列表头十档排序","表头原生按钮与下拉共享 setPageSort 和持久化状态","Glass/Vaporwave 增加方向、焦点和窄屏样式"],"affected_files":["src/bookhub/library/repository.py","src/bookhub/ui/web/js/app.js","src/bookhub/ui/web_bridge.py","src/bookhub/ui/web/css/base.css","src/bookhub/ui/web/css/skins/glass/components.css","src/bookhub/ui/web/css/skins/vaporwave/components.css"],"outputs":["主页与合集四列表头升降序","双皮肤 1440/749/390 Qt WebEngine 验收"],"risks":["全量测试仍有两个既有非法整型设置失败","兼容性：旧四档设置继续有效，非法值仍回退 file_mtime_desc；无数据库或资源 payload 迁移","回滚方案：回退本功能提交即可；旧版本读到新增枚举时会回退 file_mtime_desc，无需数据库回滚"],"next_actions":[]}
```

## 2026-09-12 - 截掉字段标签并接入标签前进后退

完整记录见 `logs/history/2026-09-12.md`。

```json
{"log_id":"worklog-20260912-003","timestamp":"2026-09-12T10:45:00+08:00","actor":"ui-agent","task":"截掉字段前缀标签并为标签页接入前进后退","changes":["目录与 get_all_tags 截掉 author/publisher/language/series 前缀","build_metadata_tags 不再写入字段标签","exit_collection/reopen_recent_collection 在标签页退出或重开最近标签"],"affected_files":["src/bookhub/library/metadata.py","src/bookhub/library/repository.py","src/bookhub/ui/web/js/app.js","src/bookhub/ui/web_bridge.py","src/bookhub/i18n/locales/zh-cn.json"],"outputs":["字段标签不再出现在标签目录","同一后退/前进绑定可用于标签详情"],"risks":["存量 tags_json 需重扫才从书本详情清掉","图书详情仍可能显示旧字段标签"],"next_actions":["等待确认是否提交（排除 pycache）"]}
```

## 2026-09-12 - 补齐 open_tag 交互事件

完整记录见 `logs/history/2026-09-12.md`。

```json
{"log_id":"worklog-20260912-002","timestamp":"2026-09-12T10:30:00+08:00","actor":"ui-agent","task":"补齐标签目录 open_tag 可追踪事件","changes":["Bridge.openTag 仅在用户点目录标签时发出 open_tag","目录 click 先 openTag 再拉详情，刷新路径不发","同步 UI contract 与 ui-agent 输出枚举"],"affected_files":["src/bookhub/ui/web_bridge.py","src/bookhub/ui/web/js/app.js","src/tests/test_web_bridge_smoke.py","src/tests/js/test_tag_management.js","Agent-rule/contracts/ui-contract.md","Agent-rule/agents/ui-agent.md"],"outputs":["open_tag 合同闭环","标签专项与 Bridge 冒烟覆盖发出/不发出"],"risks":["loading 硬锁与改范围双请求仍在","add_root 可能过宽置位 tagCatalogInvalidated","未提交且勿带 pycache"],"next_actions":["等待确认是否提交（排除 pycache）"]}
```

## 2026-09-12 - 标签管理目录与混合资源详情

完整记录见 `logs/history/2026-09-12.md`，GUI 证据见 `logs/evidence/2026-09-12-tag-management-gui.md`。

```json
{"log_id":"worklog-20260912-001","timestamp":"2026-09-12T10:08:29+08:00","actor":"ui-agent","task":"新增标签管理目录、混合资源详情与三类范围设置","changes":["漫画标签持久化与三类 Repository 汇总","Bridge 标签接口和独立失效信号","双皮肤目录/详情/设置与请求竞态保护"],"affected_files":["requirements.txt","src/bookhub/library/repository.py","src/bookhub/ui/web_bridge.py","src/bookhub/ui/web_window.py","src/bookhub/ui/web/js/app.js"],"outputs":["标签管理功能","50 项专项测试","真实 Qt WebEngine GUI 验收"],"risks":["两个既有非法整型设置测试仍失败","既有 Vaporwave 字体 404"],"next_actions":[]}
```

## 2026-09-11 - 提交并触发 minor Release

```json
{
  "log_id": "worklog-20260911-012",
  "timestamp": "2026-09-11T19:15:00+08:00",
  "actor": "maintenance-agent",
  "task": "提交文本小说排序与规则扫描改动并触发远程 minor Release",
  "changes": [
    "提交功能改动并 push origin/main",
    "workflow_dispatch bump=minor，从 latest GitHub Release v2.3.0 递增为预期 v2.4.0"
  ],
  "affected_files": [
    ".github/workflows/release.yml"
  ],
  "outputs": [
    "origin/main 功能提交",
    "workflow_dispatch Release"
  ],
  "risks": [
    "工作流另提 chore: release 提交",
    "Nuitka 远程构建可能超过一小时"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 文本标签不再拼入 series

```json
{
  "log_id": "worklog-20260911-011",
  "timestamp": "2026-09-11T19:25:00+08:00",
  "actor": "parser-agent",
  "task": "文本标签不再拼入 series",
  "changes": [
    "scan_text_roots 标签只取 tag 字段拆分结果",
    "去掉 series: 前缀拼凑"
  ],
  "affected_files": [
    "src/bookhub/library/scanner.py",
    "src/tests/test_text_scan_incremental.py",
    "src_construction.md"
  ],
  "outputs": ["详情标签只显示 tag 规则结果"],
  "risks": [
    "Text Rules 的 series 字段仍可配置但扫描结果无处落库",
    "下次扫描会清掉已入库的 series: 标签"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 单行内循环提取与扫描字段刷新

```json
{
  "log_id": "worklog-20260911-010",
  "timestamp": "2026-09-11T19:20:00+08:00",
  "actor": "parser-agent",
  "task": "单行内循环提取与扫描字段刷新",
  "changes": [
    "新增 loop_inline：按行 finditer 取出全部捕获，默认 #([^#\\s]+)、join=newline",
    "scan_text_roots 无论指纹是否变化都跑当前 rules；未变走 update_text_novel_metadata",
    "默认标题链先剥 Title:/标题：再完整首行，去掉 take_after_text(T)"
  ],
  "affected_files": [
    "src/bookhub/library/text_rules/step_handlers.py",
    "src/bookhub/library/text_rules/rule_catalog.py",
    "src/bookhub/library/text_rules/rule_examples.py",
    "src/bookhub/library/scanner.py",
    "src/bookhub/library/repository.py",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/bookhub/ui/web_bridge.py",
    "src/tests/test_rule_engine.py",
    "src/tests/test_text_scan_incremental.py",
    "src/tests/test_text_novel_sort.py",
    "src_construction.md",
    "Agent-rule/agents/parser-agent.md",
    "Agent-rule/agents/indexer-agent.md",
    "Agent-rule/contracts/indexer-contract.md"
  ],
  "outputs": [
    "一行多个 #tag 可入库为多个标签",
    "改规则后点一次扫描即可刷新字段，不重置 status"
  ],
  "risks": [
    "无自定义 title 时标题变成 TXT 首行",
    "每次扫描用规则覆盖库内 title/author/tags/info_text"
  ],
  "next_actions": []
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

## 2026-09-11 - 文本小说主页与合集详情排序

```json
{
  "log_id": "worklog-20260911-009",
  "timestamp": "2026-09-11T18:40:00+08:00",
  "actor": "ui-agent",
  "task": "为文本小说区域增加与漫画同形态的排序选项",
  "changes": [
    "books 增加 file_mtime，扫描写入，启动时从指纹或 stat 回填",
    "新增 text_novel_sort_order_main / text_novel_sort_order_fav，默认 file_mtime_desc",
    "Text Novel 主页与小说合集详情标题栏增加四档下拉，合集详情真正按所选排序",
    "图书馆缺省仍按标题，随机推荐与漫画合集缺口不改"
  ],
  "affected_files": [
    "src/bookhub/library/repository.py",
    "src/bookhub/library/scanner.py",
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/test_text_novel_sort.py",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/test_comic_search.py",
    "Agent-rule/contracts/ui-contract.md",
    "Agent-rule/agents/ui-agent.md",
    "src_construction.md"
  ],
  "outputs": [
    "小说列表可按文件日期或标题正逆序排列并跨重启保持",
    "合集详情排序与主页分键持久化"
  ],
  "risks": [
    "已有小说库首次打开默认从标题 A-Z 变为文件日期新到旧",
    "file_mtime=0 且文件缺失的行每次启动仍会尝试回填"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 推送 Codex 文本小说改动并远程 minor Release

```json
{
  "log_id": "worklog-20260911-008",
  "timestamp": "2026-09-11T17:45:00+08:00",
  "actor": "master-agent",
  "task": "扫描最近一次 Codex 对话后推送未发布提交并触发远程 minor Release",
  "changes": [
    "确认 Codex 会话 01a08f8b 已完成本地提交：文本小说 Grid/同名封面与设置页缩略图清空/重建",
    "rebase origin/main，接入已发布的 chore: release v2.2.0，避免漏功能空 bump",
    "不提交已跟踪的 library_viewmodel pycache",
    "workflow_dispatch bump=minor，从 latest GitHub Release v2.2.0 递增为预期 v2.3.0"
  ],
  "affected_files": [
    "Agent-rule/logs/worklog.md",
    "Agent-rule/logs/history/2026-09-11.md",
    "Agent-rule/logs/decision-log.md",
    "src_construction.md"
  ],
  "outputs": [
    "main 含 Codex 两个功能提交",
    "远程 Nuitka 打包 GitHub Release v2.3.0"
  ],
  "risks": [
    "工作流先改 version.py 再 Nuitka，构建失败时 tag 已存在",
    "Nuitka 超时上限 120 分钟"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 文本小说缩略图清空与重建

```json
{
  "log_id": "worklog-20260911-007",
  "timestamp": "2026-09-11T17:29:42+08:00",
  "actor": "thumbnail-agent",
  "task": "补齐设置页文本小说缩略图清空与重建",
  "changes": [
    "Settings 缩略图任务增加 text_novel scope 的 cleanup/regenerate 两个入口",
    "抽取 text_cover 共享服务供扫描和设置页重建复用",
    "清空仅删除受控缓存并清除封面状态；重建保留有效 manual，否则读取当前 sidecar",
    "Settings 在 390px 使用单列外壳，长按钮可换行并提供键盘焦点样式"
  ],
  "affected_files": [
    "src/bookhub/library/text_cover.py",
    "src/bookhub/library/repository.py",
    "src/bookhub/library/scanner.py",
    "src/bookhub/library/thumbnail_tasks.py",
    "src/bookhub/library/thumbnail_worker.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web/css/base.css",
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/test_text_thumbnail_tasks.py",
    "src/tests/test_web_bridge_smoke.py"
  ],
  "outputs": [
    "设置页六个分 scope 缩略图维护按钮",
    "59 项专项 Python 测试与 4 个 subtests 通过",
    "Glass/Vaporwave 在 1440/749/390 无页面横向溢出"
  ],
  "risks": [
    "Vaporwave 既有 Sora/SpaceMono 字体文件 404，不由本功能引入",
    "全量测试仍有两个既有 Repository 非法整型设置失败"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 文本小说 Grid 与同名封面优化

```json
{
  "log_id": "worklog-20260911-006",
  "timestamp": "2026-09-11T16:55:06+08:00",
  "actor": "ui-agent",
  "task": "文本小说 Grid 与同名封面优化",
  "changes": [
    "Text Novel 独立持久化 Grid/List，首次默认 Grid，List 仅保留标题、作者、标签、路径",
    "扫描同目录同 stem 的 webp/png/jpg/jpeg，按固定优先级生成 360x540 内 WebP 缓存",
    "新增 cover_source 与 cover_fingerprint，旧 Text Novel 非空封面迁移 manual，sidecar 增删改随重扫更新",
    "Grid 保留详情、双击打开、右键、搜索、选中、虚拟化与键盘选择",
    "修复 390px 下三列外壳裁掉搜索和视图按钮的问题"
  ],
  "affected_files": [
    "src/bookhub/library/repository.py",
    "src/bookhub/library/scanner.py",
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/ui/web_window.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web/css/base.css",
    "src/bookhub/ui/web/css/skins/glass/components.css",
    "src/bookhub/ui/web/css/skins/vaporwave/components.css",
    "Agent-rule/registry/module-registry.md",
    "src/tests/test_text_scan_incremental.py",
    "src/tests/test_cover_grid_settings.py",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/js/test_random_recommendations.js"
  ],
  "outputs": [
    "同名封面自动缓存、刷新和删除回退",
    "Text Novel Grid/List 独立视图",
    "双皮肤多视口 GUI 验收证据"
  ],
  "risks": [
    "Vaporwave 既有 Sora/SpaceMono 字体文件 404，不由本功能引入",
    "全量测试仍有两个既有 Repository 非法整型设置失败"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 提交并触发远程 Release

```json
{
  "log_id": "worklog-20260911-005",
  "timestamp": "2026-09-11T13:05:00+08:00",
  "actor": "ui-agent",
  "task": "提交快捷键改动并触发远程 minor Release",
  "changes": [
    "提交快捷键、合集分键与侧键识别，排除 pyc",
    "触发 GitHub Actions Release bump=minor"
  ],
  "affected_files": [".github/workflows/release.yml"],
  "outputs": ["origin/main 功能提交", "workflow_dispatch Release"],
  "risks": ["工作流会再提交 chore: release 并打 tag", "Nuitka 远程构建可能超过一小时"],
  "next_actions": []
}
```

## 2026-09-11 - 快捷键绑定识别鼠标侧键

```json
{
  "log_id": "worklog-20260911-004",
  "timestamp": "2026-09-11T13:10:00+08:00",
  "actor": "ui-agent",
  "task": "修复快捷键绑定无法识别鼠标侧键",
  "changes": [
    "JS 识别 button/which/buttons、BrowserBack 与 keyCode 166/167，并在 pointerdown/mousedown/mouseup/auxclick 去重录入",
    "ShortcutWebView 过滤 Chromium 子控件上的 Back/Forward",
    "Windows 原生过滤 WM_XBUTTONDOWN 与 WM_APPCOMMAND"
  ],
  "affected_files": [
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web_window.py",
    "src/tests/js/test_shortcuts.js",
    "src/tests/test_web_bridge_smoke.py",
    "Agent-rule/contracts/ui-contract.md",
    "Agent-rule/registry/module-registry.md"
  ],
  "outputs": [
    "侧键三条通道归一为 MouseBack/MouseForward",
    "专项测试覆盖映射、子控件与 auxclick 去重"
  ],
  "risks": [
    "Chromium 独立 HWND 仍可能不进 Qt 消息泵",
    "应用内未绑定的侧键不再触发网页前进/后退"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 合集退出/进入拆分与按页记忆

```json
{
  "log_id": "worklog-20260911-003",
  "timestamp": "2026-09-11T12:55:00+08:00",
  "actor": "ui-agent",
  "task": "把合集导航从单一切换拆成退出与进入最近系列，并按合集页独立记忆",
  "changes": [
    "新增 exit_collection 与 reopen_recent_collection，移除 toggle_recent_collection",
    "State.recentCollections 按 collections/novel_collections/comic_collections 分记",
    "非合集页、列表态退出、详情态进入分别提示"
  ],
  "affected_files": [
    "src/bookhub/library/repository.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/js/test_shortcuts.js",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/test_cover_grid_settings.py"
  ],
  "outputs": [
    "设置导航组显示进入最近系列与退出当前系列",
    "专项测试覆盖三类独立记忆与删除失效"
  ],
  "risks": [
    "已保存的 toggle_recent_collection 绑定不会迁移",
    "全量测试仍有两个既有非法整型失败"
  ],
  "next_actions": []
}
```

## 2026-09-11 - 关闭 open_resource 可追踪交互事件

```json
{
  "log_id": "worklog-20260911-002",
  "timestamp": "2026-09-11T12:45:00+08:00",
  "actor": "ui-agent",
  "task": "接管 Codex 快捷键 WIP 并补齐审查未结案的外部打开事件",
  "changes": [
    "openResource 成功解析到存在的目标后发出 event/resource_id/timestamp",
    "缺失资源或缺失文件不发出成功事件，仍走原有 toast",
    "同步 Shortcut 合同、shortcut_action_dispatcher 输出与 Bridge 冒烟断言"
  ],
  "affected_files": [
    "src/bookhub/ui/web_bridge.py",
    "src/tests/test_web_bridge_smoke.py",
    "Agent-rule/contracts/ui-contract.md",
    "Agent-rule/registry/module-registry.md"
  ],
  "outputs": [
    "interactionEvent 信号可被测试连接断言",
    "Repository/Bridge 专项 47 项通过"
  ],
  "risks": [
    "全量测试仍有 2 个既有非法整型设置容错失败",
    "Vaporwave 仍有 2 个既有 SpaceMono 字体 404"
  ],
  "next_actions": []
}
```

## 2026-09-09 - 新增随机推荐页面

```json
{
  "log_id": "worklog-20260909-003",
  "timestamp": "2026-09-09T13:10:10+08:00",
  "actor": "ui-agent",
  "task": "新增图书、小说、漫画三列随机推荐页面及会话缓存",
  "changes": [
    "新增 random_recommendations 导航、只读 Bridge 接口与三列推荐视图",
    "推荐卡所有详情和资源动作继承列级 sourcePage",
    "仅扫描、资源新增/删除使缓存失效，并用 request id 阻止旧回调写回",
    "补齐 Glass/Vaporwave 样式、中文文案、行为测试与实际 GUI 验收"
  ],
  "affected_files": [
    "src/bookhub/ui/web_bridge.py",
    "src/bookhub/ui/web_window.py",
    "src/bookhub/ui/web/js/app.js",
    "src/bookhub/ui/web/css/base.css",
    "src/bookhub/ui/web/css/skins/glass/components.css",
    "src/bookhub/ui/web/css/skins/vaporwave/components.css",
    "src/bookhub/i18n/locales/zh-cn.json",
    "src/tests/test_web_bridge_smoke.py",
    "src/tests/js/test_random_recommendations.js"
  ],
  "outputs": [
    "每类最多 3 项且来源隔离的会话级推荐",
    "可执行的前端缓存、重抽、并发与来源路由行为测试",
    "Agent-rule/logs/evidence/2026-09-09-random-recommendations-gui.md"
  ],
  "risks": [
    "全量测试仍有 2 个既有非法整型设置容错失败",
    "Vaporwave 仍有 2 个既有 SpaceMono 字体 404"
  ],
  "next_actions": []
}
```


---

## 2026-04-13 - Collections & Favorites 模块实现

### 任务
完善 Collections 和 Favorites 模块（自定义书单），以及配套的右键菜单功能。

### 实现内容

**新增文件**:
1. `src/bookhub/ui/pages/collections_page.py`
   - `CollectionsPage` - 主书单列表页，网格展示，支持增删改
   - `CollectionCard` - 书单卡片（彩色首字母封面）
   - `CollectionDetailPage` - 书单内书籍列表

2. `src/bookhub/ui/pages/favorites_page.py`
   - `FavoritesPage` - 收藏书籍展示页
   - `FavoriteBookCard` - 收藏书籍卡片

3. `src/bookhub/ui/dialogs/add_to_collection_dialog.py`
   - `AddToCollectionDialog` - 添加到书单对话框
   - 支持搜索书单、复选框批量选择、新建书单

**修改文件**:
4. `src/bookhub/library/repository.py`
   - 新增 SQLite 表：collections, collection_books, favorite_books
   - 新增 15 个 CRUD 方法支持书单和收藏功能

5. `src/bookhub/ui/widgets/book_card.py`
   - 新增 `install_book_context_menu()` 函数
   - 右键菜单：添加/移除收藏、添加到书单

6. `src/bookhub/ui/app_window.py`
   - 将 Collections 和 Favorites PlaceholderPage 替换为真实页面

### 技术栈
- PySide6 (UI framework)
- SQLite (通过现有 LibraryRepository._connection() 扩展)
- hashlib (书单封面颜色哈希)

### 设计决策
- 书单封面使用书单名称的 MD5 哈希选取颜色，显示首字母缩写（类似 Google Material Design）
- 右键菜单通过 `install_book_context_menu()` 函数在外部安装，不侵入 BookCardWidget 原有结构
- 收藏和书单使用独立 SQLite 表，与现有 books 表通过 book_id 关联
- 懒初始化 DB 表（首次调用时创建），不修改 _init_db 方法

### 后续
- 在 library_page.py 中调用 `install_book_context_menu(card, repository)` 后，右键菜单即可生效

---

## 2026-04-23 - QuickAddDialog 顶部白色层问题留档（仅记录）

### 任务
用户反馈右键弹窗中“添加标签”文字下方仍有白色层，本次仅做问题留档，不继续改代码。

### 现象
- 已移除书名条样式层与书单左侧 LIST 列后，顶部区域仍存在层级感（白色/浅色层视觉）。

### 初步判断
- 问题更可能来自 `titleBar` 容器样式而非 `bookLabel` 文本自身。
- 重点关注：
  - `QWidget#titleBar` 的 `background-color`
  - `QWidget#titleBar` 的 `border-bottom`

### 影响文件（观察范围）
- `src/bookhub/ui/dialogs/quick_add_dialog.py`
- `src/bookhub/ui/resources/styles.py`（如需排查全局样式覆盖）

### 风险
- 若直接调整标题栏样式，可能影响弹窗边界层次感与关闭按钮可见性，需要视觉回归确认。

### 后续建议
1. 将 `titleBar` 背景与 `dialogBody` 统一；
2. 去除 `titleBar` 下边框分割线；
3. 若问题仍在，排查全局 QSS 通配规则优先级。

---

## 2026-05-03 - Settings 路径删除按钮遮挡修复

### 任务
修复 Settings 页面中 Library/Comic 路径列表右侧 Delete 按钮被遮挡的问题。

### 实现内容

**修改文件**:
1. `src/bookhub/ui/pages/settings_page.py`
   - 引入 `Qt` 与 `QAbstractItemView`。
   - `folders` 与 `comic_folders` 统一设置滚动策略：
     - 关闭横向滚动条 `ScrollBarAlwaysOff`
     - 垂直滚动模式 `ScrollPerPixel`
     - 垂直滚动条 `ScrollBarAsNeeded`
   - 路径行构建重构为共享方法 `_append_root_row(...)`，避免 Library/Comic 两套逻辑漂移。
   - 路径标签改为单行显示（`setWordWrap(False)`），并保留文本可选中与 tooltip。
   - Delete 按钮设置最小宽度 `72` 且右对齐，行右侧内边距增加到 `12`，保证窄宽度下不被遮挡。

2. `src_construction.md`
   - 在 `settings_page.py` 条目中插入本次修复说明，更新当前事实文档。

### 风险与验证
- 风险较低：仅调整设置页路径行布局与列表滚动策略，不涉及扫描/存储逻辑。
- 验证标准：窄窗口宽度下 Delete 按钮完整可见且可点击；Library/Comic 两个列表行为一致。

---

## 2026-09-19 - 总书库与书籍合集持久化排序

### 任务
为总书库和已打开的书籍合集详情增加持久化排序，并复用 Text Novel 的下拉与 List 表头交互。

### 实现内容
- Repository 新增 `library_sort_order_main`、`library_sort_order_fav`：总书库支持 10 档字段排序，书籍合集再增加加入时间升/降序；非法值分别回退到 `title_asc`、`added_desc`。
- Bridge 为两类 payload 增加 `sort`，扩展 `setPageSort(page, order)`，保持主页与合集状态独立，并在排序后的资源上继续搜索过滤。
- Web UI 为总书库显示 10 档下拉、合集详情显示 12 档下拉；List 保留封面列，标题/作者/标签/路径使用原生按钮并同步箭头与 `aria-sort`。
- 600px 以下为总书库和书籍合集详情启用现有单列响应式布局，保证 390px 下返回按钮、排序下拉及表格无横向溢出。
- 同步 UI contract、UI agent、module registry 与 `src_construction.md`。

### 影响、兼容性与回滚
- 影响仅限 Library 主页和已打开的书籍合集详情；合集总览、Text Novel、Comic、搜索范围及 Grid/List 切换规则不变。
- 无数据库 schema 迁移；旧库自动补默认设置。旧版本会忽略新增设置键，新版本遇到非法值会分别回退到 `title_asc` / `added_desc`。
- 回滚时可直接回退本功能代码；`app_settings` 中遗留的两个新增键可安全保留，无需清库或数据迁移。

### 验证结果
- Python 全套：`283` 项通过。
- Node 行为测试：random recommendations、tag management、shortcuts、quick add 共 4 组通过。
- Qt WebEngine GUI：Glass/Vaporwave 两套皮肤，Library/合集详情的 1440、749、390px 均通过；下拉数量、选中态、表头双向切换、箭头、`aria-sort`、封面列、返回按钮、持久化和横向溢出均已检查，控制台脚本错误为空。

---

## 2026-09-21 - 总书库图片文件夹书籍导入

### 任务
沿用总书库根目录扫描，在单次遍历中把符合门槛的图片目录作为普通书籍导入，并贯通封面、缓存、合集和外部打开。

### 实现内容
- 候选限定根下第 1～`scan_depth` 层、无子目录、直接图片至少 3 张且严格多于其他文件；支持 JPG/JPEG/PNG/WebP/GIF/BMP/TIF/TIFF，合格目录内部文件不再单独入库。
- 图片书以 `.imgfolder` / `book` 入库；直接文件名、size、mtime_ns 形成快照，自然序首图持久化到新增的 `books.cover_image_path`，旧数据库自动迁移。
- 扫描根完整可读后才执行缺失/失格清理；失格删除记录及收藏/合集关联，摘要增加图片书识别、新增、更新与失效移除指标。
- Library 缩略图任务可从保存的首图重建 `book/compressed` WebP；手动封面有效时保留，损坏首图以结构化 warning 降级。
- Bridge 下发 `coverImage`；双击打开首图，右键打开目录；总书库与书籍合集复用左上角 `.format-badge` 显示 `IMG`。
- 同步 Indexer/Thumbnail/UI agent 与 contract、module registry、project context、中英文 README 和 `src_construction.md`。

### 验证结果
- 新增专项覆盖资格边界、八类图片扩展、自然排序、冲突、增量、手动封面、失效/不可访问根、迁移、重建和 Bridge 交互；Python 全量 309 项通过。
- 五组 Node 行为测试、`app.js` / `text_rules.js` 语法检查和 `git diff --check` 通过。
- Glass/Vaporwave 的总书库与书籍合集在 1400/760/390px 真实 Qt WebEngine 验收通过，无脚本错误或横向溢出。
- 用户 `E:/DL book/设定集` 仅只读核验，识别 1 个合格目录（80 JPG、0 其他文件、0 子目录）。

---

## 2026-09-20 - 双语 README 用户向重写与公开主截图

### 任务
将中英文 README 重组为面向个人藏书用户的产品入口，并用匿名演示数据生成当前 Web UI 的 1920×1080 Glass 主截图。

### 实现内容
- `README.md` / `README.en.md` 改为“定位与下载 → 截图 → 目标用户 → 核心能力 → 稳定版/main → 上手 → 格式 → 隐私与限制 → 开发与帮助”的用户向顺序。
- 保留两份 README 各一个 `**v2.4.0**` 标记，稳定版与 main 未发布能力分开描述，避免 Release 安装包承诺源码独有功能。
- 新增 `docs/assets/screenshots/simple-book-library-glass-1920x1080.png`：真实 Qt WebEngine、Glass 日间、隔离临时数据库、虚构书名与程序生成封面。
- `shared-rules.md` 增加对外文档维护规则，`project-context.md` 规则版本升级为 `v0.1.1`；业务 agent、contract 与 registry 不变。
- `src_construction.md` 插入公开文档资产路径，保持当前事实结构。

### 影响、兼容性与回滚
- 仅修改公开文档、截图资产和规则说明，不改变运行时代码、数据库、CLI、模块接口或依赖。
- 现有 Release workflow 仍可通过粗体版本标记同步两个 README。
- 回滚时可恢复两份 README 与规则文档并删除新增截图；用户数据和运行时无需迁移。

### 验证结果
- 远端 tags、本地 tag 与 `APP_VERSION` 均确认最新稳定版本为 `v2.4.0`。
- 截图尺寸为 1920×1080、492557 bytes；真实页面 `scrollWidth == clientWidth == 1920`，脚本错误为空。
- 截图正文仅出现 `C:\DemoLibrary\...` 演示路径，不含用户目录或工作区路径；人工目检封面、详情、排序与导航清晰可见。
- 中英文 README 本地链接完整，各有一个 Release workflow 可识别的版本标记；`git diff --check` 通过。

---

## 2026-09-20 - README TXT Rules 目标用户补充

### 任务
补充文本小说 Rules 面向的实际用户场景，并提供自然的英文翻译。

### 实现内容
- 中文 README 说明：使用自动化程序、浏览器插件或油猴脚本从网站收集 TXT 图书后，可用 Rules 提取标题、作者和标签并分类，避免逐本手动打 Tag。
- 英文 README 对应说明 download automation、browser extensions 和 Tampermonkey/Greasemonkey userscripts 用户。
- 中英文均明确 Rules 只负责本地文件识别与分类，不负责下载内容。
- 更新 `src_construction.md` 的公开文档资产说明。

### 验证结果
- 英文新增说明的每个段落均不超过 240 个字符。
- `git diff --check` 通过。
