# 2026-09-23 玻璃 / 蒸汽波无刷新热切换真实 GUI 验收

## 根因与实现

- 原 `setUiSkin()` 只写入 `settings.uiSkin`、重绘设置页并提示重启，没有调用视觉换肤链路。
- 历史 WebView reload 方案会重建 DOM 并丢失路由、滚动和交互状态，本次不再使用。
- `base.css` 常驻；目标皮肤 CSS 首次后台加载，全部成功后在同一事件循环切换 `media`，后续直接复用缓存。
- 视觉切换成功后才通过既有 Bridge 持久化；加载失败保持旧皮肤并显示本地化警告。

## 自动化验证

- Python 全量：`330 tests`，通过。
- Node 行为：7 组通过，包含生产 `app.js` 的 Glass → Vaporwave → Glass、加载时序、缓存复用、skin-only 设置推送不重建 DOM、状态保持和失败回滚。
- JavaScript 语法：`app.js`、`text_rules.js` 通过 `node --check`。
- `zh-cn.json` 使用 `utf-8-sig` 解析通过；`git diff --check` 通过。

## 真实 Qt WebEngine 验收

- 环境：真实 `WebAppWindow` + PySide6 6.6.1 + Qt WebEngine，隔离临时 SQLite 与 24 本虚构图书，night 模式。
- 窗口：1400×860、760×820、390×820；Glass ↔ Vaporwave 双向切换均成功。
- 切换前后 Settings 路由、appearance 分区、内容与设置 DOM identity、昼夜状态保持；1400/760px 的设置页滚动保持 72px。
- Library 场景在三档宽度均保持搜索词、137px 滚动记录、选中项 identity、详情弹窗 identity 与可见状态。
- 两套皮肤 CSS 均驻留且只启用目标皮肤；Vaporwave 5 个、Glass 2 个，`base.css` 未被标记为皮肤资源。
- 三档宽度均无页面或内容横向溢出、无脚本错误、无白屏。

## 证据

- 截图目录：`C:\Users\83023\.codex\visualizations\2026\09\23\01a0cdf5-4fe8-7de2-baf4-31c5f0b7e68e`。
- 截图：`ui-skin-hot-swap-{glass|vaporwave}-{1400|760|390}.png`，共 6 张匿名截图。
- 临时验收脚本：`C:\tmp\bookhub_ui_skin_hot_swap_gui_qa.py`；不属于产品运行时或打包内容，未新增依赖或启动入口。
