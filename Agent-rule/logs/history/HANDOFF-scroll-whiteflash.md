# Handoff: QWebEngine 滚动白屏 / 重加载感（含 Text Rules 复现）

> 会话：Simple-Book-library · 2026-07-11  
> 用途：交给更强模型做根因确认与可能的底层重构  
> 应用栈：PySide6 + QWebEngineView + `app://` SPA（`src/bookhub/ui/web/`）

---

## 一、用户当前症状（新）

在 **Text Rules Web 面板**（Settings → 文本根 → Rules）内 **上下滚动** 时，再次出现类似「白屏 / 整页重加载」的观感。

注意：历史上「白屏」曾被拆成多种不同根因（见下），**不要假设同一机制**。本次可能是新路径（全量 `renderTextRulesPanel` / 预览回调 / overlay 合成），也可能与主列表滚动问题同源（Chromium 合成 / 主线程卡顿）。

---

## 二、历史问题谱系（已证实 vs 已修复）

### A. 焦点切回闪白（已修，非刷新）

- **表象**：切回窗口瞬间闪白。
- **证据**：仅有 `ActivationChange` / `window.focus`，**无** `renderPage` / `push_resources` / `loadFinished`。
- **修复**：`QWebEnginePage.setBackgroundColor` 同步日/夜底色；`viewEnter` 去掉 `opacity:0`。
- **文件**：`web_window.py`、`app.css`。

### B. 切页壳层空白（主线程卡顿，已缓解）

- **表象**：切到漫画大库时整块内容变白/卡住。
- **根因**：同步挂大量封面卡堵主线程（曾一次 608 卡）。
- **修复**：`scheduleRenderPage` + `renderGen`；后改为视口虚拟列表。
- **文件**：`app.js`。

### C. 壳层 backdrop 闪烁（已修）

- **表象**：滚动封面时侧栏/顶栏像在闪。
- **根因**：滚动区上方 chrome 的 `backdrop-filter` 对增长网格反复采样。
- **修复**：`.sidebar/.topbar/.detail-panel` 的 live `backdrop-filter: none`（注释在 `app.css`）。

### D. 大库狂滑「白屏卡住」（已缓解）

- **表象**：快速滑动后短暂白屏/无响应。
- **根因**：懒加载图片集中苏醒 + 解码风暴，非反复 `renderPage`。
- **缓解**：视口虚拟列表；`gridColumns` 放大单卡降同屏数；封面 `eager`；缓冲屏设置 3–6。

### E. 滚动失控上下抽到底（已修，有日志）

- **表象**：`scrollTop` 自动连跳冲到底。
- **证据（debug-e12ada / virt-debug-2）**：一旦 `topPad>0`，每帧 `scrollDelta≈301`（=一行高），`clamped:true`，冲到 `atBottom`。
- **根因**：Chromium **overflow-anchor** + 虚拟列表改 spacer/重建 DOM → scrollTop 被锚定推高 → 算出更大 topPad → 反馈环。
- **修复**：`.content-split` / `.virt-spacer-*` / `.cover-grid` 设 `overflow-anchor: none`；range 未变跳过 DOM 重建。
- **驳回假设**：行高估算大偏差（deltaMid 仅 ~-18）；ResizeObserver 振荡；滚动中 remount。

### F. 左键拖动滚动（已删）

- 恶性交互 Bug，已移除 `initDragScroll`。

### G. 旧分片 appendChunk（已替换）

- 旧日志曾见贴底 `scroll-append` 使 `remain` 暴涨；该路径已不在磁盘 `app.js` 中。

---

## 三、Text Rules 现状与高度可疑点（未用日志证实）

### 入口与文件

| 角色 | 路径 |
|------|------|
| UI | `src/bookhub/ui/web/js/text_rules.js` |
| 样式 | `src/bookhub/ui/web/css/app.css`（`.tr-*`） |
| Bridge | `src/bookhub/ui/web_bridge.py`（`openTextRules` / preview / save） |
| Catalog | `src/bookhub/library/text_rules/rule_catalog.py` |

### 架构风险（代码审阅级，待 runtime 验证）

1. **全量重绘**：几乎任何交互都调用 `renderTextRulesPanel()` → `clear(host)` 整面板拆掉重建（含滚动容器），滚动位置必然丢失；若预览/change 在滚动中触发，会像「白屏重载」。
2. **`.tr-col { overflow: auto }`**：三栏各自滚动；**未**设 `overflow-anchor: none`（主列表已设，TR 未跟）。
3. **`.tr-overlay`**：`position: fixed` 全屏遮罩；主壳仍有/曾有玻璃与 `contain`；QWebEngine 合成层滚动时可能闪底色（历史焦点闪白同类）。
4. **`markDirty` → 防抖 preview**：`input` 也会 `markDirty`；若某控件在滚动时误触发 change/input，会 preview + 可能连带重绘。
5. **无虚拟化**：步骤很多时中栏 DOM 大，滚动卡顿会被用户描述成白屏。

### 建议优先假设（给下一任模型）

