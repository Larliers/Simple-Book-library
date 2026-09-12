# 标签管理 GUI 验收证据（2026-09-12）

- 被测程序：`.venv/Scripts/pythonw.exe` 启动的真实 `WebAppWindow`，Repository 替换为隔离数据库，不读写用户书库。
- 调试通道：Qt WebEngine page-level CDP，`127.0.0.1:9231`。
- 双击入口：沿用现有 `启动 简易图书馆.lnk`，未新增第二个启动器。
- 截图：`C:/Users/83023/.codex/visualizations/2026/09/12/01a09334-3335-7963-bfa9-ba71e70b62b4/tag-manager-glass-1400.png`、`tag-manager-vaporwave-1400.png`。

## 结果

- Glass 与 Vaporwave 均在 1400×860、1120×800 检查；页面和内容区无横向溢出，标签项为原生按钮并可键盘聚焦。
- A→Z 为 A/B/C/#，Z→A 为 C/B/A/#；组内同步反转，`#` 始终置尾。中文“阿拉伯服饰/白色/城市”分别进入 A/B/C。
- 顶栏搜索在目录和详情态禁用；目录展示唯一标签数、组标签数及资源计数。
- “白色”详情按 Library/Library/Text Novel/Comic 稳定顺序返回 4 张卡，均有 `role=button`、`tabindex=0`、来源标识，Enter 选中后右侧详情可见。
- 当前详情中把范围切为仅 Library 后，资源立即刷新为 2 项；恢复全选后恢复为 4 项。
- 不存在标签保留标题、返回按钮和空状态；设置 > 常规显示独立范围卡片及三个复选项。
- 控制台未发现标签功能异常；仅有既有 Vaporwave Sora/SpaceMono 字体资源 404。

## 自动化

- 标签 Repository/Bridge 专项：50 passed。
- Node 标签行为脚本：通过；覆盖排序请求竞态和旧响应丢弃。
- 全量：251 passed、36 subtests passed；2 个既有非法整型设置用例失败，分别为 `set_scan_depth("abc")` 与 `set_text_preview_chars("abc")`。
- `node --check`、Python `py_compile`、中文 JSON 与 `pypinyin==0.55.0` 导入：通过。
