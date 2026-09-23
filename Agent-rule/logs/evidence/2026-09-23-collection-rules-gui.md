# 2026-09-23 集合规则真实 GUI 验收

## 环境

- 真实 `WebAppWindow` + Qt WebEngine，隔离临时 SQLite 与虚构 Book/Text Novel/Comic 数据。
- 皮肤：Glass、Vaporwave。
- 窗口：1200×860、740×820、600×820；另检查 600px 右键模态。

## 验收结果

- Settings → 集合规则按 Book/Text Novel/Comic 三组显示；启用状态、自动成员和排除数可见。
- 1200/740/600 三档两套皮肤均满足 `documentElement/content/manager/editor scrollWidth <= clientWidth`，无脚本错误。
- 右键顺序为“打开 → 编辑集合规则… → 重命名 → 删除”，打开菜单后首项获得焦点。
- 单合集模态在 1200px 与 600px 均无横向溢出，条件、开关和排除区可见且可关闭。
- 影响预览生成 5 个统计项；修改配置会使旧预览失效。
- 关闭已启用规则时出现选择层；取消后保留原开关状态。
- “取消排除”后 UI 排除行从 1 降为 0，Repository 回读排除数为 0，并立即恢复仍命中的资源。
- 审查后 Node DOM 回归另覆盖：空合集只请求一次、空白草稿行不进入规则 payload、右键 action 在开模态前恢复卡片焦点、异步旧预览不得重新解锁保存。

## 自动化入口

- 临时门禁脚本：`C:\tmp\bookhub_collection_rules_gui_qa.py`。
- 该脚本不属于产品运行时或打包内容；没有新增依赖或启动入口。
