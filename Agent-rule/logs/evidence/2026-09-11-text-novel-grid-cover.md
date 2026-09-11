# 文本小说 Grid 与同名封面验收证据

## 自动测试

- 专项 Python：66 passed，4 subtests passed。
- Node 行为测试：`test_random_recommendations.js` 与 `test_shortcuts.js` 通过。
- JavaScript 语法：`node --check src/bookhub/ui/web/js/app.js` 通过。
- 全量 Python：229 passed，36 subtests passed；2 个既有非法整型设置失败，与本变更无关。
- `git diff --check` 通过，仅有工作区既有行尾转换提示。

## 真实 Qt WebEngine

- 使用隔离数据库及实际 `scan_text_roots` 生成 5 张同名封面缓存和 1 个无封面占位，不访问现有书库数据库。
- Glass 与 Vaporwave 均检查 1920、1440、1280、768、749、390、375 宽度。
- 所有宽度均无 document/content 横向溢出；Grid 默认激活并显示标题。
- 390px 首轮发现外壳裁切视图控件，增加 600px 单列断点后复验为两列卡片，搜索、Grid/List 和 Scan 均可操作。
- 键盘 Enter 可选中卡片并打开详情；卡片具有 `role=button`、`tabindex=0`，两套皮肤均提供 `:focus-visible` 描边。
- List 为 4 列（Title、Author、Tags、Path），无 Cover 列；切回 Grid 后按钮状态同步。
- 控制台仅有既有 Vaporwave Sora/SpaceMono 字体文件 404，无本功能 JavaScript 异常。

## 截图

- `C:\Users\83023\.codex\visualizations\2026\09\11\01a08f8b-44cf-7e33-a3ca-54ec24e46f9f\text-novel-glass-1440.png`
- `C:\Users\83023\.codex\visualizations\2026\09\11\01a08f8b-44cf-7e33-a3ca-54ec24e46f9f\text-novel-glass-749.png`
- `C:\Users\83023\.codex\visualizations\2026\09\11\01a08f8b-44cf-7e33-a3ca-54ec24e46f9f\text-novel-glass-390.png`
- `C:\Users\83023\.codex\visualizations\2026\09\11\01a08f8b-44cf-7e33-a3ca-54ec24e46f9f\text-novel-vaporwave-1440.png`
- `C:\Users\83023\.codex\visualizations\2026\09\11\01a08f8b-44cf-7e33-a3ca-54ec24e46f9f\text-novel-vaporwave-749.png`
- `C:\Users\83023\.codex\visualizations\2026\09\11\01a08f8b-44cf-7e33-a3ca-54ec24e46f9f\text-novel-vaporwave-390.png`
