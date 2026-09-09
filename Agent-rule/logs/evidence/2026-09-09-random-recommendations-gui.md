# 随机推荐 GUI 验收证据（2026-09-09）

- 被测程序：`.venv/Scripts/pythonw.exe src/main.py`
- 调试通道：Qt WebEngine page-level CDP，`127.0.0.1:9223`
- 验收脚本：`C:/Users/83023/.codex/visualizations/2026/09/09/01a08467-5398-7132-a16f-92516f8f3338/qt-cdp-verify.js`
- 截图：同目录 `random-recommendations-glass.png`、`random-recommendations-glass-1120.png`、`random-recommendations-vaporwave-1120.png`

## 结果

```json
{
  "columns": [
    {"title": "图书", "count": 3},
    {"title": "小说", "count": 3},
    {"title": "漫画", "count": 3}
  ],
  "searchDisabled": true,
  "viewToggle": "none",
  "sessionRetained": true,
  "rerolled": true,
  "keyboardSelection": {"selected": true, "detailVisible": true, "focusRole": "button"},
  "contextMenu": {"open": true, "labels": ["打开封面", "快速添加标签 / 合集", "编辑封面...", "从书库移除"]},
  "glass1400x860": {"horizontalOverflow": false},
  "glass1120x800": {"horizontalOverflow": false, "columnCount": 3},
  "vaporwave1120x800": {"horizontalOverflow": false, "columnCount": 3},
  "newRuntimeErrors": []
}
```

注：Vaporwave 加载时仍有两个既有字体 404：`SpaceMono-Regular.woff2` 与 `SpaceMono-Bold.woff2`。它们来自既有 `fonts.css`，本功能未修改该文件；未发现本功能新增的 JavaScript 异常或网络错误。
