# 可自定义快捷键 GUI 验收证据（2026-09-11）

- 被测程序：`.venv/Scripts/pythonw.exe src/main.py`
- 调试通道：Qt WebEngine page-level CDP，`127.0.0.1:9224`
- 验收脚本：`C:/Users/83023/.codex/visualizations/2026/09/09/01a08467-5398-7132-a16f-92516f8f3338/qt-cdp-shortcuts-verify.js`
- 截图：同目录 `shortcuts-settings-glass-2560.png`、`shortcuts-settings-vaporwave-2560.png`
- 当前持久化 Web zoom 为 1.2，因此 2560/1400/1120 设备宽分别对应 2133/1167/933 CSS px。

## 结果

- Glass 与 Vaporwave 在 2560×1440、1400×860、1120×800 均渲染 1 个导航动作与 6 个资源动作；页面、内容区及所有快捷键行均无横向溢出。
- 实际设置页完成 `KeyK` 录入；重复绑定拒绝并保持录入态；`MouseForward` 经同一原生输入处理函数完成录入；Escape 取消录入。
- Library 选中资源后 `KeyK` 打开 Quick Add；搜索输入框聚焦和普通模态框开启时均暂停快捷键。
- `MouseBack` 绑定完成合集详情退出与最近系列重新进入，目标 ID 保持一致，页面 URL 未发生 Chromium 历史导航。
- Qt 集成测试向真实 `ShortcutWebView` 发送 Back/Forward 的 press/release，四个事件均被接受，且仅 press 分别发出 `MouseBack`/`MouseForward`。
- 测试前后完整绑定表恢复为原值（本次为七项全空）。

控制台无本功能新增错误。Vaporwave 仍报告既有 `SpaceMono-Regular.woff2` 与 `SpaceMono-Bold.woff2` 两个 404，本任务未修改字体路径。

## 自动化

- `node --check src/bookhub/ui/web/js/app.js`：通过。
- Node 快捷键/随机推荐行为脚本：通过。
- Repository/Bridge 专项：46 passed。
- 全量：213 passed、32 subtests passed；2 个既有 Repository 非法整型用例失败，分别为 `set_scan_depth("abc")` 与 `set_text_preview_chars("abc")`。
