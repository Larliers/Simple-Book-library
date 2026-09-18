# Quick Add 合集无刷新 GUI 验收证据（2026-09-15）

- 被测程序：真实 `WebAppWindow` 与 Qt WebEngine；`web_window.LibraryRepository` 替换为隔离临时数据库，不读写用户书库。
- 双击入口：沿用项目根目录现有 `启动 简易图书馆.lnk`，未新增第二个启动器。
- 验收脚本：`C:/Users/83023/.codex/visualizations/2026/09/15/01a0a2e1-2b21-7680-b70a-7b3bda33069e/bookhub_quick_add_3kind_qa.py`
- 截图目录：`C:/Users/83023/.codex/visualizations/2026/09/15/01a0a2e1-2b21-7680-b70a-7b3bda33069e/`
- JSON 报告：同目录 `quick-add-3kind-report.json`

## 结果

Glass 740×860 与 Vaporwave 600×860 均覆盖：

- Library / Text Novel / Comic：深滚动后「创建并添加」
- Library：加入已有合集「Existing Books」（不创建）

成功条件：弹窗关闭、合集页缓存即时出现目标名称、`renderGen` 不变、页面与内容区无横向溢出。除 Vaporwave 600 Text Novel 外，提交前后 `scrollTop=1400`。

Vaporwave 600 Text Novel 的 `#contentArea` 在本次布局下 `scrollHeight=4598` 但内部 `scrollTop` 保持 0（`clientHeight` 吃掉可滚区间）；合集写入仍不重绘，Glass 740 同页为 `scrollTop=1400`。不当作功能失败。

| 皮肤 | 宽度 | 用例 | 截图 |
|---|---|---|---|
| Glass | 740 | Library 创建 | `quick-add-glass-740-library-create.png` |
| Glass | 740 | Library 加入已有 | `quick-add-glass-740-library-add-existing.png` |
| Glass | 740 | Text Novel 创建 | `quick-add-glass-740-text_novel-create.png` |
| Glass | 740 | Comic 创建 | `quick-add-glass-740-comic-create.png` |
| Vaporwave | 600 | Library 创建 | `quick-add-vaporwave-600-library-create.png` |
| Vaporwave | 600 | Library 加入已有 | `quick-add-vaporwave-600-library-add-existing.png` |
| Vaporwave | 600 | Text Novel 创建 | `quick-add-vaporwave-600-text_novel-create.png` |
| Vaporwave | 600 | Comic 创建 | `quick-add-vaporwave-600-comic-create.png` |

Codex 上午另存 `quick-add-glass-740.png`、`quick-add-vaporwave-600.png`（仅 Library 快捷创建）。

## 自动化

- 聚焦：`PYTHONPATH=src pytest src/tests/test_repository_orphan_cleanup.py::RepositorySettingNormalizeTests src/tests/test_collection_kinds.py src/tests/test_web_bridge_smoke.py -q` → `71 passed`
- 全量：`PYTHONPATH=src pytest src/tests -q` → `270 passed, 43 subtests passed`
- Node `test_quick_add.js`：经 Bridge 冒烟调用，输出 `QUICK_ADD_BEHAVIOR_OK`
- 控制台：`window.__qaErrors` 为空；Vaporwave 既有字体 404 不在本次 JS error 钩子内
