# 文本小说列表表头排序 GUI 验收证据（2026-09-13）

- 被测程序：真实 `WebAppWindow` 与 Qt WebEngine；Repository 替换为隔离临时数据库，不读写用户书库。
- 双击入口：沿用项目根目录现有 `启动 简易图书馆.lnk`，未新增第二个启动器。
- 截图目录：`C:/Users/83023/.codex/visualizations/2026/09/13/01a0992e-edfe-7da3-ba83-68f2ee03c9ed/`，文件名为 `text-sort-{glass|vaporwave}-{1440|749|390}.png`。

## 结果

- Glass 与 Vaporwave 均在 1440×860、749×800、390×844 验收；Text Novel 主页和小说合集详情均无页面或内容区横向溢出。
- 文件日期排序时四列表头均为 `aria-sort=none` 且不显示箭头；首次点击作者得到 `author_asc`、`▲` 与 `aria-sort=ascending`，再次点击得到 `author_desc`、`▼` 与 `aria-sort=descending`。
- 表头和下拉框同步显示相同 sort；下拉切到路径升序后，活动表头为“路径 ▲”。
- 小说合集详情使用同一组四列表头；点击标签后得到 `tags_asc`，主页与合集分别持久化为各自设置键。
- 四个表头均为原生 `button`；真实 Qt WebEngine 焦点下按 Enter 得到 `author_asc`，重新聚焦后按 Space 得到 `author_desc`；两套皮肤的 hover、active 与 `focus-visible` 样式已加载，交互阶段未捕获 JavaScript error。

## 自动化

- Text Novel Repository/Bridge 专项：53 passed。
- Node DOM 行为脚本与 `node --check`：通过。
- 中文 JSON：通过。
- 全量：256 passed、43 subtests passed；2 个既有失败仍为 `set_scan_depth("abc")` 与 `set_text_preview_chars("abc")`，与本功能无关。
