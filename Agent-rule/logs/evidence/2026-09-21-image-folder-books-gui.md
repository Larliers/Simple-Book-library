# 总书库图片文件夹书籍 GUI 验收证据（2026-09-21）

- 被测程序：真实 `WebAppWindow` + Qt WebEngine；使用隔离临时 SQLite、缓存和虚构图片目录，不读写 `src/sql/library.db` 或用户书库。
- 验收脚本：`C:/tmp/bookhub_image_folder_gui_qa.py`。
- 截图目录：`C:/Users/83023/.codex/visualizations/2026/09/20/01a0bf3a-d2a0-7773-8bac-1e34eb963edd/`。
- 皮肤与视口：Glass / Vaporwave；1400×860、760×800、390×844；总书库与书籍合集详情。

## 结果

- 两套皮肤、两个页面的卡片均显示 `IMG`，相对封面容器偏移为 `top=6px`、`left=6px`，复用既有 `.format-badge`。
- 六组页面/视口组合均无 document 或内容区横向溢出，`window.__qaErrors` 均为空。
- 双击总书库与合集卡片均打开自然序首图 `0001.jpg`；右键菜单“打开文件夹”打开图片书目录。
- 临时扫描摘要为 `image_book_detected_folders=1`、`image_book_added_count=1`，无 warning/error。
- 用户样本仅只读核验：深度 2、80 张 JPG、0 个其他文件、0 个子目录，预期识别 1 本图片书；未写入用户书库。
- 双轴审查修复后 Python 全量 `313` 项通过；五组 Node 行为测试、`app.js` / `text_rules.js` 语法检查和 `git diff --check` 通过。

## 截图

- `image-folder-glass-library-{1400,760,390}.png`
- `image-folder-glass-collection-{1400,760,390}.png`
- `image-folder-vaporwave-library-{1400,760,390}.png`
- `image-folder-vaporwave-collection-{1400,760,390}.png`
