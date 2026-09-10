# 随机推荐响应式密度 GUI 验收证据（2026-09-10）

- 被测程序：`.venv/Scripts/pythonw.exe src/main.py`
- 调试通道：Qt WebEngine page-level CDP，`127.0.0.1:9223`
- 验收脚本：`C:/Users/83023/.codex/visualizations/2026/09/09/01a08467-5398-7132-a16f-92516f8f3338/qt-cdp-responsive-verify.js`
- 截图：同目录 `random-recommendations-responsive-glass-2560.png`、`random-recommendations-responsive-vaporwave-2560.png`
- 应用持久化 Web zoom 为 1.1，因此 2560×1440 设备视口对应 2327×1309 CSS px。

## 结果

```json
{
  "glass2560_default_6_2": {"eachCategoryCount": 6, "rows": 3, "effectiveColumns": 2, "cardWidthPx": 247, "horizontalOverflow": false},
  "glass2560_3_1": {"eachCategoryCount": 3, "rows": 3, "effectiveColumns": 1, "cardWidthPx": 260, "horizontalOverflow": false},
  "glass2560_12_3": {"eachCategoryCount": 12, "rows": 4, "effectiveColumns": 3, "cardWidthPx": 159, "horizontalOverflow": false},
  "glass1920_default": {"rows": 3, "effectiveColumns": 2, "cardWidthPx": 150, "horizontalOverflow": false},
  "glass1400_default": {"rows": 6, "effectiveColumns": 1, "cardWidthPx": 161, "horizontalOverflow": false},
  "glass1120_default": {"rows": 6, "effectiveColumns": 1, "cardWidthPx": 195, "horizontalOverflow": false},
  "vaporwave2560_default_6_2": {"eachCategoryCount": 6, "rows": 3, "effectiveColumns": 2, "cardWidthPx": 247, "horizontalOverflow": false},
  "vaporwave2560_3_1": {"eachCategoryCount": 3, "rows": 3, "effectiveColumns": 1, "cardWidthPx": 260, "horizontalOverflow": false},
  "vaporwave2560_12_3": {"eachCategoryCount": 12, "rows": 4, "effectiveColumns": 3, "cardWidthPx": 159, "horizontalOverflow": false},
  "vaporwave1920_default": {"rows": 3, "effectiveColumns": 2, "cardWidthPx": 150, "horizontalOverflow": false},
  "vaporwave1400_default": {"rows": 6, "effectiveColumns": 1, "cardWidthPx": 161, "horizontalOverflow": false},
  "vaporwave1120_default": {"rows": 6, "effectiveColumns": 1, "cardWidthPx": 195, "horizontalOverflow": false},
  "columnSettingChangePreservedRecommendationIds": true,
  "switchPageRetainedRecommendationIds": true,
  "rerollReplacedRecommendationIds": true,
  "keyboardAndDetail": {"selected": true, "focusedRole": "button", "detailVisible": true},
  "shortAndEmpty": {"categoryCounts": [2, 1, 0], "thirdCategoryEmptyState": true},
  "settingsItemsOptions": ["3", "6", "9", "12"],
  "settingsColumnsOptions": ["1", "2", "3"]
}
```

两套皮肤均完成 2560×1440 的 6/2、3/1、12/3 组合及 1920×1080、1400×860、1120×800 断点。外层始终保持图书/小说/漫画三列；卡片按行优先排列，中间区域可纵向滚动。视觉检查确认封面随分类宽度放大，边框、阴影、格式角标和空封面保持皮肤风格。另以实际运行时 DOM 注入 2/1/0 项结果，确认数量不足与空分类提示；切页缓存、重新推荐、键盘焦点和右侧详情均通过。

控制台未发现本功能新增错误。Vaporwave 每次加载仍报告既有 `SpaceMono-Regular.woff2` 与 `SpaceMono-Bold.woff2` 两个 404；本任务未修改字体资源或路径。
