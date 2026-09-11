# Text Novel 缩略图任务验收证据

## 根因

- Settings 的缩略图任务数组只有 Library 与 Comic。
- `ThumbnailTaskWorker` 未分派 `text_novel` scope。
- 后端没有 Text Novel 清空/重建任务，因此 sidecar 来源状态也没有对应维护语义。

## 自动化验证

- 专项 Python：`59 passed, 4 subtests passed`。
- Node 行为：`RANDOM_RECOMMENDATIONS_BEHAVIOR_OK`、`SHORTCUTS_BEHAVIOR_OK`。
- JavaScript 语法与中英文资源 JSON：通过。
- 全量 Pytest：`232 passed, 36 subtests passed, 2 failed`；两项失败均为既有非法整型设置回退测试，与本任务无关。
- `git diff --check`：通过，仅报告仓库既有 LF/CRLF 转换提示。

## 真实 Qt WebEngine 验收

- 数据隔离启动，不触碰正式数据库。
- Glass / Vaporwave：1440、749、390 三档均渲染 6 个缩略图维护按钮，其中 Text Novel 为清空与重建各 1 个。
- 各视口 `documentElement` 无横向溢出；390px Settings 改为单列，长按钮允许换行。
- 截图位于 Codex 本轮可视化目录：`text-thumbnail-settings-{glass|vaporwave}-{1440|749|390}.png`。
- 控制台仅出现既有 Vaporwave Sora/SpaceMono 字体 404。
