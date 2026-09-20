# 多资源批量 Quick Add GUI 验收证据（2026-09-20）

- 被测程序：真实 `WebAppWindow` + Qt WebEngine；Repository 替换为隔离临时数据库，不读写用户书库。
- 验收脚本：`C:/tmp/bookhub_batch_multi_gui_qa.py`。
- 截图目录：`C:/Users/83023/.codex/visualizations/2026/09/19/01a0b9a9-e2ef-7803-9bf1-75ac657d91a8/`。
- 皮肤与视口：Glass / Vaporwave；1400×860、1120×800、520×760。

## 结果

- 标签详情稳定返回 24 项，选择覆盖 Library、Text Novel、Comic 各 1 项；DOM 选中数与 `aria-selected=true` 均为 3。
- 右侧批量面板显示总数及三类计数；批量弹窗显示 3 个 kind 分组。
- 三个视口的 document、内容区和弹窗均无横向溢出；520px 下弹窗边界为 `left=24`、`right=496`。
- 成功提交后：弹窗关闭、选择数变为 0、Tag `2026` 写入 3 项、三类合集各写入 1 个成员；内容区滚动位置 `180 → 180`。
- SQLite trigger 强制中途失败后：弹窗仍打开、2 项选择保留、合集选择保留、`data-submitting=false`，无 disabled 控件，可直接重试。
- 两套皮肤的 `window.__qaErrors` 均为空。

## 截图

- `batch-multi-glass-1400.png`
- `batch-multi-glass-1120.png`
- `batch-multi-glass-520.png`
- `batch-multi-glass-failure.png`
- `batch-multi-vaporwave-1400.png`
- `batch-multi-vaporwave-1120.png`
- `batch-multi-vaporwave-520.png`
- `batch-multi-vaporwave-failure.png`

## 自动化

- Python 全量：`292 passed, 70 subtests passed`。
- Node 行为：random recommendations、tag management、shortcuts、quick add、multi select 共 5 组通过。
- JavaScript 语法：`app.js`、`text_rules.js` 均通过 `node --check`。
- `git diff --check` 通过，仅报告现有 Windows CRLF 转换提示。