| ID | 假设 |
|----|------|
| H1 | 滚动中触发了 `renderTextRulesPanel` 全量 clear+rebuild |
| H2 | preview 回调或 `textRulesOpen`/settings 信号导致面板重挂 |
| H3 | `.tr-col` 缺少 `overflow-anchor: none`，spacer/高度变化锚定跳动（若有动态高度） |
| H4 | overlay/fixed + QWebEngine 合成：滚动时露出 page 底色（真闪白非 reload） |
| H5 | 主线程长任务（preview Python 同步回传挤 UI）造成短暂白屏感 |

---

## 四、已验证有效的工程约束（重构时勿破坏）

1. 主内容滚动容器必须 `overflow-anchor: none`（虚拟列表）。
2. 滚动路径上避免 live `backdrop-filter`。
3. 页面底色与 `QWebEnginePage.setBackgroundColor` 一致，避免清屏露白。
4. 大列表禁止全量挂 DOM；用视口窗口 + range 去重。
5. 调试日志：JS 用 ingest `http://127.0.0.1:7262/ingest/83849951-30eb-4a89-b748-e11b95f30a88` + session `e12ada`；或 `bridge.agentDebugLog` 写 `debug-e12ada.log` / `.cursor/debug-e12ada.log`（Qt 有时拦 fetch）。
6. **先日志后修**；修后保留埋点做 post-fix。

---

## 五、建议重构方向（若确认非小补丁）

1. **Text Rules 状态驱动局部更新**：拆成 left/mid/right 独立 render；禁止滚动中 `clear(host)`；保存 scrollTop 或用事件委托避免重建。
2. **预览与编辑解耦**：preview 只改 `#trPreviewResult` 文本，永不重绘表单。
3. **统一滚动策略模块**：所有 `overflow: auto` 面板套用同一套（anchor none、无 backdrop、可选 contain）。
4. **可选**：步骤列表也做轻量虚拟化（规则很多时）。
5. **底层**：评估 QWebEngine 合成（`transform`/`isolation`/`contain`）与 overlay 层级是否过度；必要时 Text Rules 改为非 fixed 的 stage 内路由页，减少双层滚动。

---

## 六、可直接粘贴给更强模型的提示词

```text
你在仓库 F:/Coding_Dev/BOOKS/Simple-Book-library 工作。这是 PySide6 + QWebEngine 本地书库；前端在 src/bookhub/ui/web/。

【当前 Bug】
用户在 Web 版 Text Rules 面板（Settings → 文本根 Rules）内上下滚动时，出现「白屏 / 像整页重加载」的观感。

【必须先读】
- Agent-rule/logs/history/2026-07-11.md（白屏/虚拟列表/overflow-anchor 全谱系）
- Agent-rule/logs/history/HANDOFF-scroll-whiteflash.md（本交接）
- src/bookhub/ui/web/js/text_rules.js（尤其 renderTextRulesPanel / clear(host) / markDirty）
- src/bookhub/ui/web/css/app.css（.tr-* 与 .content-split overflow-anchor）
- src/bookhub/ui/web_window.py（setBackgroundColor）
- src/bookhub/ui/web/js/app.js（mountVirtualCoverGrid / attachVirtualWindow）

【历史已证实（勿重复踩坑）】
1. 焦点闪白 ≠ 刷新；修 setBackgroundColor + 去掉 viewEnter opacity:0
2. 壳层闪：滚动路径禁用 backdrop-filter
3. 大库卡：虚拟列表 + 降同屏解码
4. 滚动失控抽到底：overflow-anchor + spacer 反馈环；已对 .content-split/virt-spacer/cover-grid 设 overflow-anchor:none + range 去重
5. 左键拖动滚动已删除

【Text Rules 代码级嫌疑（未用日志证实）】
- renderTextRulesPanel() 几乎每次交互 clear 整面板重建 → 滚动中若被调用必像 reload
- .tr-col overflow:auto 未设 overflow-anchor:none
- markDirty/preview 与全量重绘耦合
- fixed overlay 与 QWebEngine 合成可能露底色

【工作方式】
1. 先提 3–5 个假设并埋点（JS ingest + 必要时 bridge 写 debug-e12ada.log），区分：是否调用了 renderTextRulesPanel、scrollTop 是否被重置、是否 preview/signal、是否纯合成闪白。
2. 有 runtime 证据再改；优先最小修复；若架构迫使全量 rebuild，再重构为局部更新。
3. 更新 src_construction.md（插入注释）与 Agent-rule/logs/history/。
4. 回复中文；结束说明下一步/未做/风险。

【成功标准】
Text Rules 三栏内快速上下滚动：无白屏、无整页闪断、滚动位置稳定；预览仍可用；pytest src/tests/test_web_bridge_smoke.py 通过。
```

---

## 七、复现步骤（给下一任 / 埋点用）

1. 源码启动应用（非旧打包）。
2. 设置 → 文本小说根目录 → Rules 打开 Web 面板。
3. 在中栏步骤区或右栏预览区快速上下滚动 10–20 秒，观察白屏/重载感。
4. 若有埋点：同时试改一个步骤参数，看滚动是否与 preview/重绘耦合。
